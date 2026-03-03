import os
import tempfile

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_temp_dir():
    temp_dir = os.path.join(get_project_root(), 'Temp')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def get_tts_temp_dir():
    temp_dir = os.path.join(get_temp_dir(), 'tts')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def get_transcription_temp_dir():
    temp_dir = os.path.join(get_temp_dir(), 'transcription')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def get_waveform_temp_dir():
    temp_dir = os.path.join(get_temp_dir(), 'waveform')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def cleanup_temp_dir(max_age_hours=24):
    import time
    temp_dir = get_temp_dir()
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if current_time - os.path.getmtime(file_path) > max_age_seconds:
                    os.remove(file_path)
            except:
                pass
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except:
                pass

PROJECT_ROOT = get_project_root()
TEMP_DIR = get_temp_dir()
