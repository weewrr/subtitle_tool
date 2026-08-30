"""SRT 配音时间对齐模块（自然语速优先）。

被 Qwen3-TTS/srt_dubbing_qwen.py 阶段二调用，职责：
  - 超时的片段向窗口内邻居借用空闲时间（优先利用原始静音），
    速度回落到舒适区，避免整段被统一加速；
  - 仅在真正全局溢出时才做有上限(HARD_MAX)的平滑压缩；
  - 相邻语速做平滑，避免忽快忽慢；
  - 逐段 time-stretch(ffmpeg atempo, 变速不变调) 拼接，
    并输出对齐报告与质量检查。
"""

import itertools
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

_file_counter = itertools.count()


class AlignmentConfig:
    """对齐参数。所有时间为秒。"""

    def __init__(self):
        # ---- 借时（局部窗口扩张）----
        self.max_lead_s = 1.0      # 允许提前起始的最大时长（字幕出现前即开始配音）
        self.min_gap_s = 0.05      # 相邻段实际音频间保留的最小间隙
        self.max_speed = 1.35      # 借时阶段允许的最大语速（舒适区上限）

        # ---- 全局溢出压缩 ----
        self.hard_max_speed = 1.6  # 全局溢出压缩的语速硬上限

        # ---- 相邻语速平滑 ----
        self.smooth_rounds = 1        # 平滑轮数
        self.smooth_own_weight = 0.6  # 平滑时自身语速权重（其余分给邻居均值）

        # ---- 拼接 ----
        self.fade_ms = 5.0            # 每段首尾线性淡入淡出（毫秒），防爆音


@dataclass
class Segment:
    """一条字幕的 TTS 音频与时间信息。

    original_* 为字幕时间轴（秒）；tts_audio 为裁剪静音后的音频
    （float32 numpy 数组）；tts_duration 为其真实时长（秒）。
    final_* / speed 由 compute_alignment 就地填写。
    """

    id: int
    text: str
    original_start: float
    original_end: float
    tts_duration: float
    tts_audio: np.ndarray

    # ---- 对齐结果 ----
    final_start: Optional[float] = None
    final_duration: Optional[float] = None
    speed: float = 1.0


def _is_playable(seg):
    return (seg.tts_audio is not None
            and len(seg.tts_audio) > 0
            and seg.tts_duration > 0)


def _neighbor_caps(segments, i, video_duration_s, cfg, prev_end):
    """估算第 i 段可借的 (lead_cap, slot, lag_cap)。

    后借：到下一条字幕开始前（优先占用字幕间静音）；
    前借：不与上一段实际音频结束重叠，且不超过 max_lead_s。
    """
    seg = segments[i]
    slot = max(0.0, seg.original_end - seg.original_start)
    n = len(segments)

    lead_cap = min(cfg.max_lead_s, max(0.0, seg.original_start - prev_end))
    if i + 1 < n:
        next_start = segments[i + 1].original_start
    elif video_duration_s:
        next_start = video_duration_s
    else:
        next_start = seg.original_end + 10 * cfg.max_lead_s
    lag_cap = max(0.0, next_start - cfg.min_gap_s - seg.original_end)
    if video_duration_s:
        lag_cap = min(lag_cap, max(0.0, video_duration_s - seg.original_end))
    return lead_cap, slot, lag_cap


