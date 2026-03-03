from backend.routes.whisper import whisper_bp
from backend.routes.vosk import vosk_bp
from backend.routes.transcription import transcription_bp
from backend.routes.subtitle import subtitle_bp
from backend.routes.translation import translation_bp
from backend.routes.spell_check import spell_check_bp
from backend.routes.hard_subtitle import hard_subtitle_bp
from backend.routes.waveform import waveform_bp
from backend.routes.tts import tts_bp
from backend.routes.video import video_bp

__all__ = [
    'whisper_bp',
    'vosk_bp',
    'transcription_bp',
    'subtitle_bp',
    'translation_bp',
    'spell_check_bp',
    'hard_subtitle_bp',
    'waveform_bp',
    'tts_bp',
    'video_bp'
]
