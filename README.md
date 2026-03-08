# Subtitle Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.4+-green.svg)](https://vuejs.org/)
[![Electron](https://img.shields.io/badge/electron-31+-blue.svg)](https://www.electronjs.org/)

一款功能强大的字幕编辑与处理工具，支持字幕编辑、翻译、语音识别、配音生成、硬字幕嵌入等功能。

## 功能特性

### 字幕编辑
- 支持 SRT、VTT、ASS、SSA 等多种字幕格式
- 实时预览与编辑
- 撤销/重做操作
- 查找替换、多重替换
- 转到指定字幕编号
- 拼写检查（基于 LLM）

### 语音识别
- 基于 OpenAI Whisper 的语音识别
- 支持 GPU 加速
- 自动语言检测
- 多种模型选择（tiny/base/small/medium/large）

### 字幕翻译
- 支持多种翻译引擎（Ollama、DeepL、LibreTranslate）
- 批量翻译
- 自定义提示词
- 支持 LLM 翻译

### 智能处理
- 长句智能分割
- 句子合并
- 重复词/重复行检测

### 文本转语音（TTS）
- **多引擎支持**：
  - Spark-TTS：基于 Spark-TTS 的声音克隆
  - Qwen3-TTS：基于 Qwen3-TTS 的声音克隆
- **声音克隆**：使用参考音频克隆声音
- **Qwen3-TTS 模式**：
  - ICL (高质量)：克隆质量更高，需要参考文本
  - xvec_only (快速)：速度更快，参考文本可选
- **智能时间轴对齐**：
  - 单条字幕独立生成配音
  - 自动静音间隙填充
  - 音频过长：FFmpeg 加速对齐
  - 音频过短：开头+结尾平分静音填充
- 支持导入外部音频

### 硬字幕生成
- 视频硬字幕嵌入
- 自定义字体、大小、颜色、描边
- 字幕位置调整
- 实时预览

### 波形显示
- 视频/音频波形可视化
- 字幕时间轴对齐
- 缩放与拖拽

## 技术栈

### 后端
- Python 3.12+
- Flask - Web 框架
- OpenAI Whisper - 语音识别
- Spark-TTS / Qwen3-TTS - 语音合成
- FFmpeg - 音视频处理、音频变速

### 前端
- Vue 3 - 前端框架
- Element Plus - UI 组件库
- Pinia - 状态管理
- Vite - 构建工具
- Electron - 桌面应用

## 项目结构

```
subtitle_tool/
├── backend/                 # 后端代码
│   ├── config/             # 配置文件
│   ├── routes/             # API 路由
│   ├── services/           # 业务逻辑
│   │   └── spark_tts_service.py  # TTS 服务
│   └── utils/              # 工具函数
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/    # Vue 组件
│   │   │   └── TtsPanel.vue  # TTS 面板
│   │   ├── stores/        # 状态管理
│   │   ├── services/      # API 服务
│   │   └── views/         # 页面视图
│   └── electron/          # Electron 配置
├── Spark-TTS/              # Spark-TTS 引擎
│   ├── cli/               # 命令行工具
│   ├── sparktts/          # 核心模块
│   ├── srt_dubbing.py     # 字幕配音脚本
│   └── pretrained_models/ # 模型文件
├── Qwen3-TTS/              # Qwen3-TTS 引擎
│   ├── qwen_tts/          # 核心模块
│   ├── srt_dubbing_qwen.py # 字幕配音脚本
│   └── Qwen3-TTS-12Hz-1.7B-Base/ # 模型文件
├── Release/                # Whisper.cpp 发布版本
├── Temp/                   # 临时文件目录
├── app.py                  # Flask 应用入口
└── requirements.txt        # Python 依赖
```

## 安装说明

### 环境要求
- Python 3.12+
- Node.js 18+
- FFmpeg（需添加到系统 PATH）
- CUDA（可选，用于 GPU 加速）

### 后端安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 PyTorch (CUDA 版本)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 下载 Spark-TTS 模型
cd Spark-TTS
python -c "from huggingface_hub import snapshot_download; snapshot_download('SparkAudio/Spark-TTS-0.5B', local_dir='pretrained_models/Spark-TTS-0.5B')"

# 下载 Qwen3-TTS 模型（可选）
cd ../Qwen3-TTS
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-Base', local_dir='Qwen3-TTS-12Hz-1.7B-Base')"
```

### 前端安装

```bash
cd frontend
npm install
```

## 运行方式

### 开发模式

```bash
# 启动后端
python app.py

# 启动前端开发服务器（新终端）
cd frontend
npm run dev

# 启动 Electron 应用
npm run electron:dev
```

### 生产模式

```bash
# 构建前端
cd frontend
npm run build

# 启动后端服务
python app.py
```

## API 接口

### 语音识别
- `POST /api/transcribe` - 上传文件进行语音识别
- `GET /api/transcribe/status` - 获取识别状态
- `GET /api/transcribe/result` - 获取识别结果

### 翻译
- `POST /api/translate` - 翻译文本

### 拼写检查
- `POST /api/spell-check/ai` - AI 拼写检查

### TTS 配音
- `GET /api/tts/engines` - 获取可用 TTS 引擎列表
- `GET /api/tts/reference-audios` - 获取参考音频列表
- `POST /api/tts/upload-reference` - 上传参考音频
- `DELETE /api/tts/reference-audio/<filename>` - 删除参考音频
- `POST /api/tts/generate-subtitles` - 生成字幕配音
- `GET /api/tts/status` - 获取生成状态
- `GET /api/tts/result` - 获取生成结果
- `GET /api/tts/download/<filename>` - 下载音频文件

### 波形生成
- `POST /api/waveform/generate` - 上传文件生成波形
- `POST /api/waveform/generate-from-path` - 根据文件路径生成波形

### 硬字幕
- `POST /api/hard-subtitle/generate` - 生成硬字幕视频
- `POST /api/hard-subtitle/generate-from-path` - 根据文件路径生成硬字幕

## 配置说明

### Whisper 模型配置
支持以下模型：
- `tiny` - 最快，准确率较低
- `base` - 平衡速度和准确率
- `small` - 推荐使用
- `medium` - 更高准确率
- `large` - 最高准确率，需要更多资源

### TTS 配音配置
- `engine`: TTS 引擎（spark-tts / qwen3-tts）
- `mode`: Qwen3-TTS 模式（icl / xvec_only）
- `prompt_speech_path`: 参考音频路径（用于声音克隆）
- `prompt_text`: 参考音频对应文本（可选）

### 时间轴对齐算法

配音生成采用以下步骤确保时间轴对齐：

1. **单条生成**：每条字幕独立调用 TTS 生成音频
2. **静音填充**：在字幕间隙插入静音，保持时间轴连续
3. **时长调整**：
   ```
   tempo = 实际时长 / 目标时长
   
   - tempo > 1 (音频过长): FFmpeg 加速对齐
   - tempo < 1 (音频过短): 开头+结尾平分静音填充
   - 变速范围限制: 0.5x ~ 2.0x
   ```
4. **拼接输出**：将所有片段拼接为完整配音文件

## 常见问题

### CUDA 内存不足
- 使用较小的 Whisper 模型
- 减小 batch size
- 使用 CPU 模式

### 音频生成失败
- 检查 TTS 模型是否正确安装
- 确保有足够的磁盘空间
- 查看后端日志获取详细错误信息

### 字幕时间轴不对齐
- 使用分割长句功能优化字幕
- 手动调整字幕时间
- 检查变速范围是否超出限制

### FFmpeg 未找到
- 确保 FFmpeg 已安装并添加到系统 PATH
- Windows 用户可从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request。

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别
- [Spark-TTS](https://github.com/SparkAudio/Spark-TTS) - 语音合成
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - 语音合成
- [Vue.js](https://vuejs.org/) - 前端框架
- [Element Plus](https://element-plus.org/) - UI 组件库
- [Electron](https://www.electronjs.org/) - 桌面应用框架
- [FFmpeg](https://ffmpeg.org/) - 音视频处理
