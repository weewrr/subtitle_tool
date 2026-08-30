<div align="center">

![Banner](docs/assets/banner.jpg)

# Subtitle Tool 字幕编辑工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.4+-green.svg)](https://vuejs.org/)
[![Electron](https://img.shields.io/badge/electron-31+-blue.svg)](https://www.electronjs.org/)

[English](README.md) | **简体中文**

一款功能强大的本地字幕编辑与处理工具，支持字幕编辑、语音识别、翻译、配音生成、硬字幕嵌入等功能。基于 **Vue 3 + Electron** 桌面前端与 **Flask** 本地后端，语音识别与语音合成全部在本地完成，数据不出本机。

</div>

## 功能特性

### 字幕编辑
- 支持 SRT、VTT、ASS、SSA 等多种字幕格式的导入、编辑与导出
- 撤销/重做、查找替换、多重替换、转到指定字幕编号
- 基于 LLM 的拼写检查与自定义词典
- 时间轴重叠检测与一键修复、字幕统计面板

### 语音识别
- 基于 OpenAI Whisper（openai-whisper / faster-whisper / whisper.cpp / whisper-ctranslate2）
- 支持 GPU 加速、自动语言检测，多模型选择（tiny/base/small/medium/large）
- 后台任务化：进度上报、可取消，临时文件自动清理

### 字幕翻译
- 多引擎支持：Ollama（本地模型，免 Key）、DeepSeek、阿里百炼（DashScope）、DeepL / Google / ChatGPT / Anthropic / Gemini / Mistral / LibreTranslate
- 云端引擎模型名可自由输入；自定义提示词支持**视频时长软约束**
- 批量翻译、异步任务

### 文本转语音（TTS）
- 多引擎声音克隆：**Spark-TTS**、**Qwen3-TTS**（ICL 高质量 / xvec_only 快速两种模式）
- 智能时间轴对齐：批量生成（batch=4）、自动静音裁剪/挤压/填充，完全不变速
- 支持导入外部音频作为参考音色

### 硬字幕与波形
- 视频硬字幕嵌入：自定义字体、大小、颜色、描边、位置
- 视频/音频波形可视化、字幕时间轴对齐、缩放与拖拽

## 快速开始

### 环境要求

- Python 3.12+（后端）
- Node.js 18+（前端构建）
- FFmpeg（需加入系统 PATH）
- _（可选）_ CUDA 显卡——用于 Whisper / TTS 的 GPU 加速
- _（可选）_ Ollama 服务——使用本地翻译引擎时

### 安装

```bash
# 方式一：一键安装前后端依赖（仓库根目录）
npm run install:all

# 方式二：分步安装
pip install -r requirements.txt          # 后端 Python 依赖
cd frontend && npm install               # 前端依赖
```

> 可复现部署请使用锁定文件：`pip install -r requirements.lock.txt`。

下载语音合成模型（可选，仅使用 TTS 时）：

```bash
# Spark-TTS 模型
cd Spark-TTS
python -c "from huggingface_hub import snapshot_download; snapshot_download('SparkAudio/Spark-TTS-0.5B', local_dir='pretrained_models/Spark-TTS-0.5B')"

# Qwen3-TTS 模型
cd ../Qwen3-TTS
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-Base', local_dir='Qwen3-TTS-12Hz-1.7B-Base')"
```

### 运行

开发模式（Electron 桌面应用 + 自动拉起后端）：

```bash
npm run dev
# 或分步：
python app.py                # 终端 1：启动 Flask 后端（http://127.0.0.1:5000）
cd frontend && npm run dev   # 终端 2：启动 Vite 开发服务器
cd frontend && npm run electron:dev   # 终端 3：启动 Electron（开发模式）
```

纯浏览器模式（无 Electron）：

```bash
python app.py
cd frontend && npm run dev
# 浏览器访问 Vite 开发服务器地址
```

## 项目结构

```
subtitle_tool/
├── backend/                 # Flask 后端
│   ├── config/             # 配置（端口、上传上限、模型目录等）
│   ├── routes/             # API 路由（Blueprint）
│   ├── services/           # 业务逻辑（识别/翻译/TTS/硬字幕等）
│   └── utils/              # 工具（统一响应、日志、临时目录清理）
├── frontend/               # Vue 3 + Electron 前端
│   ├── src/
│   │   ├── components/     # 组件（含 modals/ 各功能弹窗）
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── services/       # API 服务封装
│   │   └── utils/          # 工具（runtime/存储）
│   ├── electron/           # Electron 主进程与 preload
│   └── tests/              # 单元测试（Vitest）
├── Spark-TTS/              # Spark-TTS 语音合成引擎（含预训练模型）
├── Qwen3-TTS/              # Qwen3-TTS 语音合成引擎
├── Release/                # Whisper.cpp 发布二进制（whisper-cli 等）
├── Temp/                   # 运行时临时文件（自动清理）
├── app.py                  # Flask 应用入口
├── .env.example            # 环境变量示例（完整清单见"配置说明"）
├── requirements.txt        # Python 依赖（宽松下限）
└── requirements.lock.txt   # Python 依赖（可复现锁定）
```

## 常用命令

```bash
npm run install:all                 # 安装前后端全部依赖
npm run dev                         # 开发模式启动（Electron + 后端）
python app.py                       # 启动 Flask 后端服务
npm run electron:build              # 构建并打包桌面应用（electron-builder）
cd frontend && npm test             # 运行前端单元测试（Vitest）
cd frontend && npm run lint         # ESLint 检查（Vue/JS）
```

> 命令来源：仓库根目录与 `frontend/package.json` 的 scripts 字段。

## 配置说明

> 环境变量完整示例见仓库根目录 [`.env.example`](.env.example)，下表为主要项。

### 后端环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `SUBTITLE_TOOL_BACKEND_PORT` | 否 | `5000` | 后端服务端口 |
| `SUBTITLE_TOOL_BACKEND_DEBUG` | 否 | `0` | 设为 `1` 启用 Flask 调试模式 |
| `TRANSLATION_DURATION_CONSTRAINT_ENABLED` | 否 | `true` | 翻译的视频时长软约束开关（`false`/`0` 关闭） |
| `DEEPSEEK_API_KEY` | 否 | — | DeepSeek 翻译引擎的 Key（也可在翻译窗口直接填写） |
| `DASHSCOPE_API_KEY` / `BAILIAN_API_KEY` | 否 | — | 阿里百炼翻译引擎的 Key |

### 前端环境变量（`frontend/.env*`）

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | 后端 API 地址（开发默认 `http://localhost:5000`，生产为空走 Electron 注入） |
| `VITE_APP_TITLE` | 应用标题 |

### 功能配置（界面内）

- **Whisper 模型**：tiny / base / small / medium / large
- **TTS 引擎**：spark-tts / qwen3-tts，Qwen3 模式 icl / xvec_only
- **翻译引擎**：Ollama / DeepSeek / 阿里百炼 等在设置与翻译窗口中管理

## API 接口

统一响应结构：`{ success, data, error_code, message }`。所有接口前缀 `/api`，仅放行本机 origin 与 `app://` 源。

| 模块 | 接口 |
|------|------|
| 语音识别 | `POST /transcribe`、`GET /transcribe/<task_id>`、`GET /transcribe/<task_id>/result`、`GET /transcribe/<task_id>/events`（SSE）、`POST /transcribe/<task_id>/cancel` |
| Whisper 模型 | `GET /whisper/list`、`GET /whisper/downloaded`、`POST /whisper/download`、`GET /whisper/status`；whisper-cpp / whisper-ctranslate2 同构 |
| Vosk | `GET /vosk/list`、`POST /vosk/download`、`GET /vosk/status` |
| 翻译 | `POST /translation/async`、`GET /translation/status`、`GET /translation/result` |
| 拼写检查 | `POST /spell-check/ai`、`POST /spell-check/suggestions`、词典/人名增删查 |
| TTS 配音 | `GET /tts/engines`、`POST /tts/generate-subtitles`、`GET /tts/status`、`GET /tts/result`、`POST /tts/abort`、`GET /tts/download/<filename>`；音色 `GET /tts/voices`、`POST /tts/upload-voice`、`DELETE /tts/delete-voice/<filename>` |
| TTS 合成视频 | `POST /tts-video/generate`、`GET /tts-video/status`、`POST /tts-video/abort`、`GET /tts-video/download` |
| 硬字幕 | `POST /hard-subtitle/generate`、`POST /hard-subtitle/generate-from-path`、`GET /hard-subtitle/status`、`POST /hard-subtitle/abort`、`GET /hard-subtitle/download` |
| 波形 | `POST /waveform/generate`、`POST /waveform/generate-from-path` |
| 视频 | `GET /video/serve?path=<path>`（本地文件服务） |
| 字幕持久化 | `POST /subtitle/save-original`、`POST /subtitle/save-translation`、`POST /subtitle/auto-save` |
| 系统 | `GET /settings/health`、`GET /settings/version`、`GET /settings/diagnostics`、缓存统计与清理、`POST /settings/open-directory`、`POST /settings/open-logs` |

## 测试与质量

```bash
cd frontend && npm test    # Vitest 单元测试（tests/ 目录）
cd frontend && npm run lint
```

当前单元测试覆盖字幕格式解析/序列化等核心工具（`frontend/tests/subtitle-formats.test.js`）。后端暂无自动化测试，主要依赖接口联调验证。

## 打包发布

```bash
cd frontend && npm run electron:build   # vite build + electron-builder
```

electron-builder 配置（`frontend/package.json` 的 `build` 字段）：Windows NSIS 安装包、macOS DMG、Linux AppImage；注册 `.stproj` 项目文件关联。

## 常见问题

### CUDA 内存不足
- 使用较小的 Whisper 模型；减小 batch size；或使用 CPU 模式。

### 音频生成失败
- 检查 TTS 模型是否正确安装；确保磁盘空间充足；查看后端日志获取详细错误。

### 字幕时间轴不对齐
- 使用"分割长句"功能优化字幕；手动调整字幕时间；配音超长时后端日志会记录静音区间借用与顺延情况。

### FFmpeg 未找到
- 确保 FFmpeg 已安装并加入系统 PATH（Windows 可从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载）。

## 免责声明

- 本工具仅供个人学习与研究使用，按"现状"提供，不作任何明示或默示的保证，详见 [MIT License](LICENSE)。
- 语音识别、语音合成与翻译由 AI 模型驱动，输出可能存在错误，**请务必在使用前人工校对生成的字幕、译文与配音**。
- 语音识别、TTS 及 Ollama 翻译引擎均在本地运行；但**云端翻译引擎（DeepSeek、百炼、DeepL、Google、ChatGPT 等）会将字幕文本发送至第三方服务**，请勿用于涉密或敏感内容。
- 用户需自行确保所处理的视频、音频与参考音色来源合法，遵守版权法律法规及所用模型和 API 的服务条款；因不当使用产生的后果由使用者自行承担，作者不承担任何责任。

## 文档维护

更新本文档的场景：
- 新增或重命名 API 路由（`backend/routes/`）
- 环境变量或配置项变更（`backend/config/settings.py`、`frontend/.env*`）
- 新增或移除后端/前端脚本命令（根目录与 `frontend/package.json`）
- 项目目录结构变化

## 许可证

[MIT License](LICENSE)

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [whisper.cpp](https://github.com/ggerganov/whisper.cpp) - 语音识别
- [Spark-TTS](https://github.com/SparkAudio/Spark-TTS) - 语音合成
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) - 语音合成
- [Vue.js](https://vuejs.org/) · [Element Plus](https://element-plus.org/) · [Electron](https://www.electronjs.org/) - 前端框架
- [FFmpeg](https://ffmpeg.org/) - 音视频处理
