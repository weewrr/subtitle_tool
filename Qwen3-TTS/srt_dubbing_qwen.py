# Copyright (c) 2025 Qwen Team
# SRT字幕配音脚本 - Qwen3-TTS版本

import os
import re
import sys
import argparse
import logging
import platform
import numpy as np
import soundfile as sf
import subprocess
import tempfile

import torch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000


def parse_srt_time(time_str):
    """将SRT时间格式转换为毫秒"""
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        hours = int(hours)
        minutes = int(minutes)
        sec_parts = seconds.split('.')
        secs = int(sec_parts[0])
        ms = int(sec_parts[1].ljust(3, '0')[:3]) if len(sec_parts) > 1 else 0
        return (hours * 3600 + minutes * 60 + secs) * 1000 + ms
    return 0


def parse_srt(srt_path):
    """解析SRT字幕文件"""
    subtitles = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0].strip())
                time_line = lines[1].strip()
                time_match = re.match(
                    r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
                    time_line
                )
                if time_match:
                    start_time = parse_srt_time(time_match.group(1))
                    end_time = parse_srt_time(time_match.group(2))
                    text = '\n'.join(lines[2:]).strip()
                    subtitles.append({
                        'index': index,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text
                    })
            except (ValueError, IndexError) as e:
                logger.warning(f"解析字幕块失败: {block[:50]}... 错误: {e}")
                continue
    
    return subtitles


def generate_silence(duration_ms, sample_rate=SAMPLE_RATE):
    """生成指定时长的静音"""
    samples = int(duration_ms / 1000 * sample_rate)
    return np.zeros(samples, dtype=np.float32)


def trim_silence(wav, sample_rate, threshold=0.01):
    """裁剪音频首尾静音，尽量挤压静音区间（保留少量首尾余量防止切音）"""
    if len(wav) == 0:
        return wav
    non_silent = np.where(np.abs(wav) > threshold)[0]
    if len(non_silent) == 0:
        return wav
    head_margin = int(0.02 * sample_rate)
    tail_margin = int(0.05 * sample_rate)
    start = max(0, int(non_silent[0]) - head_margin)
    end = min(len(wav), int(non_silent[-1]) + 1 + tail_margin)
    return wav[start:end]


