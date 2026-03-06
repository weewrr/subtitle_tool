import os
import io
import soundfile as sf
from flask import Blueprint, request, jsonify, send_file
from backend.services.spark_tts_service import spark_tts_service
from backend.utils.temp_dir import get_tts_temp_dir
from backend.config.settings import Config

tts_bp = Blueprint('tts', __name__, url_prefix='/api/tts')

def get_speech_dir():
    """获取 speech 目录路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    speech_dir = os.path.normpath(os.path.join(base_dir, 'Spark-TTS', 'speech'))
    os.makedirs(speech_dir, exist_ok=True)
    return speech_dir

@tts_bp.route('/voices', methods=['GET'])
def list_voices():
    """列出 speech 目录下的音频文件"""
    try:
        speech_dir = get_speech_dir()
        voices = []
        
        if os.path.exists(speech_dir):
            for file in os.listdir(speech_dir):
                if file.lower().endswith(('.wav', '.mp3', '.ogg', '.m4a', '.flac')):
                    file_path = os.path.join(speech_dir, file)
                    file_size = os.path.getsize(file_path)
                    voices.append({
                        'name': os.path.splitext(file)[0],
                        'filename': file,
                        'path': file_path,
                        'size': file_size,
                        'type': 'reference'
                    })
        
        return jsonify({
            'success': True,
            'voices': voices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/upload-voice', methods=['POST'])
def upload_voice():
    """上传参考音频到 speech 目录"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '请上传音频文件'
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        allowed_extensions = ['.wav', '.mp3', '.ogg', '.m4a', '.flac']
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': '不支持的音频格式'
            }), 400
        
        speech_dir = get_speech_dir()
        filename = f"{os.path.splitext(file.filename)[0]}{ext}"
        file_path = os.path.join(speech_dir, filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'voice': {
                'name': os.path.splitext(file.filename)[0],
                'filename': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'type': 'reference'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/delete-voice/<filename>', methods=['DELETE'])
def delete_voice(filename):
    """删除参考音频"""
    try:
        speech_dir = get_speech_dir()
        file_path = os.path.join(speech_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tts_bp.route('/info', methods=['GET'])
def get_info():
    """获取模型信息"""
    return jsonify({
        'success': True,
        **spark_tts_service.get_model_info()
    })

@tts_bp.route('/status', methods=['GET'])
def get_status():
    """获取生成状态"""
    return jsonify(spark_tts_service.get_status())

@tts_bp.route('/result', methods=['GET'])
def get_result():
    """获取生成结果"""
    return jsonify(spark_tts_service.get_result())

@tts_bp.route('/download/<filename>', methods=['GET'])
def download_audio(filename):
    """下载生成的音频"""
    try:
        temp_dir = get_tts_temp_dir()
        for subdir in os.listdir(temp_dir):
            subdir_path = os.path.join(temp_dir, subdir)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file == filename or file.endswith('_dubbed.wav'):
                        file_path = os.path.join(subdir_path, file)
                        if os.path.exists(file_path):
                            return send_file(file_path, as_attachment=True, download_name=filename)
        
        return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tts_bp.route('/abort', methods=['POST'])
def abort_generation():
    """中止生成"""
    spark_tts_service.abort()
    return jsonify({'success': True, 'message': '已中止生成'})

@tts_bp.route('/generate-subtitles', methods=['POST'])
def generate_subtitle_audio():
    try:
        data = request.get_json()
        
        subtitles = data.get('subtitles', [])
        prompt_speech_path = data.get('prompt_speech_path')
        prompt_text = data.get('prompt_text')
        
        print(f"\n{'='*60}")
        print(f"[TTS ROUTE] Received request from frontend:")
        print(f"  - subtitles count: {len(subtitles)}")
        print(f"  - prompt_speech_path: {prompt_speech_path}")
        print(f"  - prompt_text: {prompt_text}")
        print(f"  - prompt_speech_path type: {type(prompt_speech_path)}")
        print(f"{'='*60}\n")
        
        if not subtitles:
            return jsonify({
                'success': False,
                'error': 'Subtitles are required'
            }), 400
        
        if not prompt_speech_path:
            return jsonify({
                'success': False,
                'error': '请选择参考音频'
            }), 400
        
        if not os.path.exists(prompt_speech_path):
            return jsonify({
                'success': False,
                'error': f'参考音频不存在: {prompt_speech_path}'
            }), 400
        
        result = spark_tts_service.generate_subtitle_audio_async(
            subtitles,
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
            'status': 'started',
            'message': '生成任务已启动'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
