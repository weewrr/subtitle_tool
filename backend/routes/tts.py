import os
import io
import subprocess
import soundfile as sf
from flask import Blueprint, request, jsonify, send_file
from backend.services.spark_tts_service import spark_tts_service
from backend.utils.temp_dir import get_tts_temp_dir
from backend.config.settings import Config

tts_bp = Blueprint('tts', __name__, url_prefix='/api/tts')

def _get_video_duration_ms(video_path):
    """
    用 ffprobe 获取视频/音频文件时长（毫秒）。
    失败或路径无效时返回 None（配音脚本将跳过整体变速）。
    """
    if not video_path or not isinstance(video_path, str) or not os.path.exists(video_path):
        return None
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode != 0:
            return None
        duration_s = float(result.stdout.strip())
        return int(duration_s * 1000)
    except (ValueError, OSError):
        return None

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

@tts_bp.route('/engines', methods=['GET'])
def get_engines():
    """获取可用的TTS引擎列表"""
    return jsonify({
        'success': True,
        'engines': spark_tts_service.get_available_engines()
    })

@tts_bp.route('/generate-subtitles', methods=['POST'])
def generate_subtitle_audio():
    try:
        data = request.get_json()
        
        subtitles = data.get('subtitles', [])
        prompt_speech_path = data.get('prompt_speech_path')
        prompt_text = data.get('prompt_text')
        engine = data.get('engine', 'spark-tts')
        mode = data.get('mode', 'icl')
        video_path = data.get('video_path')
        # 配音总长超过视频长度时，配音脚本会整体加速压回视频长度。
        # 时长来源优先级：
        # 1) 前端从播放器 video 元素读取的时长（精确，浏览器/Electron 通用）
        # 2) ffprobe 从视频路径提取（Electron 路径模式）
        # 3) 最后一条字幕的结束时间（永远可用：字幕来自视频识别时即近似视频长度，
        #    配音超出该末端说明时间轴放不下，压回该末端语义正确）
        video_duration_ms = data.get('video_duration_ms') or _get_video_duration_ms(video_path)
        if not video_duration_ms and subtitles:
            try:
                video_duration_ms = max(int(s.get('end_time', 0)) for s in subtitles)
                print(f"[TTS ROUTE] using last subtitle end as duration: {video_duration_ms} ms")
            except (TypeError, ValueError):
                video_duration_ms = None
        
        print(f"\n{'='*60}")
        print(f"[TTS ROUTE] Received request from frontend:")
        print(f"  - subtitles count: {len(subtitles)}")
        print(f"  - prompt_speech_path: {prompt_speech_path}")
        print(f"  - prompt_text: {prompt_text}")
        print(f"  - engine: {engine}")
        print(f"  - mode: {mode}")
        print(f"  - video_path: {video_path}")
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
        
        # 配音总长超过视频长度时，配音脚本会整体加速压回视频长度。
        # video_duration_ms 已在上方按「前端播放器值 → ffprobe 路径 → 字幕末端」的
        # 优先级确定，此处不可再用 ffprobe 覆盖，否则浏览器模式下（无 video_path）
        # 会把它重置为 None，导致整体变速失效。
        if video_duration_ms:
            print(f"[TTS ROUTE] final video_duration_ms for tempo: {video_duration_ms} ms")
        
        result = spark_tts_service.generate_subtitle_audio_async(
            subtitles,
            prompt_speech_path=prompt_speech_path,
            prompt_text=prompt_text,
            engine=engine,
            mode=mode,
            video_duration_ms=video_duration_ms
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
