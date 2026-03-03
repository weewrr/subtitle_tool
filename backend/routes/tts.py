import os
import io
import soundfile as sf
from flask import Blueprint, request, jsonify, send_file
from backend.services.spark_tts_service import spark_tts_service
from backend.utils.temp_dir import get_tts_temp_dir

tts_bp = Blueprint('tts', __name__, url_prefix='/api/tts')

@tts_bp.route('/info', methods=['GET'])
def get_info():
    try:
        info = spark_tts_service.get_model_info()
        return jsonify({
            'success': True,
            'loaded': info['loaded'],
            'model_dir': info['model_dir'],
            'spark_tts_root': info['spark_tts_root']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/generate-subtitles', methods=['POST'])
def generate_subtitle_audio():
    try:
        data = request.get_json()
        
        subtitles = data.get('subtitles', [])
        gender = data.get('gender', 'male')
        pitch = data.get('pitch', 'moderate')
        speed = data.get('speed', 'moderate')
        prompt_speech_path = data.get('prompt_speech_path')
        prompt_text = data.get('prompt_text')
        
        if not subtitles:
            return jsonify({
                'success': False,
                'error': 'Subtitles are required'
            }), 400
        
        result = spark_tts_service.generate_subtitle_audio_async(
            subtitles,
            gender=gender,
            pitch=pitch,
            speed=speed,
            prompt_speech_path=prompt_speech_path,
            prompt_text=prompt_text
        )
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
        return jsonify({
            'success': True,
            'status': result['status'],
            'message': result['message']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/status', methods=['GET'])
def get_status():
    try:
        status = spark_tts_service.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/result', methods=['GET'])
def get_result():
    try:
        result = spark_tts_service.get_result()
        if result:
            return jsonify({
                'success': True,
                'output_path': result
            })
        return jsonify({
            'success': False,
            'error': 'No result available'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/abort', methods=['POST'])
def abort_generation():
    try:
        spark_tts_service.abort()
        return jsonify({
            'success': True,
            'message': 'Generation aborted'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/download/<path:filename>', methods=['GET'])
def download_audio(filename):
    try:
        tts_temp = get_tts_temp_dir()
        
        for root, dirs, files in os.walk(tts_temp):
            for f in files:
                if f == filename or f.endswith('_dubbed.wav'):
                    file_path = os.path.join(root, f)
                    return send_file(
                        file_path,
                        mimetype='audio/wav',
                        as_attachment=True
                    )
        
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
