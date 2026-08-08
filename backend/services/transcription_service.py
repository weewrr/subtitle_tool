import copy
import importlib
import json
import logging
import os
import subprocess
import threading
import time
import uuid
import wave

import numpy as np

from backend.config.settings import Config
from backend.utils.temp_dir import get_transcription_temp_dir
from backend.utils.time_utils import format_time_srt

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Background transcription jobs with per-job progress and event delivery."""

    def __init__(self):
        self._jobs = {}
        self._lock = threading.RLock()
        self._event = threading.Condition(self._lock)
        # whisper patches tqdm at module scope; serialize this engine while the
        # temporary progress bridge is installed.
        self._openai_transcribe_lock = threading.Lock()

    def _new_job(self, file_path, model_name, language, engine, use_gpu):
        task_id = str(uuid.uuid4())
        job = {
            'task_id': task_id, 'transcribing': True, 'status': 'queued',
            'phase': 'queued', 'progress': 0, 'error': None, 'result': None,
            'media_duration': None, 'processed_seconds': 0, 'eta_seconds': None,
            'created_at': time.time(), 'updated_at': time.time(),
            'cancel_requested': False, 'file_path': file_path,
            'model_name': model_name, 'language': language, 'engine': engine,
            'use_gpu': use_gpu,
        }
        self._jobs[task_id] = job
        return task_id

    def _public_job(self, job):
        data = {key: value for key, value in job.items() if key not in {'result', 'file_path'}}
        return copy.deepcopy(data)

    def _update_job(self, task_id, **changes):
        with self._event:
            job = self._jobs.get(task_id)
            if not job:
                return False
            job.update(changes)
            job['updated_at'] = time.time()
            self._event.notify_all()
            return bool(job.get('cancel_requested'))

    def _is_cancelled(self, task_id):
        with self._lock:
            return self._jobs.get(task_id, {}).get('cancel_requested', True)

    def _get_media_duration(self, file_path):
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return max(0.0, float(result.stdout.strip()))
        except (FileNotFoundError, subprocess.SubprocessError, ValueError):
            return None

    def _extract_audio(self, task_id, video_path, audio_path, duration):
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        command = ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000', '-progress', 'pipe:1', '-nostats', audio_path]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        try:
            for line in process.stdout:
                if self._is_cancelled(task_id):
                    process.terminate()
                    raise RuntimeError('任务已取消')
                key, _, value = line.strip().partition('=')
                if key == 'out_time_ms' and duration:
                    seconds = int(value) / 1_000_000
                    self._update_job(task_id, phase='extracting_audio', status='extracting_audio', processed_seconds=seconds,
                                     progress=min(10, round(seconds / duration * 10, 1)))
            _, stderr = process.communicate()
            if process.returncode != 0:
                raise RuntimeError(f'音频提取失败: {stderr[-500:]}')
        finally:
            if process.poll() is None:
                process.kill()

    def transcribe_async(self, file_path, model_name='base', language=None, engine='openai', use_gpu=True):
        with self._lock:
            task_id = self._new_job(file_path, model_name, language, engine, use_gpu)
        threading.Thread(target=self._transcribe_thread, args=(task_id,), daemon=True).start()
        return {'task_id': task_id, 'status': 'started'}

    def _transcribe_thread(self, task_id):
        temp_audio_path = None
        try:
            with self._lock:
                job = self._jobs[task_id]
                file_path, model_name, language = job['file_path'], job['model_name'], job['language']
                engine, use_gpu = job['engine'], job['use_gpu']
            duration = self._get_media_duration(file_path)
            self._update_job(task_id, media_duration=duration)
            # Normalize every input to a known PCM format. OpenAI Whisper then
            # receives samples directly, avoiding its own ffmpeg/path handling.
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f'{uuid.uuid4()}.wav')
            self._update_job(task_id, phase='extracting_audio', status='extracting_audio', progress=0)
            self._extract_audio(task_id, file_path, temp_audio_path, duration)
            audio_path = temp_audio_path
            if self._is_cancelled(task_id):
                raise RuntimeError('任务已取消')
            self._update_job(task_id, phase='loading_model', status='loading_model', progress=max(10, self.get_status(task_id)['progress']))
            result = self._transcribe_file(task_id, audio_path, model_name, language, engine, use_gpu, duration)
            if self._is_cancelled(task_id):
                raise RuntimeError('任务已取消')
            self._update_job(task_id, phase='generating_subtitles', status='generating_subtitles', progress=98)
            self._update_job(task_id, transcribing=False, phase='completed', status='completed', progress=100, result=result,
                             processed_seconds=duration or self.get_status(task_id)['processed_seconds'], eta_seconds=0)
        except Exception as exc:
            logger.exception('转录任务 %s 失败', task_id)
            cancelled = self._is_cancelled(task_id)
            self._update_job(task_id, transcribing=False, phase='cancelled' if cancelled else 'error',
                             status='cancelled' if cancelled else 'error', error=None if cancelled else str(exc), progress=0 if cancelled else self.get_status(task_id)['progress'])
        finally:
            # 只清理临时音频文件，不删除原始文件
            for path in (temp_audio_path,):
                if path and os.path.exists(path):
                    try: os.unlink(path)
                    except OSError: pass

    def _language_code(self, language):
        if not language or language.lower() == 'auto-detect': return None
        return {'english': 'en', 'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko'}.get(language.lower(), language.lower())

    def _transcribe_file(self, task_id, audio_path, model_name, language, engine, use_gpu, duration):
        lang_code = self._language_code(language)
        self._update_job(task_id, phase='transcribing', status='transcribing', progress=max(15, self.get_status(task_id)['progress']))
        if engine == 'whisper-ctranslate2':
            from backend.services.whisper_ctranslate2_service import WhisperCTranslate2Service
            service = WhisperCTranslate2Service()
            return self._parse_srt(service.transcribe(audio_path, model_name, lang_code, use_gpu,
                progress_callback=lambda seconds: self._recognition_progress(task_id, seconds, duration),
                is_cancelled=lambda: self._is_cancelled(task_id))['srt'])
        if engine == 'whisper-cpp':
            from backend.services.whisper_cpp_service import WhisperCppService
            result = WhisperCppService().transcribe(
                audio_path, model_name, lang_code,
                progress_callback=lambda percent: self._recognition_frame_progress(task_id, percent, 100, duration),
                is_cancelled=lambda: self._is_cancelled(task_id)
            )
            self._recognition_progress(task_id, duration or 0, duration)
            return self._parse_srt(result['srt'])
        return self._transcribe_with_openai(task_id, audio_path, model_name, lang_code, use_gpu, duration)

    def _recognition_progress(self, task_id, processed_seconds, duration):
        progress = 15 if not duration else min(95, round(15 + processed_seconds / duration * 80, 1))
        elapsed = max(0.1, time.time() - self.get_status(task_id)['created_at'])
        eta = max(0, round((duration - processed_seconds) / max(processed_seconds / elapsed, 0.001))) if duration and processed_seconds else None
        self._update_job(task_id, phase='transcribing', status='transcribing', progress=progress, processed_seconds=processed_seconds, eta_seconds=eta)

    def _recognition_frame_progress(self, task_id, processed_frames, total_frames, duration):
        if not total_frames:
            return
        ratio = min(1.0, max(0.0, processed_frames / total_frames))
        processed_seconds = (duration * ratio) if duration else 0
        progress = round(15 + ratio * 80, 1)
        elapsed = max(0.1, time.time() - self.get_status(task_id)['created_at'])
        eta = round((elapsed / ratio - elapsed)) if ratio else None
        self._update_job(task_id, phase='transcribing', status='transcribing', progress=progress,
                         processed_seconds=processed_seconds, eta_seconds=max(0, eta) if eta is not None else None)

    def _transcribe_with_openai(self, task_id, audio_path, model_name, language, use_gpu, duration):
        import torch
        import whisper
        device = 'cuda' if (use_gpu and torch.cuda.is_available() and torch.backends.cudnn.is_available()) else 'cpu'
        model = whisper.load_model(model_name, device=device, download_root=Config.WHISPER_CACHE_DIR)
        self._update_job(task_id, phase='transcribing', status='transcribing', progress=15)
        audio = self._load_normalized_wav(audio_path)
        # The upstream implementation uses tqdm with real mel-frame counts.
        # Bridge those counts into this task's SSE status instead of discarding them.
        whisper_transcribe = importlib.import_module('whisper.transcribe')
        original_tqdm = whisper_transcribe.tqdm.tqdm
        service = self

        class ProgressBridge:
            def __init__(self, *args, **kwargs):
                # tqdm writing to Electron's inherited Windows console handle can
                # raise OSError(22).  We only need its update calls, not its UI.
                kwargs['disable'] = True
                self._bar = original_tqdm(*args, **kwargs)
                self._total = self._bar.total or kwargs.get('total')
                self._processed = 0

            def update(self, amount=1):
                self._processed += amount
                result = self._bar.update(amount)
                service._recognition_frame_progress(task_id, self._processed, self._total, duration)
                return result

            def __enter__(self):
                self._bar.__enter__()
                return self

            def __exit__(self, *args):
                return self._bar.__exit__(*args)

            def __getattr__(self, name):
                return getattr(self._bar, name)

        with self._openai_transcribe_lock:
            whisper_transcribe.tqdm.tqdm = ProgressBridge
            try:
                result = model.transcribe(audio, language=language, verbose=False, word_timestamps=True, fp16=device == 'cuda', temperature=0.0, best_of=5, beam_size=5)
            finally:
                whisper_transcribe.tqdm.tqdm = original_tqdm
        self._recognition_progress(task_id, duration or 0, duration)
        return self._generate_srt(result)

    @staticmethod
    def _load_normalized_wav(audio_path):
        with wave.open(audio_path, 'rb') as audio_file:
            if audio_file.getnchannels() != 1 or audio_file.getsampwidth() != 2 or audio_file.getframerate() != 16000:
                raise RuntimeError('标准化音频格式异常，期望 16 kHz 单声道 PCM WAV')
            samples = np.frombuffer(audio_file.readframes(audio_file.getnframes()), dtype=np.int16)
        return samples.astype(np.float32) / 32768.0

    def _parse_srt(self, srt_content):
        segments, lines, i = [], srt_content.strip().splitlines(), 0
        while i < len(lines):
            if lines[i].strip().isdigit() and i + 1 < len(lines) and ' --> ' in lines[i + 1]:
                start, end = lines[i + 1].split(' --> '); i += 2; text = []
                while i < len(lines) and lines[i].strip(): text.append(lines[i].strip()); i += 1
                segments.append({'start': self._srt_time_to_seconds(start), 'end': self._srt_time_to_seconds(end), 'text': ' '.join(text)})
            i += 1
        return {'text': ' '.join(item['text'] for item in segments), 'srt': srt_content, 'segments': segments, 'language': 'unknown'}

    @staticmethod
    def _srt_time_to_seconds(value):
        hours, minutes, seconds = value.replace(',', '.').split(':')
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    def _generate_srt(self, result):
        segments, rows = [], []
        for index, segment in enumerate(result.get('segments', []), 1):
            text = segment['text'].strip()
            if text:
                segments.append({'start': segment['start'], 'end': segment['end'], 'text': text})
                rows.extend([str(index), f"{format_time_srt(segment['start'])} --> {format_time_srt(segment['end'])}", text, ''])
        return {'text': result.get('text', ''), 'srt': '\n'.join(rows), 'segments': segments, 'language': result.get('language', 'unknown')}

    def get_status(self, task_id):
        with self._lock:
            job = self._jobs.get(task_id)
            return self._public_job(job) if job else None

    def get_result(self, task_id):
        with self._lock:
            job = self._jobs.get(task_id)
            return copy.deepcopy(job.get('result')) if job else None

    def cancel(self, task_id):
        return self._update_job(task_id, cancel_requested=True, status='cancelling', phase='cancelling')

    def event_stream(self, task_id):
        last_payload = None
        while True:
            with self._event:
                job = self._jobs.get(task_id)
                if not job: return
                payload = json.dumps(self._public_job(job), ensure_ascii=False)
                terminal = job['status'] in {'completed', 'error', 'cancelled'}
                if payload == last_payload and not terminal:
                    self._event.wait(timeout=15)
                    continue
            last_payload = payload
            yield f'data: {payload}\n\n'
            if terminal: return
