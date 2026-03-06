import os
import sys
import subprocess
import threading
import logging
import time

from backend.utils.temp_dir import get_tts_temp_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SparkTTSService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.status = {
            'generating': False,
            'progress': 0,
            'status': 'idle',
            'error': None,
            'result': None,
            'current_subtitle': 0,
            'total_subtitles': 0
        }
    
    def get_spark_tts_root(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        spark_tts_root = os.path.normpath(os.path.join(base_dir, 'Spark-TTS'))
        if os.path.exists(spark_tts_root):
            return spark_tts_root
        return None
    
    def get_model_dir(self):
        spark_tts_root = self.get_spark_tts_root()
        if spark_tts_root:
            model_dir = os.path.normpath(os.path.join(spark_tts_root, 'pretrained_models', 'Spark-TTS-0.5B'))
            if os.path.exists(model_dir):
                return model_dir
        return None
    
    def generate_subtitle_audio_async(self, subtitles, prompt_speech_path, prompt_text=None, output_dir=None):
        if self.status['generating']:
            return {'error': '已有生成任务正在进行中'}
        
        if not prompt_speech_path:
            return {'error': '请选择参考音频'}
        
        print(f"[SPARK_TTS_SERVICE] generate_subtitle_audio_async called:")
        print(f"  - prompt_speech_path: {prompt_speech_path}")
        print(f"  - prompt_text: {prompt_text}")
        
        thread = threading.Thread(
            target=self._generate_thread,
            args=(subtitles, prompt_speech_path, prompt_text, output_dir)
        )
        thread.start()
        
        return {'status': 'started', 'message': '生成任务已启动'}
    
    def _generate_thread(self, subtitles, prompt_speech_path, prompt_text, output_dir):
        try:
            self.status['generating'] = True
            self.status['progress'] = 0
            self.status['status'] = 'preparing'
            self.status['error'] = None
            self.status['result'] = None
            self.status['current_subtitle'] = 0
            self.status['total_subtitles'] = len(subtitles)
            
            print(f"\n{'='*60}")
            print(f"[SPARK_TTS_SERVICE] _generate_thread started:")
            print(f"  - prompt_speech_path: {prompt_speech_path}")
            print(f"  - prompt_text: {prompt_text}")
            print(f"  - output_dir: {output_dir}")
            print(f"{'='*60}\n")
            
            spark_tts_root = self.get_spark_tts_root()
            if not spark_tts_root:
                raise RuntimeError("Spark-TTS directory not found")
            
            model_dir = self.get_model_dir()
            if not model_dir:
                raise RuntimeError("Spark-TTS model not found")
            
            import uuid
            temp_id = str(uuid.uuid4())[:8]
            
            if output_dir is None:
                output_dir = os.path.normpath(os.path.join(get_tts_temp_dir(), temp_id))
            
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create output dir: {e}")
                output_dir = os.path.normpath(os.path.join(os.environ.get('TEMP', '/tmp'), f'tts_{temp_id}'))
                os.makedirs(output_dir, exist_ok=True)
            
            srt_content = self._generate_srt_content(subtitles)
            srt_file = os.path.normpath(os.path.join(output_dir, 'subtitle.srt'))
            
            try:
                with open(srt_file, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
            except Exception as e:
                logger.error(f"Failed to write SRT file: {e}")
                raise RuntimeError(f"无法写入SRT文件: {e}")
            
            self.status['status'] = 'generating'
            self.status['progress'] = 5
            
            logger.info(f"Generated SRT file: {srt_file}")
            logger.info(f"Model dir: {model_dir}")
            logger.info(f"Output dir: {output_dir}")
            logger.info(f"Prompt speech path: {prompt_speech_path}")
            
            print(f"\n{'='*60}")
            print(f"[SPARK_TTS_SERVICE] Before building command:")
            print(f"  - srt_file: {srt_file}")
            print(f"  - model_dir: {model_dir}")
            print(f"  - output_dir: {output_dir}")
            print(f"  - prompt_speech_path: {prompt_speech_path}")
            print(f"  - prompt_text: {prompt_text}")
            print(f"  - prompt_speech_path exists: {os.path.exists(prompt_speech_path)}")
            print(f"{'='*60}\n")
            
            srt_dubbing_path = os.path.normpath(os.path.join(spark_tts_root, 'srt_dubbing.py'))
            
            prompt_speech_path = os.path.normpath(prompt_speech_path)
            if not os.path.exists(prompt_speech_path):
                raise RuntimeError(f"参考音频不存在: {prompt_speech_path}")
            
            cmd = [
                sys.executable,
                srt_dubbing_path,
                srt_file,
                '--output_dir', output_dir,
                '--model_dir', model_dir,
                '--prompt_speech_path', prompt_speech_path
            ]
            
            if prompt_text:
                cmd.extend(['--prompt_text', prompt_text])
            
            logger.info(f"Using voice cloning mode with prompt: {prompt_speech_path}")
            logger.info(f"Running command: {' '.join(cmd)}")
            print(f"[SPARK_TTS_SERVICE] Running command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=spark_tts_root,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            def read_output(pipe, log_prefix):
                try:
                    for line in iter(pipe.readline, ''):
                        if line:
                            print(f"[{log_prefix}] {line.strip()}")
                            logger.info(f"{log_prefix}: {line.strip()}")
                except Exception as e:
                    print(f"[ERROR] Error reading {log_prefix}: {e}")
                    logger.error(f"Error reading {log_prefix}: {e}")
            
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout, 'STDOUT'))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, 'STDERR'))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            logger.info("Process started, waiting for completion...")
            
            while process.poll() is None:
                if self.status.get('aborted'):
                    process.terminate()
                    self.status['status'] = 'aborted'
                    self.status['generating'] = False
                    return
                
                self._update_progress_from_subtitles(len(subtitles))
                time.sleep(0.5)
            
            logger.info(f"Process finished with return code: {process.returncode}")
            
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            
            if process.returncode != 0:
                logger.error(f"srt_dubbing.py failed with return code: {process.returncode}")
                raise RuntimeError(f"配音生成失败，返回码: {process.returncode}")
            
            logger.info(f"srt_dubbing.py completed successfully")
            
            output_file = os.path.join(output_dir, 'subtitle_dubbed.wav')
            if not os.path.exists(output_file):
                possible_outputs = [f for f in os.listdir(output_dir) if f.endswith('_dubbed.wav')]
                if possible_outputs:
                    output_file = os.path.join(output_dir, possible_outputs[0])
                else:
                    raise RuntimeError("未找到生成的音频文件")
            
            self.status['progress'] = 100
            self.status['status'] = 'completed'
            self.status['generating'] = False
            self.status['result'] = output_file
            
            logger.info(f"Audio generated: {output_file}")
            
        except Exception as e:
            self.status['status'] = 'error'
            self.status['error'] = str(e)
            self.status['generating'] = False
            logger.error(f"Subtitle audio generation failed: {e}")
    
    def _update_progress_from_subtitles(self, total):
        if total > 0 and self.status['progress'] < 95:
            current_progress = self.status['progress']
            if current_progress < 10:
                self.status['progress'] = 10
            elif current_progress < 90:
                self.status['progress'] = min(current_progress + 1, 90)
    
    def _generate_srt_content(self, subtitles):
        lines = []
        for i, sub in enumerate(subtitles, 1):
            start_time = self._ms_to_srt_time(sub.get('start_time', 0))
            end_time = self._ms_to_srt_time(sub.get('end_time', 0))
            text = sub.get('text', '')
            
            lines.append(str(i))
            lines.append(f"{start_time} --> {end_time}")
            lines.append(text)
            lines.append('')
        
        return '\n'.join(lines)
    
    def _ms_to_srt_time(self, ms):
        ms = int(ms)
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def get_status(self):
        return {'status': self.status}
    
    def get_result(self):
        result = self.status.get('result')
        if result:
            self.status['result'] = None
            return {'success': True, 'output_path': result}
        return {'success': False, 'error': 'No result available'}
    
    def get_model_info(self):
        spark_tts_root = self.get_spark_tts_root()
        model_dir = self.get_model_dir()
        return {
            'loaded': model_dir is not None,
            'model_dir': model_dir,
            'spark_tts_root': spark_tts_root
        }
    
    def abort(self):
        self.status['aborted'] = True

spark_tts_service = SparkTTSService()
