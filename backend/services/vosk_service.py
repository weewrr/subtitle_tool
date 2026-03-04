import os
import sys
import subprocess
import threading
import zipfile
import requests
import uuid
from backend.config.settings import Config
from backend.utils.temp_dir import get_transcription_temp_dir


class VoskService:
    def __init__(self):
        self.download_status = {
            'downloading': False,
            'progress': 0,
            'status': 'idle',
            'error': None
        }
        self.models = self._get_vosk_models()
    
    def _get_vosk_models(self):
        return [
            {"code": "en", "name": "English (medium size, 128 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip"},
            {"code": "en-large", "name": "English (very large, 1.8 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"},
            {"code": "cn", "name": "Chinese (small, 42 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"},
            {"code": "cn-large", "name": "Chinese (very large, 1.3 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"},
            {"code": "fr", "name": "French (small, 39 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-fr-pguyot-0.3.zip"},
            {"code": "fr-large", "name": "French (large, 1.4 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip"},
            {"code": "es", "name": "Spanish (small, 39 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"},
            {"code": "es-large", "name": "Spanish (large, 1.4 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip"},
            {"code": "ko", "name": "Korean (small, 83 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip"},
            {"code": "de", "name": "German (small, 45 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip"},
            {"code": "de-large", "name": "German (large, 1.9 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip"},
            {"code": "pt", "name": "Portuguese (small, 31 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"},
            {"code": "pt-large", "name": "Portuguese (large, 1.6 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-pt-fb-v0.1.1-20220516_2113.zip"},
            {"code": "it", "name": "Italian (small, 48 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip"},
            {"code": "it-large", "name": "Italian (large, 1.2 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-it-0.22.zip"},
            {"code": "nl", "name": "Dutch (large, 860 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-nl-spraakherkenning-0.6-lgraph.zip"},
            {"code": "sv", "name": "Swedish", "url": "https://alphacephei.com/vosk/models/vosk-model-small-sv-rhasspy-0.15.zip"},
            {"code": "ru", "name": "Russian (small, 45 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"},
            {"code": "ru-large", "name": "Russian (large, 1.8 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"},
            {"code": "fa", "name": "Farsi", "url": "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip"},
            {"code": "tr", "name": "Turkish", "url": "https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip"},
            {"code": "el", "name": "Greek", "url": "https://alphacephei.com/vosk/models/vosk-model-el-gr-0.7.zip"},
            {"code": "ar", "name": "Arabic (small, 318 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip"},
            {"code": "ar-large", "name": "Arabic (large, 1.3 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-ar-0.22-linto-1.1.0.zip"},
            {"code": "uk", "name": "Ukrainian (small, 133 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-small.zip"},
            {"code": "uk-medium", "name": "Ukrainian (medium, 325 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-uk-v3-lgraph.zip"},
            {"code": "uz", "name": "Uzbek (small, 49 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip"},
            {"code": "ph", "name": "Filipino", "url": "https://alphacephei.com/vosk/models/vosk-model-tl-ph-generic-0.6.zip"},
            {"code": "kz", "name": "Kazakh", "url": "https://alphacephei.com/vosk/models/vosk-model-kz-0.15.zip"},
            {"code": "jp", "name": "Japanese (small, 48 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip"},
            {"code": "jp-large", "name": "Japanese (large, 1 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-ja-0.22.zip"},
            {"code": "ca", "name": "Catalan", "url": "https://alphacephei.com/vosk/models/vosk-model-small-ca-0.4.zip"},
            {"code": "hi", "name": "Hindi (small, 42 MB)", "url": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip"},
            {"code": "hi-large", "name": "Hindi (large, 1.5 GB)", "url": "https://alphacephei.com/vosk/models/vosk-model-hi-0.22.zip"},
            {"code": "cz", "name": "Czech", "url": "https://alphacephei.com/vosk/models/vosk-model-small-cs-0.4-rhasspy.zip"},
            {"code": "pl", "name": "Polish", "url": "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip"},
            {"code": "br", "name": "Breton (small, 84 MB)", "url": "https://github.com/gweltou/patromou/releases/download/vosk-models/vosk-model-br-26.01.zip"}
        ]
    
    def get_models(self):
        return self.models
    
    def _ensure_vosk_installed(self):
        try:
            import vosk
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'vosk', '-q'])
            import vosk
        return vosk
    
    def _ensure_ffmpeg_installed(self):
        try:
            import ffmpeg
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ffmpeg-python', '-q'])
            import ffmpeg
        return ffmpeg
    
    def _extract_audio(self, video_path, audio_path):
        ffmpeg = self._ensure_ffmpeg_installed()
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path,
                    format='wav',
                    acodec='pcm_s16le',
                    ac=1,
                    ar=16000,
                    loglevel='error'
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"音频提取失败：{e.stderr.decode('utf-8') if e.stderr else str(e)}")
    
    def download_model(self, model_code):
        model = next((m for m in self.models if m['code'] == model_code), None)
        if not model:
            raise ValueError(f"模型不存在：{model_code}")
        
        model_dir = os.path.join(Config.BASE_DIR, 'Vosk')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, f"vosk-model-{model_code}")
        if os.path.exists(model_path):
            return f"模型已存在：{model_path}"
        
        zip_path = os.path.join(model_dir, f"{model_code}.zip")
        
        try:
            response = requests.get(model['url'], stream=True, timeout=600)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress = int((downloaded_size / total_size) * 100)
                        self.download_status['progress'] = progress
                        self.download_status['status'] = f"downloading {progress}%"
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_dir)
            
            os.remove(zip_path)
            
            self.download_status['status'] = 'completed'
            self.download_status['progress'] = 100
            
            return f"模型下载完成：{model_path}"
        except Exception as e:
            self.download_status['status'] = 'error'
            self.download_status['error'] = str(e)
            raise RuntimeError(f"模型下载失败：{str(e)}")
    
    def transcribe_with_vosk(self, file_path, model_code='cn', transcribe_status=None):
        vosk = self._ensure_vosk_installed()
        
        model_dir = os.path.join(Config.BASE_DIR, 'Vosk')
        model_path = os.path.join(model_dir, f"vosk-model-{model_code}")
        
        if not os.path.exists(model_path):
            self.download_model(model_code)
        
        if not file_path.endswith('.wav'):
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}.wav")
            self._extract_audio(file_path, temp_audio_path)
            audio_path = temp_audio_path
        else:
            audio_path = file_path
            temp_audio_path = None
        
        try:
            if transcribe_status:
                transcribe_status['status'] = 'loading_model'
                transcribe_status['progress'] = 10
            
            model = vosk.Model(model_path)
            
            if transcribe_status:
                transcribe_status['status'] = 'transcribing'
                transcribe_status['progress'] = 20
            
            import soundfile as sf
            data, samplerate = sf.read(audio_path)
            
            rec = vosk.KaldiRecognizer(model, samplerate)
            rec.SetWords(True)
            
            results = []
            total_chunks = len(data) // 8000 + 1
            processed_chunks = 0
            
            for i in range(0, len(data), 8000):
                chunk = data[i:i+8000]
                if rec.AcceptWaveform(chunk.tobytes()):
                    results.append(rec.Result())
                processed_chunks += 1
                
                if transcribe_status:
                    progress = 20 + int((processed_chunks / total_chunks) * 70)
                    transcribe_status['progress'] = min(progress, 90)
            
            results.append(rec.FinalResult())
            
            import json
            segments = []
            text = ""
            
            for result in results:
                res = json.loads(result)
                if 'result' in res:
                    for word in res['result']:
                        segments.append({
                            'start': word['start'],
                            'end': word['end'],
                            'text': word['word']
                        })
                        text += word['word'] + ' '
            
            sentences = []
            current_sentence = {}
            
            for segment in segments:
                if not current_sentence:
                    current_sentence = {
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text']
                    }
                else:
                    if segment['start'] - current_sentence['end'] < 0.3:
                        current_sentence['end'] = segment['end']
                        current_sentence['text'] += ' ' + segment['text']
                    else:
                        sentences.append(current_sentence)
                        current_sentence = {
                            'start': segment['start'],
                            'end': segment['end'],
                            'text': segment['text']
                        }
            
            if current_sentence:
                sentences.append(current_sentence)
            
            srt_content = ''
            for i, sentence in enumerate(sentences):
                start_time = self._format_time(sentence['start'])
                end_time = self._format_time(sentence['end'])
                srt_content += f"{i+1}\n"
                srt_content += f"{start_time} --> {end_time}\n"
                srt_content += f"{sentence['text']}\n\n"
            
            return {
                'text': text.strip(),
                'srt': srt_content,
                'segments': sentences,
                'language': model_code.split('-')[0]
            }
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
    
    def _format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def get_download_status(self):
        return self.download_status
