import hashlib
import json
import os
import subprocess
import uuid

import numpy as np
from flask import Blueprint, request

from backend.utils.response import fail
from backend.utils.temp_dir import get_waveform_temp_dir

waveform_bp = Blueprint('waveform', __name__, url_prefix='/api/waveform')


class WaveformError(RuntimeError):
    """波形提取失败(ffmpeg 缺失/转码失败/音频解析失败等)"""


def _cache_key(file_path, samples_per_second):
    """缓存键:绝对路径 + mtime + 采样率。文件被修改后自动失效。"""
    stat = os.stat(file_path)
    raw = f'{os.path.normcase(os.path.abspath(file_path))}|{stat.st_mtime_ns}|{stat.st_size}|{samples_per_second}'
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _load_cached(cache_key):
    path = os.path.join(get_waveform_temp_dir(), f'{cache_key}.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _store_cached(cache_key, waveform_data):
    path = os.path.join(get_waveform_temp_dir(), f'{cache_key}.json')
    tmp_path = path + f'.{uuid.uuid4()}.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(waveform_data, f)
        os.replace(tmp_path, path)
    except OSError:
        # 缓存写入失败不影响主流程
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _convert_to_wav(file_path):
    """非 WAV 输入统一转码为 8kHz 单声道 PCM WAV,返回临时文件路径。"""
    audio_path = os.path.join(get_waveform_temp_dir(), f'{uuid.uuid4()}.wav')
    try:
        result = subprocess.run([
            'ffmpeg', '-y', '-i', file_path,
            '-ac', '1',
            '-ar', '8000',
            '-acodec', 'pcm_s16le',
            audio_path
        ], capture_output=True, text=True, timeout=60,
           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        if result.returncode != 0:
            raise WaveformError('音频提取失败: ' + result.stderr[-500:])
        return audio_path
    except subprocess.TimeoutExpired:
        raise WaveformError('音频提取超时')
    except FileNotFoundError:
        raise WaveformError('请安装 ffmpeg')


def _compute_peaks(samples, samples_needed, dtype_max):
    """numpy 分块峰值计算:每块幅度 = (max - min) / 2 / dtype_max。

    相比逐样本 Python 循环,内存从 Python int 列表降为紧凑 ndarray,
    速度提升 1-2 个数量级(小时级音频从数十秒降到亚秒)。
    """
    total = len(samples)
    if total == 0 or samples_needed <= 0:
        return []
    # 每块起止索引(处理 total < samples_needed 时部分块为空的情况)
    starts = (np.arange(samples_needed) * total) // samples_needed
    ends = ((np.arange(samples_needed) + 1) * total) // samples_needed
    # reduceat 对重复起点(空块)返回该位置元素值 → max-min=0,与旧行为一致
    starts_clamped = np.minimum(starts, total - 1)
    maxs = np.maximum.reduceat(samples, starts_clamped)
    mins = np.minimum.reduceat(samples, starts_clamped)
    amplitude = (maxs - mins) / 2.0 / dtype_max
    # 空块(ends <= starts)幅度归零
    amplitude[ends <= starts] = 0.0
    return np.round(amplitude, 6).tolist()


def extract_waveform(file_path, samples_per_second=100):
    """提取波形峰值数据。失败抛 WaveformError,由路由层统一处理。

    结果按「绝对路径 + mtime + 大小 + 采样率」缓存到 Temp/waveform,
    同一视频重复打开不再重新 ffmpeg 转码与重算。
    """
    cache_key = _cache_key(file_path, samples_per_second)
    cached = _load_cached(cache_key)
    if cached is not None:
        return cached

    # wave 模块仅支持 WAV,其余容器先转码
    temp_wav = None
    try:
        if file_path.lower().endswith('.wav'):
            audio_path = file_path
        else:
            temp_wav = _convert_to_wav(file_path)
            audio_path = temp_wav

        import wave
        try:
            with wave.open(audio_path, 'rb') as wav:
                channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                framerate = wav.getframerate()
                n_frames = wav.getnframes()

                if framerate <= 0 or n_frames <= 0:
                    raise WaveformError('音频数据为空')

                duration = n_frames / framerate
                frames = wav.readframes(n_frames)
        except wave.Error as e:
            raise WaveformError(f'音频解析失败: {e}')

        # numpy 直接从原始字节解码,避免 struct.unpack 生成 Python int 列表
        if sample_width == 2:
            samples = np.frombuffer(frames, dtype=np.int16)
            dtype_max = 32768.0
        elif sample_width == 1:
            samples = np.frombuffer(frames, dtype=np.int8)
            dtype_max = 128.0
        else:
            raise WaveformError(f'不支持的采样位宽: {sample_width * 8} bit')

        if channels == 2:
            samples = samples[::2]

        samples_needed = max(1, int(duration * samples_per_second))
        waveform = _compute_peaks(samples, samples_needed, dtype_max)

        result = {
            'data': waveform,
            'duration': duration,
            'samples_per_second': samples_per_second
        }
        _store_cached(cache_key, result)
        return result
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.unlink(temp_wav)
            except OSError:
                pass


def _waveform_response(file_path, samples_per_second):
    try:
        waveform_data = extract_waveform(file_path, samples_per_second)
    except WaveformError as e:
        return fail(str(e), error_code='WAVEFORM_FAILED', status=500)
    return {
        'waveform': waveform_data,
        'duration': waveform_data['duration']
    }


@waveform_bp.route('/generate', methods=['POST'])
def generate_waveform():
    if 'file' not in request.files:
        return fail('请上传文件', error_code='FILE_REQUIRED', status=400)

    upload_file = request.files['file']
    try:
        samples_per_second = int(request.form.get('samples_per_second', 100))
    except ValueError:
        return fail('samples_per_second 必须为整数', error_code='INVALID_PARAM', status=400)

    ext = os.path.splitext(upload_file.filename)[1].lower()
    tmp_path = os.path.join(get_waveform_temp_dir(), f"{uuid.uuid4()}{ext}")
    upload_file.save(tmp_path)

    try:
        return _waveform_response(tmp_path, samples_per_second)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@waveform_bp.route('/generate-from-path', methods=['POST'])
def generate_waveform_from_path():
    data = request.get_json() or {}
    file_path = data.get('file_path')
    if not file_path:
        return fail('请提供文件路径', error_code='FILE_PATH_REQUIRED', status=400)

    if not os.path.exists(file_path):
        return fail('文件不存在', error_code='FILE_NOT_FOUND', status=400)

    try:
        samples_per_second = int(data.get('samples_per_second', 100))
    except (TypeError, ValueError):
        return fail('samples_per_second 必须为整数', error_code='INVALID_PARAM', status=400)

    return _waveform_response(file_path, samples_per_second)