def apply_global_tempo_ffmpeg(wav, tempo, temp_dir, sample_rate=SAMPLE_RATE):
    """
    全局变速（变速不变调）：配音总长超过视频长度时，
    将整条配音按 tempo 压缩回视频长度。atempo 接受任意小数倍速（如 1.437）。
    失败时返回原音频。
    """
    in_path = os.path.join(temp_dir, 'global_pre_tempo.wav')
    out_path = os.path.join(temp_dir, 'global_post_tempo.wav')
    sf.write(in_path, wav, sample_rate)
    
    cmd = [
        'ffmpeg', '-y',
        '-i', in_path,
        '-filter:a', f'atempo={tempo:.6f}',
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
            logger.error(f"ffmpeg全局变速失败: {result.stderr}")
            return wav
        out_wav, _ = sf.read(out_path)
        if out_wav.dtype != np.float32:
            out_wav = out_wav.astype(np.float32)
        return out_wav
    except FileNotFoundError:
        logger.error("ffmpeg未找到，请确保已安装并添加到PATH")
        return wav


def detect_language(text):
    """检测文本语言"""
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(re.sub(r'\s', '', text))
    
    if total_chars == 0:
        return "Auto"
    
    chinese_ratio = chinese_chars / total_chars
    
    if chinese_ratio > 0.3:
        return "Chinese"
    else:
        return "Auto"


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS SRT字幕配音生成")
    parser.add_argument("srt_file", type=str, help="SRT字幕文件路径")
    parser.add_argument("--output_dir", type=str, default=None, help="输出目录")
    parser.add_argument("--model_dir", type=str, 
                        default="Qwen3-TTS-12Hz-1.7B-Base",
                        help="模型目录")
    parser.add_argument("--device", type=int, default=0, help="CUDA设备编号")
    parser.add_argument("--prompt_speech_path", type=str, required=True,
                        help="参考音频路径")
    parser.add_argument("--video_duration_ms", type=float, default=None,
                        help="视频总时长（毫秒），配音总长超过时整体加速压回视频长度")
    parser.add_argument("--prompt_text", type=str, default=None,
                        help="参考音频文本")
    parser.add_argument("--mode", type=str, default="icl",
                        choices=["icl", "xvec_only"],
                        help="克隆模式: icl(高质量) 或 xvec_only(快速)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.srt_file):
        logger.error(f"SRT文件不存在: {args.srt_file}")
        sys.exit(1)
    
    if not os.path.exists(args.prompt_speech_path):
        logger.error(f"参考音频不存在: {args.prompt_speech_path}")
        sys.exit(1)
    
    if args.output_dir is None:
        args.output_dir = os.path.dirname(args.srt_file)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    temp_dir = tempfile.mkdtemp(prefix='qwen_tts_dubbing_')
    
    logger.info(f"解析SRT文件: {args.srt_file}")
    subtitles = parse_srt(args.srt_file)
    
    if not subtitles:
        logger.error("未找到有效的字幕条目")
        sys.exit(1)
    
    logger.info(f"共找到 {len(subtitles)} 条字幕")
    
    device = f"cuda:{args.device}" if torch.cuda.is_available() else "cpu"
    # 打印实际设备名，便于确认运行在独显而非核显（CUDA 只索引 NVIDIA GPU）
    device_desc = device
    if device.startswith("cuda"):
        device_desc += f" ({torch.cuda.get_device_name(device)})"
    logger.info(f"使用设备: {device_desc}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qwen_tts_dir = os.path.normpath(os.path.join(script_dir, '..', 'Qwen3-TTS'))
    
    if os.path.isabs(args.model_dir):
        model_dir = args.model_dir
    else:
        model_dir = os.path.normpath(os.path.join(qwen_tts_dir, args.model_dir))
    
    if not os.path.exists(model_dir):
        logger.error(f"模型目录不存在: {model_dir}")
        sys.exit(1)
    
    logger.info(f"加载模型: {model_dir}")
    
    sys.path.insert(0, qwen_tts_dir)
    from qwen_tts import Qwen3TTSModel
    
    model = Qwen3TTSModel.from_pretrained(
        model_dir,
        device_map=device,
        dtype=torch.bfloat16,
    )
    
    logger.info("模型加载完成，开始生成配音...")
    
    x_vector_only_mode = (args.mode == "xvec_only")
    
    if args.prompt_text:
        ref_text = args.prompt_text
    else:
        if not x_vector_only_mode:
            logger.warning("ICL模式需要参考文本，自动切换到 xvec_only 模式")
            x_vector_only_mode = True
    
    voice_clone_prompt = model.create_voice_clone_prompt(
        ref_audio=args.prompt_speech_path,
        ref_text=args.prompt_text,
        x_vector_only_mode=x_vector_only_mode,
    )
    
    audio_segments = []
    current_position_ms = 0
    
    # 配音过长时允许提前起始、借用前方静音的最大时长
    MAX_LEAD_MS = 1000
    
    gen_kwargs = dict(
        max_new_tokens=2048,
        do_sample=True,
        top_k=50,
        top_p=1.0,
        temperature=0.9,
        repetition_penalty=1.05,
    )
    
    # ===== 阶段一：批量生成所有配音段（提速关键）=====
    # Qwen3-TTS 的 generate_voice_clone 原生支持批量：一次 generate 同时生成多段，
    # 将逐段生成的调度/启动开销摊薄到 batch 内，GPU 利用率显著提升。
    # 参考音频（voice_clone_prompt）只有一份，generate 内部会按 batch 大小自动复制。
    # 显存不足(OOM)时可将 BATCH_SIZE 调小（如 2）。
    BATCH_SIZE = 4
    wavs = [None] * len(subtitles)
    
    for batch_start in range(0, len(subtitles), BATCH_SIZE):
        batch = subtitles[batch_start:batch_start + BATCH_SIZE]
        texts = [s['text'] for s in batch]
        languages = [detect_language(s['text']) for s in batch]
        logger.info(f"批量生成第 {batch_start+1}-{batch_start+len(batch)} 段（共 {len(subtitles)} 段）...")
        
        batch_wavs = None
        batch_sr = SAMPLE_RATE
        try:
            batch_wavs, batch_sr = model.generate_voice_clone(
                text=texts,
                language=languages,
                voice_clone_prompt=voice_clone_prompt,
                **gen_kwargs,
            )
        except Exception as e:
            logger.warning(f"  批量生成失败({e})，逐段重试本批...")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            batch_wavs = []
            for t, l in zip(texts, languages):
                try:
                    w, _ = model.generate_voice_clone(
                        text=t,
                        language=l,
                        voice_clone_prompt=voice_clone_prompt,
                        **gen_kwargs,
                    )
                    batch_wavs.append(w[0] if (w and len(w) > 0) else None)
                except Exception:
                    batch_wavs.append(None)
        
        for j, w in enumerate(batch_wavs):
            idx = batch_start + j
            if w is None:
                logger.error(f"  [{idx+1}/{len(subtitles)}] 生成失败，该段保持静音")
                wavs[idx] = None
                continue
            wav = w
            if isinstance(wav, torch.Tensor):
                wav = wav.detach().cpu().numpy()
            if wav.dtype != np.float32:
                wav = wav.astype(np.float32)
            if batch_sr != SAMPLE_RATE:
                import librosa
                wav = librosa.resample(wav, orig_sr=batch_sr, target_sr=SAMPLE_RATE)
            wavs[idx] = wav
            logger.info(f"[{idx+1}/{len(subtitles)}] 处理字幕: {subtitles[idx]['text'][:30]}...")
    
    # ===== 阶段二：自然语速优先的时间对齐（局部借时间 + 语速平滑）=====
    # 旧实现：逐句平移 + 末尾「整段统一倍速」(tempo = 总TTS/总视频)。
    # 新实现见 tts_alignment.py：
    #   - 超时的片段向窗口内邻居借用空闲时间（优先利用原始静音），
    #     速度回落到舒适区，避免整段被统一加速；
    #   - 仅在真正全局溢出时才做有上限(HARD_MAX)的平滑压缩；
    #   - 相邻语速做平滑，避免忽快忽慢；
    #   - 逐段 time-stretch 拼接，并输出对齐报告与质量检查。
    import sys as _sys
    _repo_root = os.path.dirname(script_dir)
    if _repo_root not in _sys.path:
        _sys.path.insert(0, _repo_root)
    from tts_alignment import AlignmentConfig, Segment, compute_alignment, apply_audio_stretch

    video_duration_s = args.video_duration_ms / 1000.0 if args.video_duration_ms else None

    segments = []
    for i, sub in enumerate(subtitles):
        wav = wavs[i]
        if wav is None:
            dur = sub['duration'] / 1000.0
            wav = generate_silence(dur * 1000) if dur > 0 else np.zeros(0, dtype=np.float32)
        else:
            if isinstance(wav, torch.Tensor):
                wav = wav.detach().cpu().numpy()
            if isinstance(wav, np.ndarray):
                wav = wav.astype(np.float32)
            else:
                wav = np.array(wav, dtype=np.float32)
            # 挤压静音：先裁剪配音首尾静音，得到真实 TTS 时长
            wav = trim_silence(wav, SAMPLE_RATE)
        dur = len(wav) / SAMPLE_RATE
        segments.append(Segment(
            id=i,
            text=sub['text'],
            original_start=sub['start_time'] / 1000.0,
            original_end=sub['end_time'] / 1000.0,
            tts_duration=dur,
            tts_audio=wav,
        ))

    cfg = AlignmentConfig()
    segments, report, ok, issues = compute_alignment(segments, video_duration_s, cfg)
    if not ok:
        logger.warning("对齐校验未完全通过:\n" + "\n".join(issues))
    logger.info("对齐报告:\n" + report)

    final_audio = apply_audio_stretch(segments, SAMPLE_RATE, cfg)
    
    output_file = os.path.join(args.output_dir, 'subtitle_dubbed.wav')
    sf.write(output_file, final_audio, SAMPLE_RATE)
    
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except:
        pass
    
    logger.info(f"配音生成完成: {output_file}")
    logger.info(f"总时长: {len(final_audio)/SAMPLE_RATE:.2f}秒")
    
    return output_file


if __name__ == "__main__":
    main()
