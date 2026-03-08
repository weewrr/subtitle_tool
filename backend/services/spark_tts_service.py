import os
import sys
import subprocess
import threading
import logging
import time

from backend.utils.temp_dir import get_tts_temp_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSService:
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
            'total_subtitles': 0,
            'engine': None
        }
    
    def get_spark_tts_root(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        spark_tts_root = os.path.normpath(os.path.join(base_dir, 'Spark-TTS'))
        if os.path.exists(spark_tts_root):
            return spark_tts_root
        return None
    
    def get_qwen_tts_root(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        qwen_tts_root = os.path.normpath(os.path.join(base_dir, 'Qwen3-TTS'))
        if os.path.exists(qwen_tts_root):
            return qwen_tts_root
        return None
    
    def get_spark_model_dir(self):
        spark_tts_root = self.get_spark_tts_root()
        if spark_tts_root:
            model_dir = os.path.normpath(os.path.join(spark_tts_root, 'pretrained_models', 'Spark-TTS-0.5B'))
            if os.path.exists(model_dir):
                return model_dir
        return None
    
    def get_qwen_model_dir(self):
        qwen_tts_root = self.get_qwen_tts_root()
        if qwen_tts_root:
            model_dir = os.path.normpath(os.path.join(qwen_tts_root, 'Qwen3-TTS-12Hz-1.7B-Base'))
            if os.path.exists(model_dir):
                return model_dir
        return None
    
    def get_available_engines(self):
        """获取可用的TTS引擎列表"""
        engines = []
        
        spark_model = self.get_spark_model_dir()
        if spark_model:
            engines.append({
                'id': 'spark-tts',
                'name': 'Spark-TTS (本地)',
                'model_dir': spark_model,
                'description': '基于Spark-TTS的声音克隆'
            })
        
        qwen_model = self.get_qwen_model_dir()
        if qwen_model:
            engines.append({
                'id': 'qwen3-tts',
                'name': 'Qwen3-TTS (本地)',
                'model_dir': qwen_model,
                'description': '基于Qwen3-TTS的声音克隆'
            })
        
        return engines
    
    def generate_subtitle_audio_async(self, subtitles, prompt_speech_path, prompt_text=None, output_dir=None, engine='spark-tts', mode='icl'):
        if self.status['generating']:
            return {'error': '已有生成任务正在进行中'}
        
        if not prompt_speech_path:
            return {'error': '请选择参考音频'}
        
        print(f"[TTS_SERVICE] generate_subtitle_audio_async called:")
        print(f"  - prompt_speech_path: {prompt_speech_path}")
        print(f"  - prompt_text: {prompt_text}")
        print(f"  - engine: {engine}")
        print(f"  - mode: {mode}")
        
        thread = threading.Thread(
            target=self._generate_thread,
            args=(subtitles, prompt_speech_path, prompt_text, output_dir, engine, mode)
        )
        thread.start()
        
        return {'status': 'started', 'message': '生成任务已启动'}
    
    def _generate_thread(self, subtitles, prompt_speech_path, prompt_text, output_dir, engine, mode):
        try:
            self.status['generating'] = True
            self.status['progress'] = 0
            self.status['status'] = 'preparing'
            self.status['error'] = None
            self.status['result'] = None
            self.status['current_subtitle'] = 0
            self.status['total_subtitles'] = len(subtitles)
            self.status['engine'] = engine
            
            print(f"\n{'='*60}")
            print(f"[TTS_SERVICE] _generate_thread started:")
            print(f"  - prompt_speech_path: {prompt_speech_path}")
            print(f"  - prompt_text: {prompt_text}")
            print(f"  - output_dir: {output_dir}")
            print(f"  - engine: {engine}")
            print(f"  - mode: {mode}")
            print(f"{'='*60}\n")
            
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
            logger.info(f"Output dir: {output_dir}")
            logger.info(f"Prompt speech path: {prompt_speech_path}")
            
            prompt_speech_path = os.path.normpath(prompt_speech_path)
            if not os.path.exists(prompt_speech_path):
                raise RuntimeError(f"参考音频不存在: {prompt_speech_path}")
            
            if engine == 'qwen3-tts':
                cmd = self._build_qwen_command(srt_file, output_dir, prompt_speech_path, prompt_text, mode)
                cwd = self.get_qwen_tts_root()
            else:
                cmd = self._build_spark_command(srt_file, output_dir, prompt_speech_path, prompt_text)
                cwd = self.get_spark_tts_root()
            
            if cmd is None:
                raise RuntimeError(f"TTS引擎 {engine} 不可用")
            
            logger.info(f"Using engine: {engine}")
            logger.info(f"Running command: {' '.join(cmd)}")
            print(f"[TTS_SERVICE] Running command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
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
                logger.error(f"srt_dubbing failed with return code: {process.returncode}")
                raise RuntimeError(f"配音生成失败，返回码: {process.returncode}")
            
            logger.info(f"srt_dubbing completed successfully")
            
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
    
    def _build_spark_command(self, srt_file, output_dir, prompt_speech_path, prompt_text):
        spark_tts_root = self.get_spark_tts_root()
        model_dir = self.get_spark_model_dir()
        
        if not spark_tts_root or not model_dir:
            return None
        
        srt_dubbing_path = os.path.normpath(os.path.join(spark_tts_root, 'srt_dubbing.py'))
        
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
        
        return cmd
    
    def _build_qwen_command(self, srt_file, output_dir, prompt_speech_path, prompt_text, mode='icl'):
        qwen_tts_root = self.get_qwen_tts_root()
        model_dir = self.get_qwen_model_dir()
        
        if not qwen_tts_root or not model_dir:
            return None
        
        srt_dubbing_path = os.path.normpath(os.path.join(qwen_tts_root, 'srt_dubbing_qwen.py'))
        
        cmd = [
            sys.executable,
            srt_dubbing_path,
            srt_file,
            '--output_dir', output_dir,
            '--model_dir', model_dir,
            '--prompt_speech_path', prompt_speech_path,
            '--mode', mode
        ]
        
        if prompt_text:
            cmd.extend(['--prompt_text', prompt_text])
        
        return cmd
    
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
        return {
            'engines': self.get_available_engines(),
            'spark_tts_root': self.get_spark_tts_root(),
            'qwen_tts_root': self.get_qwen_tts_root()
        }
    
    def abort(self):
        self.status['aborted'] = True

tts_service = TTSService()

spark_tts_service = tts_service
