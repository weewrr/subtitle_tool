# Copyright (c) 2025 SparkAudio
# SRT字幕配音脚本 - 单条配音+ffmpeg变速对齐时间轴

import os
import re
import sys
import argparse
import logging
import platform
import numpy as np
import soundfile as sf
import subprocess
import tempfile

import torch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


def parse_srt_time(time_str):
    """将SRT时间格式转换为毫秒"""
    time_str = time_str.strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        hours = int(hours)
        minutes = int(minutes)
        sec_parts = seconds.split('.')
        secs = int(sec_parts[0])
        ms = int(sec_parts[1].ljust(3, '0')[:3]) if len(sec_parts) > 1 else 0
        return (hours * 3600 + minutes * 60 + secs) * 1000 + ms
    return 0


def parse_srt(srt_path):
    """解析SRT字幕文件"""
    subtitles = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0].strip())
                time_line = lines[1].strip()
                time_match = re.match(
                    r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
                    time_line
                )
                if time_match:
                    start_time = parse_srt_time(time_match.group(1))
                    end_time = parse_srt_time(time_match.group(2))
                    text = '\n'.join(lines[2:]).strip()
                    subtitles.append({
                        'index': index,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text
                    })
            except (ValueError, IndexError) as e:
                logger.warning(f"解析字幕块失败: {block[:50]}... 错误: {e}")
                continue
    
    return subtitles


def generate_silence(duration_ms, sample_rate=SAMPLE_RATE):
    """生成指定时长的静音"""
    samples = int(duration_ms / 1000 * sample_rate)
    return np.zeros(samples, dtype=np.float32)