def compute_alignment(segments, video_duration_s, cfg):
    """计算每段的目标语速与最终放置位置。

    返回 (segments, report, ok, issues)；segments 为就地更新后的同一列表。
    """
    issues = []
    n = len(segments)
    if n == 0:
        return segments, '无字幕段', True, issues

    # ===== Pass A：借时 + 舒适区语速（用相邻字幕边界估算窗口）=====
    prev_end = 0.0
    for i, seg in enumerate(segments):
        if not _is_playable(seg):
            seg.speed = 1.0
            seg.final_start = seg.original_start
            seg.final_duration = 0.0
            issues.append(f"[{seg.id + 1}] TTS 音频为空，该段保持静音")
            continue
        lead_cap, slot, lag_cap = _neighbor_caps(
            segments, i, video_duration_s, cfg, prev_end)
        window = lead_cap + slot + lag_cap
        if seg.tts_duration <= slot:
            seg.speed = 1.0
        elif window > 0:
            # 用满可借窗口后的语速；超出舒适区则 clamp（残留溢出由放置阶段截断）
            seg.speed = min(max(1.0, seg.tts_duration / window), cfg.max_speed)
        else:
            seg.speed = cfg.max_speed
        seg.final_duration = seg.tts_duration / seg.speed
        prev_end = max(prev_end, seg.original_start + seg.final_duration)

    # ===== Pass B：全局溢出 → 有 HARD_MAX 上限的整体压缩 =====
    if video_duration_s:
        end_max = max(
            (max(s.original_end, s.original_start + s.final_duration)
             for s in segments if s.final_duration > 0),
            default=0.0)
        if end_max > video_duration_s + 1e-6:
            factor = end_max / video_duration_s
            for s in segments:
                if s.final_duration > 0:
                    s.speed = min(s.speed * factor, cfg.hard_max_speed)
                    s.final_duration = s.tts_duration / s.speed
            if any(s.speed >= cfg.hard_max_speed - 1e-6 for s in segments):
                issues.append(
                    f"全局溢出，部分段落语速已达硬上限 {cfg.hard_max_speed:.2f}x")

    # ===== Pass C：相邻语速平滑（只上调：加速安全，减速有超窗风险）=====
    for _ in range(max(0, cfg.smooth_rounds)):
        speeds = [s.speed for s in segments]
        for i, s in enumerate(segments):
            if s.final_duration <= 0:
                continue
            neigh = [speeds[j] for j in (i - 1, i + 1)
                     if 0 <= j < n and segments[j].final_duration > 0]
            if not neigh:
                continue
            avg = sum(neigh) / len(neigh)
            cand = cfg.smooth_own_weight * speeds[i] \
                + (1 - cfg.smooth_own_weight) * avg
            if cand > s.speed:
                s.speed = min(cand, cfg.hard_max_speed)
                s.final_duration = s.tts_duration / s.speed

    # ===== Pass D：放置（顺序游标 + 防重叠 + 截断）=====
    prev_audio_end = 0.0
    for i, seg in enumerate(segments):
        if seg.final_duration <= 0:
            seg.final_start = seg.original_start
            continue
        dur = seg.final_duration
        lead_cap, slot, lag_cap = _neighbor_caps(
            segments, i, video_duration_s, cfg, prev_audio_end)
        # 优先延后（保持字幕同步感），不足再提前起始
        lag_used = min(lag_cap, max(0.0, dur - slot))
        lead_used = min(lead_cap, max(0.0, dur - slot - lag_cap))
        start = seg.original_start - lead_used

        # 防重叠：不早于上一段实际音频结束
        min_start = prev_audio_end + cfg.min_gap_s
        if start < min_start:
            start = min_start

        # 截断：不越过下一条字幕开始 / 视频末尾（语速已达上限时的兜底）
        if i + 1 < n:
            hard_end = segments[i + 1].original_start - cfg.min_gap_s
        elif video_duration_s:
            hard_end = video_duration_s
        else:
            hard_end = start + dur
        if start + dur > hard_end + 1e-6:
            allowed = max(0.0, hard_end - start)
            issues.append(
                f"[{seg.id + 1}] 语速达上限仍超窗，截断 {dur - allowed:.2f}s")
            dur = allowed

        seg.final_start = start
        seg.final_duration = dur
        prev_audio_end = start + dur

    # ===== 报告 =====
    lines = []
    n_spd = 0
    spd_sum = 0.0
    for s in segments:
        slot = s.original_end - s.original_start
        if s.final_duration <= 0:
            lines.append(
                f"[{s.id + 1}] 窗口 {slot:.2f}s | 静音段")
            continue
        n_spd += 1
        spd_sum += s.speed
        offset = s.final_start - s.original_start
        lines.append(
            f"[{s.id + 1}] 窗口 {slot:.2f}s | TTS {s.tts_duration:.2f}s "
            f"| 语速 {s.speed:.2f}x | 起始 {s.final_start:.2f}s"
            f"({offset:+.2f}s) | 结束 {s.final_start + s.final_duration:.2f}s")
    tail = max((s.final_start + s.final_duration for s in segments
                if s.final_duration > 0), default=0.0)
    summary = f"共 {n} 段（有效 {n_spd}），平均语速 {spd_sum / n_spd:.2f}x" if n_spd \
        else "无有效音频段"
    if video_duration_s:
        summary += f"，配音末尾 {tail:.2f}s / 视频 {video_duration_s:.2f}s"
    report = "\n".join(lines + [summary])

    return segments, report, not issues, issues


