from flask import Blueprint, request, jsonify
import os
import subprocess
import json
import wave
import struct
import uuid

from backend.utils.temp_dir import get_waveform_temp_dir

waveform_bp = Blueprint('waveform', __name__, url_prefix='/api/waveform')

@waveform_bp.route('/generate', methods=['POST'])
def generate_waveform():
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    
    upload_file = request.files['file']
    samples_per_second = int(request.form.get('samples_per_second', 100))
    
    ext = os.path.splitext(upload_file.filename)[1].lower()
    tmp_path = os.path.join(get_waveform_temp_dir(), f"{uuid.uuid4()}{ext}")
    upload_file.save(tmp_path)
    
    try:
        waveform_data = extract_waveform(tmp_path, samples_per_second)
        return jsonify({
            'waveform': waveform_data,
            'duration': waveform_data['duration'] if isinstance(waveform_data, dict) else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

@waveform_bp.route('/generate-from-path', methods=['POST'])
def generate_waveform_from_path():
    data = request.get_json()
    if not data or 'file_path' not in data:
        return jsonify({'error': '请提供文件路径'}), 400
    
    file_path = data['file_path']
    samples_per_second = int(data.get('samples_per_second', 100))
    
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 400
    
    try:
        waveform_data = extract_waveform(file_path, samples_per_second)
        return jsonify({
            'waveform': waveform_data,
            'duration': waveform_data['duration'] if isinstance(waveform_data, dict) else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_waveform(file_path, samples_per_second=100):
    audio_path = file_path
    
    if not file_path.lower().endswith(('.wav', '.mp3', '.ogg', '.flac', '.m4a')):
        audio_path = os.path.join(get_waveform_temp_dir(), f"{uuid.uuid4()}.wav")
        try:
            result = subprocess.run([
                'ffmpeg', '-y', '-i', file_path,
                '-ac', '1',
                '-ar', '8000',
                '-acodec', 'pcm_s16le',
                audio_path
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return {'error': '音频提取失败: ' + result.stderr}
        except subprocess.TimeoutExpired:
            return {'error': '音频提取超时'}
        except FileNotFoundError:
            return {'error': '请安装 ffmpeg'}
    
    try:
        with wave.open(audio_path, 'rb') as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            
            duration = n_frames / framerate
            
            frames = wav.readframes(n_frames)
            
            if sample_width == 2:
                fmt = '<' + 'h' * (len(frames) // 2)
                samples = struct.unpack(fmt, frames)
            elif sample_width == 1:
                fmt = '<' + 'b' * len(frames)
                samples = struct.unpack(fmt, frames)
            else:
                samples = [0] * n_frames
            
            if channels == 2:
                samples = samples[::2]
            
            total_samples = len(samples)
            samples_needed = int(duration * samples_per_second)
            
            if samples_needed == 0:
                samples_needed = 1
            
            step = total_samples / samples_needed
            
            waveform = []
            for i in range(samples_needed):
                start = int(i * step)
                end = min(int((i + 1) * step), total_samples)
                
                if start < end:
                    chunk = samples[start:end]
                    max_val = max(chunk) if chunk else 0
                    min_val = min(chunk) if chunk else 0
                    amplitude = (max_val - min_val) / 2
                    if sample_width == 2:
                        amplitude = amplitude / 32768.0
                    elif sample_width == 1:
                        amplitude = amplitude / 128.0
                else:
                    amplitude = 0
                
                waveform.append(amplitude)
            
            return {
                'data': waveform,
                'duration': duration,
                'samples_per_second': samples_per_second
            }
            
    except Exception as e:
        return {'error': str(e)}
    finally:
        if audio_path != file_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass
