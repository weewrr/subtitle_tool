from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.config.settings import Config
from backend.routes import (
    whisper_bp,
    vosk_bp,
    transcription_bp,
    subtitle_bp,
    translation_bp,
    spell_check_bp,
    hard_subtitle_bp,
    waveform_bp,
    tts_bp,
    video_bp
)

def create_app():
    app = Flask(__name__, static_folder='.')
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    app.register_blueprint(whisper_bp)
    app.register_blueprint(vosk_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(subtitle_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(spell_check_bp)
    app.register_blueprint(hard_subtitle_bp)
    app.register_blueprint(waveform_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(video_bp)
    
    @app.route('/')
    def index():
        return send_from_directory('.', 'index.html')
    
    @app.route('/<path:path>')
    def static_files(path):
        return send_from_directory('.', path)
    
    return app