def _atempo(wav, speed, temp_dir, sample_rate):
    """ffmpeg atempo 变速不变调。失败时返回原音频（回退，不加速）。"""
    speed = min(max(speed, 0.5), 2.0)
    tag = next(_file_counter)
    in_path = os.path.join(temp_dir, f'align_in_{tag}.wav')
    out_path = os.path.join(temp_dir, f'align_out_{tag}.wav')
    sf.write(in_path, wav, sample_rate)
    cmd = [
        'ffmpeg', '-y',
        '-i', in_path,
        '-filter:a', f'atempo={speed:.6f}',
        '-ar', str(sample_rate),
        out_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode != 0:
            logger.warning(f"ffmpeg atempo 失败(speed={speed:.3f}): {result.stderr}")
            return wav
        out_wav, _ = sf.read(out_path)
        if out_wav.dtype != np.float32:
            out_wav = out_wav.astype(np.float32)
        return out_wav
    except FileNotFoundError:
        logger.warning("ffmpeg 未找到，段落未加速（保持原速）")
        return wav


def _fade(wav, fade_ms, sample_rate):
    """首尾线性淡入淡出，防止拼接爆音。"""
    n = int(fade_ms / 1000 * sample_rate)
    if n <= 0 or len(wav) < 2 * n:
        return wav
    env = np.linspace(0.0, 1.0, n, dtype=np.float32)
    out = wav.copy()
    out[:n] *= env
    out[-n:] *= env[::-1]
    return out


def apply_audio_stretch(segments, sample_rate, cfg):
    """按 compute_alignment 的结果逐段变速并拼接为完整音轨。"""
    temp_dir = tempfile.mkdtemp(prefix='tts_align_')
    try:
        placed = []
        for seg in segments:
            if seg.final_start is None or not seg.final_duration \
                    or seg.final_duration <= 0 or not _is_playable(seg):
                continue
            wav = np.asarray(seg.tts_audio, dtype=np.float32)
            speed = seg.speed if seg.speed and seg.speed > 0 else 1.0
            if abs(speed - 1.0) > 0.01:
                wav = _atempo(wav, speed, temp_dir, sample_rate)
            # 对齐到目标时长（ffmpeg 输出长度存在少量偏差）
            target_len = int(round(seg.final_duration * sample_rate))
            if len(wav) > target_len:
                wav = wav[:target_len]
            wav = _fade(wav, cfg.fade_ms, sample_rate)
            placed.append((int(round(seg.final_start * sample_rate)), wav))

        if not placed:
            return np.zeros(0, dtype=np.float32)

        total_len = max(off + len(w) for off, w in placed)
        out = np.zeros(total_len, dtype=np.float32)
        for off, w in placed:
            if off < 0:  # 防御：理论上放置阶段不会产生负起始
                w = w[-off:]
                off = 0
            end = min(total_len, off + len(w))
            if end > off:
                out[off:end] = w[:end - off]
        return out
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