def stretch_audio_ffmpeg(input_path, output_path, target_duration_ms, actual_duration_ms):
    """
    使用ffmpeg进行音频变速处理
    tempo = actual_duration / target_duration
    - tempo > 1: 加速 (音频比目标长)
    - tempo < 1: 减速 (音频比目标短)
    """
    if actual_duration_ms <= 0 or target_duration_ms <= 0:
        return False
    
    tempo = actual_duration_ms / target_duration_ms
    
    if abs(tempo - 1.0) < 0.01:
        import shutil
        shutil.copy(input_path, output_path)
        return True
    
    min_tempo = 0.5
    max_tempo = 2.0
    
    if tempo < min_tempo:
        logger.warning(f"变速倍数 {tempo:.3f} 过小，限制为 {min_tempo}")
        tempo = min_tempo
    elif tempo > max_tempo:
        logger.warning(f"变速倍数 {tempo:.3f} 过大，限制为 {max_tempo}")
        tempo = max_tempo
    
    cmd = [
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-filter:a', f'atempo={tempo}',
        '-ar', str(SAMPLE_RATE),
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg变速失败: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        logger.error("ffmpeg未找到，请确保已安装并添加到PATH")
        return False


def main():
    parser = argparse.ArgumentParser(description="SRT字幕配音生成")
    parser.add_argument("srt_file", type=str, help="SRT字幕文件路径")
    parser.add_argument("--output_dir", type=str, default=None, help="输出目录")
    parser.add_argument("--model_dir", type=str, 
                        default="pretrained_models/Spark-TTS-0.5B",
                        help="模型目录")
    parser.add_argument("--device", type=int, default=0, help="CUDA设备编号")
    parser.add_argument("--prompt_speech_path", type=str, required=True,
                        help="参考音频路径")
    parser.add_argument("--prompt_text", type=str, default=None,
                        help="参考音频文本")
    parser.add_argument("--speed", type=str, default="moderate",
                        choices=["very_low", "low", "moderate", "high", "very_high"],
                        help="语速")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.srt_file):
        logger.error(f"SRT文件不存在: {args.srt_file}")
        sys.exit(1)
    
    if not os.path.exists(args.prompt_speech_path):
        logger.error(f"参考音频不存在: {args.prompt_speech_path}")
        sys.exit(1)
    
    if args.output_dir is None:
        args.output_dir = os.path.dirname(args.srt_file)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    temp_dir = tempfile.mkdtemp(prefix='tts_dubbing_')
    
    logger.info(f"解析SRT文件: {args.srt_file}")
    subtitles = parse_srt(args.srt_file)
    
    if not subtitles:
        logger.error("未找到有效的字幕条目")
        sys.exit(1)
    
    logger.info(f"共找到 {len(subtitles)} 条字幕")
    
    if platform.system() == "Darwin" and torch.backends.mps.is_available():
        device = torch.device(f"mps:{args.device}")
    elif torch.cuda.is_available():
        device = torch.device(f"cuda:{args.device}")
    else:
        device = torch.device("cpu")
    
    logger.info(f"使用设备: {device}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isabs(args.model_dir):
        model_dir = args.model_dir
    else:
        model_dir = os.path.normpath(os.path.join(script_dir, args.model_dir))
    
    if not os.path.exists(model_dir):
        logger.error(f"模型目录不存在: {model_dir}")
        sys.exit(1)
    
    logger.info(f"加载模型: {model_dir}")
    
    sys.path.insert(0, script_dir)
    from cli.SparkTTS import SparkTTS
    
    model = SparkTTS(model_dir, device)
    
    logger.info("模型加载完成，开始生成配音...")
    
    audio_segments = []
    current_position_ms = 0
    
    for i, sub in enumerate(subtitles):
        logger.info(f"[{i+1}/{len(subtitles)}] 处理字幕: {sub['text'][:30]}...")
        
        if sub['start_time'] > current_position_ms:
            gap_duration = sub['start_time'] - current_position_ms
            silence = generate_silence(gap_duration)
            audio_segments.append(silence)
            logger.info(f"  添加 {gap_duration}ms 静音间隙")
            current_position_ms = sub['start_time']
        
        try:
            with torch.no_grad():
                wav = model.inference(
                    sub['text'],
                    args.prompt_speech_path,
                    prompt_text=args.prompt_text,
                    speed=args.speed,
                )
            
            if isinstance(wav, torch.Tensor):
                wav = wav.detach().cpu().numpy()
            
            wav = np.array(wav, dtype=np.float32)
            
            actual_duration_ms = len(wav) / SAMPLE_RATE * 1000
            target_duration_ms = sub['duration']
            
            tempo = actual_duration_ms / target_duration_ms
            stretch_ratio = 1.0 / tempo
            
            if abs(tempo - 1.0) > 0.01:
                original_path = os.path.join(temp_dir, f'original_{sub["index"]:03d}.wav')
                stretched_path = os.path.join(temp_dir, f'stretched_{sub["index"]:03d}.wav')
                
                sf.write(original_path, wav, SAMPLE_RATE)
                
                if stretch_audio_ffmpeg(original_path, stretched_path, target_duration_ms, actual_duration_ms):
                    stretched_wav, _ = sf.read(stretched_path)
                    if stretched_wav.dtype != np.float32:
                        stretched_wav = stretched_wav.astype(np.float32)
                    wav = stretched_wav
                    logger.info(f"  生成音频: {actual_duration_ms:.0f}ms → 变速{stretch_ratio:.2f}x → {len(wav)/SAMPLE_RATE*1000:.0f}ms (目标 {target_duration_ms}ms)")
                else:
                    logger.warning(f"  变速失败，使用原始音频: {actual_duration_ms:.0f}ms")
            else:
                logger.info(f"  生成音频: {actual_duration_ms:.0f}ms (目标 {target_duration_ms}ms, 无需变速)")
            
            audio_segments.append(wav)
            current_position_ms = sub['end_time']
            
        except Exception as e:
            logger.error(f"  生成失败: {e}")
            silence = generate_silence(sub['duration'])
            audio_segments.append(silence)
            current_position_ms = sub['end_time']
    
    logger.info("合成最终音频...")
    
    final_audio = np.concatenate(audio_segments)
    
    output_file = os.path.join(args.output_dir, 'subtitle_dubbed.wav')
    sf.write(output_file, final_audio, SAMPLE_RATE)
    
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except:
        pass
    
    logger.info(f"配音生成完成: {output_file}")
    logger.info(f"总时长: {len(final_audio)/SAMPLE_RATE:.2f}秒")
    
    return output_file


if __name__ == "__main__":
    main()
