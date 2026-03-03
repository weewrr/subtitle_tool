#!/usr/bin/env python3
# Spark-TTS SRT 字幕配音工具
# 参考 pyvideotrans-3.97 项目的实现

import os
import re
import torch
import soundfile as sf
import numpy as np
from datetime import timedelta
from cli.SparkTTS import SparkTTS

class SrtDubber:
    def __init__(self, model_dir="pretrained_models/Spark-TTS-0.5B", device=0):
        """初始化 SRT 配音器"""
        print(f"Loading model from: {model_dir}")
        
        # 确定设备
        if torch.cuda.is_available():
            self.device = torch.device(f"cuda:{device}")
            print(f"Using CUDA device: {self.device}")
        else:
            self.device = torch.device("cpu")
            print("GPU acceleration not available, using CPU")
        
        # 初始化模型
        self.model = SparkTTS(model_dir, self.device)
    
    def ms_to_time_string(self, ms=0, sepflag=','):
        """将毫秒转换为时间字符串"""
        td = timedelta(milliseconds=ms)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02}:{minutes:02}:{seconds:02}{sepflag}{milliseconds:03}"
    
    def format_time(self, s_time="", separate=','):
        """格式化时间字符串"""
        if not s_time.strip():
            return f'00:00:00{separate}000'
        
        hou, min, sec, ms = 0, 0, 0, 0
        tmp = s_time.strip().split(':')
        
        if len(tmp) >= 3:
            hou, min, sec = tmp[-3].strip(), tmp[-2].strip(), tmp[-1].strip()
        elif len(tmp) == 2:
            min, sec = tmp[0].strip(), tmp[1].strip()
        elif len(tmp) == 1:
            sec = tmp[0].strip()
        
        if re.search(r',|\.', str(sec)):
            t = re.split(r',|\.', str(sec))
            sec = t[0].strip()
            ms = t[1].strip()
        else:
            ms = 0
        
        hou = f'{int(hou):02}'[-2:]
        min = f'{int(min):02}'[-2:]
        sec = f'{int(sec):02}'
        ms = f'{int(ms):03}'[-3:]
        return f"{hou}:{min}:{sec}{separate}{ms}"
    
    def srt_str_to_listdict(self, srt_string):
        """解析 SRT 字幕字符串为字典列表"""
        srt_list = []
        time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-{1,2}>\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
        lines = srt_string.splitlines()
        i = 0
        
        while i < len(lines):
            time_match = re.match(time_pattern, lines[i].strip())
            if time_match:
                # 解析时间戳
                start_time_groups = time_match.groups()[0:4]
                end_time_groups = time_match.groups()[4:8]
                
                def parse_time(time_groups):
                    h, m, s, ms = time_groups
                    ms = ms.replace(',', '').replace('.', '') if ms else "0"
                    try:
                        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
                    except (ValueError, TypeError):
                        return None
                
                start_time = parse_time(start_time_groups)
                end_time = parse_time(end_time_groups)
                
                if start_time is None or end_time is None:
                    i += 1
                    continue
                
                i += 1
                text_lines = []
                while i < len(lines):
                    current_line = lines[i].strip()
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""  # 获取下一行，如果没有则为空字符串
                    
                    if re.match(time_pattern, next_line):  # 判断下一行是否为时间行
                        if re.fullmatch(r'\d+', current_line):  # 如果当前行为纯数字，则跳过
                            i += 1
                            break
                        else:
                            if current_line:
                                text_lines.append(current_line)
                            i += 1
                            break
                    
                    if current_line:
                        text_lines.append(current_line)
                        i += 1
                    else:
                        i += 1
                
                text = ('\n'.join(text_lines)).strip()
                text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip(), flags=re.I | re.S)
                text = re.sub(r'\n{2,}', '\n', text, flags=re.I | re.S).strip()
                it = {
                    "line": len(srt_list) + 1,  # 字幕索引，转换为整数
                    "start_time": int(start_time),
                    "end_time": int(end_time),  # 起始和结束时间
                    "text": text if text else "",  # 字幕文本
                }
                it['startraw'] = self.ms_to_time_string(ms=it['start_time'])
                it['endraw'] = self.ms_to_time_string(ms=it['end_time'])
                it["time"] = f"{it['startraw']} --> {it['endraw']}"
                srt_list.append(it)
            else:
                i += 1  # 跳过非时间行
        
        return srt_list
    
    def get_subtitle_from_srt(self, srtfile, *, is_file=True):
        """从 SRT 文件或字符串获取字幕列表"""
        def _readfile(file):
            content = ""
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except UnicodeDecodeError as e:
                try:
                    with open(file, 'r', encoding='gbk') as f:
                        content = f.read().strip()
                except UnicodeDecodeError as e:
                    raise RuntimeError(f"无法读取 SRT 文件: {e}")
            except BaseException as e:
                raise RuntimeError(f"读取 SRT 文件时出错: {e}")
            return content
        
        if is_file:
            content = _readfile(srtfile)
        else:
            content = srtfile.strip()
        
        if len(content) < 1:
            raise RuntimeError("SRT 字幕内容为空")
        
        result = self.srt_str_to_listdict(content)
        
        # 如果解析失败，返回空列表
        if len(result) < 1:
            raise RuntimeError("无法解析 SRT 字幕格式")
        
        return result
    
    def generate_audio_for_subtitle(self, subtitle, prompt_speech_path=None, prompt_text=None, gender=None, pitch=None, speed=None):
        """为单个字幕生成音频"""
        text = subtitle['text']
        
        with torch.no_grad():
            wav = self.model.inference(
                text,
                prompt_speech_path,
                prompt_text=prompt_text,
                gender=gender,
                pitch=pitch,
                speed=speed
            )
        
        return wav
    
    def adjust_audio_length(self, wav, target_duration_ms, sample_rate=16000):
        """调整音频长度以匹配目标时长"""
        # 由于现在直接在生成时指定目标时长，此方法可能不再需要
        # 但为了向后兼容，保留此方法
        return wav
    
    def process_srt(self, srt_file, output_dir="output", prompt_speech_path=None, prompt_text=None, gender=None, pitch=None, speed=None):
        """处理 SRT 字幕文件并生成配音"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Parsing SRT file: {srt_file}")
        subtitles = self.get_subtitle_from_srt(srt_file)
        print(f"Found {len(subtitles)} subtitles")
        
        if not subtitles:
            raise RuntimeError("No subtitles found")
        
        sample_rate = 16000
        last_end_time = 0
        audio_segments = []
        
        for i, subtitle in enumerate(subtitles):
            print(f"Processing subtitle {i+1}/{len(subtitles)}: {subtitle['text'][:50]}...")
            
            start_time = subtitle['start_time']
            end_time = subtitle['end_time']
            target_duration_ms = end_time - start_time
            
            gap_ms = start_time - last_end_time
            if gap_ms > 0 and i > 0:
                gap_samples = int(gap_ms / 1000 * sample_rate)
                silence = np.zeros(gap_samples, dtype=np.float32)
                audio_segments.append(silence)
                print(f"  Added {gap_ms}ms silence gap")
            
            if i == 0 and start_time > 0:
                initial_silence_samples = int(start_time / 1000 * sample_rate)
                silence = np.zeros(initial_silence_samples, dtype=np.float32)
                audio_segments.append(silence)
                print(f"  Added {start_time}ms initial silence")
            
            wav = self.generate_audio_for_subtitle(
                subtitle,
                prompt_speech_path=prompt_speech_path,
                prompt_text=prompt_text,
                gender=gender,
                pitch=pitch,
                speed=speed
            )
            
            actual_duration_ms = len(wav) / sample_rate * 1000
            if abs(actual_duration_ms - target_duration_ms) > 100:
                print(f"  Warning: Generated {actual_duration_ms:.0f}ms, target {target_duration_ms}ms")
            
            audio_segments.append(wav)
            last_end_time = end_time
        
        print("Merging audio segments...")
        full_audio = np.concatenate(audio_segments)
        
        output_file = os.path.join(output_dir, f"{os.path.basename(srt_file).replace('.srt', '')}_dubbed.wav")
        sf.write(output_file, full_audio, samplerate=sample_rate)
        
        total_duration_s = len(full_audio) / sample_rate
        expected_duration_s = subtitles[-1]['end_time'] / 1000
        print(f"Dubbed audio saved to: {output_file}")
        print(f"Total duration: {total_duration_s:.2f}s, Expected: {expected_duration_s:.2f}s")
        
        return output_file

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Spark-TTS SRT 字幕配音工具")
    parser.add_argument("srt_file", help="SRT 字幕文件路径")
    parser.add_argument("--output_dir", default="output", help="输出目录")
    parser.add_argument("--model_dir", default="pretrained_models/Spark-TTS-0.5B", help="模型目录")
    parser.add_argument("--device", type=int, default=0, help="CUDA 设备编号")
    parser.add_argument("--prompt_speech_path", help="参考音频路径")
    parser.add_argument("--prompt_text", help="参考音频文本")
    parser.add_argument("--gender", choices=["male", "female"], help="性别")
    parser.add_argument("--pitch", choices=["very_low", "low", "moderate", "high", "very_high"], help="音高")
    parser.add_argument("--speed", choices=["very_low", "low", "moderate", "high", "very_high"], help="语速")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.srt_file):
        print(f"Error: SRT file not found: {args.srt_file}")
        return
    
    # 初始化配音器
    dubber = SrtDubber(model_dir=args.model_dir, device=args.device)
    
    # 处理 SRT 文件
    try:
        output_file = dubber.process_srt(
            args.srt_file,
            output_dir=args.output_dir,
            prompt_speech_path=args.prompt_speech_path,
            prompt_text=args.prompt_text,
            gender=args.gender,
            pitch=args.pitch,
            speed=args.speed
        )
        print(f"\n[OK] Dubbing completed successfully!")
        print(f"Output file: {output_file}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
