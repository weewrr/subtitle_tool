# 字幕工具项目代码审查报告

**审查日期**：2026-08-30
**审查方法**：code-review-skill 四阶段流程（上下文收集 → 高层审查 → 逐行分析 → 总结决策）
**审查范围**：`backend/`（Flask 后端全部路由与服务）、`frontend/`（Vue 3 + Electron 全部源码与配置）、`app.py`
**排除范围**：`Qwen3-TTS/`、`Spark-TTS/`（第三方模型库）、`Release/`（二进制）、`thesis/`（文档）
**验证方式**：4 个并行审查代理 + 主审对全部 🔴 级发现逐一读码复核（含 Node 实测路径穿越）

---

## 总览

| 严重级别 | 数量 | 含义 |
|---|---|---|
| 🔴 blocking | 4 | 必须修复（安全漏洞 / 功能级故障） |
| 🟡 important | 38 | 应当修复 |
| 🟢 nit | ~40 | 可选优化 |
| 💡 suggestion | 9 | 替代方案 |
| 🎉 praise | 18 | 值得表扬的实现 |

**审查结论**：🔄 **Request Changes** —— 架构与工程意识整体优秀，但存在 1 条已实测验证的安全攻击链和 1 个功能级故障，必须修复后项目才达到可发布状态。

---

## 一、🔴 Blocking（必须修复）

### B-1. Electron `app://` 协议路径穿越，可读取 dist 外任意本地文件

**位置**：`frontend/electron/main.cjs:469-474`

```js
protocol.handle('app', (request) => {
  const pathname = decodeURIComponent(new URL(request.url).pathname)
  const relative = pathname.replace(/^\/+/, '') || 'index.html'
  const filePath = path.join(__dirname, '..', 'dist', relative)
  return net.fetch(pathToFileURL(filePath).toString())
})
```

**验证**：已用 Node 实测 `app://./..%2F..%2F..%2FWindows%2Fwin.ini` 可解析出 `D:\Windows\win.ini`。WHATWG URL 不会规范化 `%2F` 编码段，`decodeURIComponent` 之后 `..` 生效，`path.join` 无前缀校验直接逃逸出 dist 目录。渲染进程一旦被注入（当前 CSP 含 `unsafe-inline`），即可读取任意本地文件。

**修复**：

```js
const filePath = path.join(__dirname, '..', 'dist', relative)
const distRoot = path.join(__dirname, '..', 'dist') + path.sep
if (!filePath.startsWith(distRoot)) {
  return new Response('Not Found', { status: 404 })
}
```

### B-2. 缺少导航 / window.open 拦截，preload 暴露面被带出应用边界

**位置**：`frontend/electron/main.cjs`（`createMainWindow` 内无任何拦截）

无 `setWindowOpenHandler`、无 `will-navigate` 处理。渲染进程被注入后 `location.href = 'https://evil.com'` 即可导航到外部页面，**preload 暴露的 `window.electronAPI` 对导航后的页面依然生效**，外部页面可直接调用 `read-file`（配合下方 I-3 即构成完整的任意文件读取链）。CSP 无法阻止导航类攻击。

**修复**：

```js
mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
mainWindow.webContents.on('will-navigate', (e, url) => {
  if (!url.startsWith('app://')) { e.preventDefault(); shell.openExternal(url) }
})
```

### B-3. TTS 中止标志置位后永不清零，中止一次后 TTS 功能永久失效

**位置**：`backend/services/spark_tts_service.py:355`（置位）、`:222`（判断）、`:111-120`（任务启动重置块，已复核不含 `aborted`）

```python
def abort(self):
    self.status['aborted'] = True   # 只置位，从不复位
```

`_generate_thread` 入口重置了 `generating/progress/status/error/result` 等字段，唯独没有 `aborted`。用户点一次"中止生成"后，之后每次启动的 TTS 子进程都会在启动后 0.5 秒内被 terminate，TTS 功能在重启后端前完全不可用。

**修复**：在 `_generate_thread` 入口重置块中加 `self.status['aborted'] = False`；更彻底的做法是改用 per-task 的 cancellation event 而非全局标志。

### B-4. 切换视频文件后波形面板残留上一个视频的波形数据

**位置**：`frontend/src/components/WaveformPanel.vue:119-127`（已复核）

```js
watch(() => subtitleStore.videoFile, (val) => {
  if (!val) { /* 仅处理清空分支 */ }
})
```

`useAppActions.js` 的 `loadVideoFile` 直接 `setVideoFile(newFile)` 不经过 null。视频 A 生成波形后打开视频 B：`hasWaveform` 仍为 true、`duration` 仍是 A 的，播放头定位、字幕块定位、点击 seek 全部按错误时长映射，且界面看起来"正常"。`dubbingAudioFile` 的 watch（129-135 行）同样只处理清空分支。

**修复**：watch 改为 `(val, oldVal) => { if (!val || val !== oldVal) { 重置波形状态 } }`，或换文件时提示重新生成波形。

---

## 二、🟡 Important（应当修复）

### 安全

| # | 位置 | 问题 | 修复建议 |
|---|---|---|---|
| I-1 | `main.cjs:276-284` | `read-file` IPC 接受任意绝对路径并返回全部内容（utf-8），无来源/类型校验 | 限定字幕/项目文件扩展名白名单 + `event.senderFrame` 校验 |
| I-2 | `main.cjs:478-494` | `media://` 协议仅校验"绝对路径+存在"，无扩展名白名单；协议特权含 `bypassCSP`，渲染层可 fetch 任意本地文件；`existsSync` 对目录也返回 true | 加音视频扩展名白名单（与文件选择器过滤器一致）+ `statSync` 拒绝目录 |
| I-3 | `main.cjs:179-184` | `sandbox: false`，preload 可访问完整 Node API（当前只用 ipcRenderer，可直接开启 sandbox） | `sandbox: true` |
| I-4 | `backend/services/translation_service.py:440,472-477` | Gemini API Key 拼进 URL 查询串；`ConnectionError` 的 `str(e)` 含完整 URL（带 key），一路透传给前端并写入日志 | 改用请求头 `{'x-goog-api-key': api_key}` 或对异常消息脱敏 |
| I-5 | `backend/services/whisper_service.py:89` | 下载模型流程中自动执行 `pip install openai-whisper`，违反项目"接口内不 pip install"约定（`whisper_ctranslate2_service.py:37-46` 是正确范例） | 对齐 ct2 做法：ImportError 时返回安装提示 |
| I-6 | `backend/routes/settings.py:40-132` | 诊断/缓存路由共 8 处 `except Exception` 无日志，异常堆栈被吞，服务端零记录 | 每个分支补 `current_app.logger.exception(...)` |

### 错误传播与任务生命周期

| # | 位置 | 问题 | 修复建议 |
|---|---|---|---|
| I-7 | `backend/routes/translation.py:37-46` | 翻译引擎失败时服务层返回 `{'translated': 原文, 'error': ...}`，路由不检查 `error` 直接 200 → 前端拿到 `success: true` 且译文=原文，故障被伪装成"译文与原文相同" | `if result.get('error'): return fail(..., status=502)`（`spell_check.py:42-43` 是正确范例） |
| I-8 | `backend/services/whisper_cpp_service.py:110` | 模型下载 `requests.get(url, stream=True)` 无 timeout；连接黑洞时下载线程永久阻塞，`downloading=True` 永不释放，下载功能整体锁死 | `timeout=(10, 300)` + 捕获 Timeout |
| I-9 | `backend/services/transcription_service.py:79-93` | ffmpeg 提取音频时 stderr 用 PIPE 但循环中只消费 stdout；stderr 写满 64KB 管道缓冲后 ffmpeg 阻塞，任务卡死在 `extracting_audio` 且取消检查不执行 | `stderr=subprocess.STDOUT` 合并，或仿 `spark_tts_service.py:212-217` 起独立读取线程 |
| I-10 | `backend/services/transcription_service.py:199-214,315` | 取消后引擎进度回调仍把状态从 `cancelling` 覆盖回 `transcribing`，前端看到"取消失败"假象；openai whisper 阻塞推理无法中断 | 回调写入前判 `if not self._is_cancelled(task_id)`；推理不可中断至少注释声明 |
| I-11 | `backend/routes/hard_subtitle.py:44-47`、`tts_video.py:29-43` 及对应 service | 上传的视频/音频副本（上限 4GB/个）任务结束后不删除，连续处理多个大视频 24h 窗口内可积累数十 GB 写满磁盘 | `_task_thread` 的 finally 中删除上传副本（`transcription_service._cleanup_temp_files` 是正确范式） |
| I-12 | `backend/services/ffmpeg_task_service.py`（基类） | 长任务无并发上限：N 个请求 = N 线程 + N 个 ffmpeg 进程（x264 极吃 CPU/内存）；transcription 有 `MAX_CONCURRENT_JOBS=1` 信号量，两类任务资源策略不一致 | 基类加信号量/活跃任务上限，超限返回 429 或排队 |
| I-13 | `backend/routes/transcription.py:28-34` | 转录任务无重复提交防护，同一文件可重复全量转录 | 按"文件路径+参数"去重，返回已有 task_id |
| I-14 | `backend/routes/vosk.py:21` | Vosk 模型下载（1.8GB）在请求线程内同步执行最长 10 分钟，占用 waitress worker，违反"耗时走任务机制"约定 | 改后台线程 + status 轮询，与其他引擎一致 |

### 前端正确性与状态管理

| # | 位置 | 问题 | 修复建议 |
|---|---|---|---|
| I-15 | `WaveformPanel.vue:104`（SplitPane.vue:104） | SplitPane 嵌套时 `document.querySelector('.split-pane')` 取到最外层容器，拖动内层分隔条 `newPercent` 恒超 100 被 clamp 到极值，分隔条"卡死" | startResize 时保存正确根元素（`e.target.closest`）供 handleResize 复用 |
| I-16 | `EditPanel.vue:136-138` | 翻译异步竞态：请求返回前切换选中行，译文写入**新**选中的行 | 请求前捕获 index，响应后校验再写入 |
| I-17 | `VideoPlayer.vue:112-125` | Blob URL 泄漏：File→File / File→string 切换时旧 blob URL 不 revoke，内存无法回收 | watch 开头统一 revoke（注意现有回收条件判断的是新文件，恒为 false） |
| I-18 | `EditPanel.vue:84-88` + `subtitleStore.js:68-74` | `@input` 每个字符都调 `updateParagraphText` 且 store 内无条件全量快照入历史：连续输入一句话即填满 30 条撤销槽位，"撤销"形同虚设 | EditPanel 输入防抖 300ms，或 store 对同类连续编辑合并入栈 |
| I-19 | `WaveformPanel.vue:723-729` | 对整个 paragraphs 数组 deep watch，每键一次全量深遍历（含长字符串字段）+ 全画布重绘；文本编辑并不改变字幕块几何 | 改监听时间码签名或 store 维护轻量版本号 |
| I-20 | `SpeechRecognitionModal.vue:97-103` | 30 分钟超时定时器句柄不保存、不清理；旧定时器到期可能误杀**新**转录任务 | 保存句柄并在 `stopTracking()` 中 `clearTimeout` |
| I-21 | `HardSubtitleModal.vue:686-690` | Electron 路径模式下 `videoFile.value.name` 为 undefined → `.replace` 抛 TypeError，功能失败（`AddTtsToVideoModal.vue:257` 的 `getFileName()` 可直接复用）；另 `new File(...)` 以 Blob 内存绕开 `media://` 方案，大视频整段占内存 | 复用 getFileName 辅助函数；走路径方案 |
| I-22 | `SettingsDialog.vue:41-43` vs `SpeechRecognitionModal.vue:5,39-40` | 引擎/语言枚举在设置与识别弹窗间不一致：`openai-whisper` 无映射、语言显示裸值 "zh" | 抽取共享常量 ENGINE_OPTIONS / LANGUAGE_OPTIONS |
| I-23 | `subtitleStore.js:519-527` | `applySplitResults` 用 `new Paragraph(...)` 重建段落，**丢失全部译文及 style/actor/margin 等 ASS 属性**（`applyMergedSubtitles:499` 是正确范例） | 补齐字段赋值 |
| I-24 | `useAppActions.js:304-311` | Electron 打开项目时 `JSON.parse` 无 try-catch，损坏 `.stproj` 抛 unhandled rejection 无任何提示（浏览器路径有 try-catch，行为不一致） | 补 try-catch 与用户提示 |
| I-25 | `useCrashProtection.js:112-116` | 恢复确认框弹出期间 autoSave 已启动：空字幕快照触发 `removeItem(SESSION_KEY)`，确认框停留超 10s 后崩溃/断电 = 数据永久丢失 | 先 `await promptRestoreDraft()` 再 `startAutoSave()` |
| I-26 | `useAppActions.js:34-39` | `toggleTheme` 绕过 draft 约定直接改 settings；设置对话框打开时会用旧 draft 覆盖刚切换的主题 | 同步更新 settingsStore.draft |
| I-27 | `useCrashProtection.js:31-45` | autoSave 间隔 mount 时固化，修改 `autoSaveInterval` / 关闭开关需重挂组件才生效 | `watch(() => settings.fileTask, startAutoSave, { deep: true })` |
| I-28 | `WaveformPanel.vue:167-256` | 拖拽结束 mouseup 后浏览器仍派发 click → 触发 seek，播放位置跳到鼠标释放处 | mousedown 记录起点，位移超阈值（3px）时抑制后续 click |
| I-29 | `WaveformPanel.vue:11,21,137,144` | 勾选显示/隐藏波形后 canvas 重建，暂停态无 timeupdate，画布空白直到下次交互 | `watch([showOriginalWaveform, showDubbingWaveform], ...)` 触发重绘 |
| I-30 | `SpellCheckDialog.vue:272-323` | 循环体内 O(n²) 全量重编号 + 数组复制；确认修改逐行入栈（修 10 处 = 10 条撤销历史） | 重编号移到循环外；改批量更新单次入栈 |
| I-31 | `subtitleStore.js:76-81` vs `:68-74` | 译文修改不入撤销栈而文本修改入栈：文本可撤销、译文不可撤销，Ctrl+Z 会连带回退期间的文本修改 | 统一入栈语义 |
| I-32 | `subtitleStore.js` + `models/subtitle.js:136,185-197` | 撤销栈：每键全量深拷贝（5000 行 × 100 快照常驻内存）；运行时上限 100 与序列化上限 30 不一致，保存重开后可撤销步数骤降 | 上限统一为 30；时间码微调做 500ms 合并；长期考虑命令模式 |
| I-33 | `src/router/index.js` + `HomeView.vue` + `main.js:25` | router 为死代码：App.vue 无 `<router-view>`，HomeView 永不渲染且反向 import App 形成循环引用 | 移除 router 依赖（单页工作台不需要）或重构为 shell + router-view |
| I-34 | `src/main.js:15` + 5 处组件裸 axios | 双 HTTP 客户端轨道：全局 defaults 服务裸 axios 调用，绕过 ApiService 拦截器（无统一解壳、超时不一致）；`TtsPanel.vue:192` 等用相对路径 `/api/`，Electron 自定义协议 origin 下会请求失败 | 裸调用迁入 ApiService，删除全局 defaults |
| I-35 | `useAppActions.js:42-54` | `pickFile` 用户取消时隐藏 input 永久残留 document.body（每次"打开→取消"泄漏一个节点） | 补 `addEventListener('cancel', () => input.remove())` |
| I-36 | `backend/routes/waveform.py:185` 等 | 上传分支波形缓存键含每次不同的 uuid → 缓存永远 miss，写入的数 MB JSON 永不命中，只能等 24h 清理回收（磁盘泄漏） | 上传分支以内容摘要（sha256）为缓存键，或跳过缓存 |
| I-37 | `backend/routes/waveform.py:180,209` | `samples_per_second` 无上限校验，大值触发 `np.arange` 数 GB 分配 → OOM（前端自身 bug 同样可触发） | `min(max(1, value), 1000)` |
| I-38 | `backend/routes/transcription.py:28-34` + `app.py:15` | 转录无并发上限：连续提交 N 任务并行 N 线程，Whisper 以 GB 计的模型内存峰值不可控；SSE 长连接 × waitress 8 线程偏紧 | 信号量上限 1~2（与 I-12 一并收敛） |

---

## 三、🟢 Nit（可选，择要）

**后端**
- `config/settings.py:39-41`、`utils/file_utils.py:16-17`：`if not exists: makedirs` 存在 TOCTOU 竞态 → `os.makedirs(directory, exist_ok=True)`
- `routes/settings.py:13-22`：自制 `make_response` 与 `utils.response.fail` 重复且默认语义不一致（200 + error_code=None）→ 删除并改用 `fail()`
- `routes/transcription.py`：全文件裸 `jsonify({'error':...})`，error_code int/str 全局不统一
- `routes/waveform.py:141-142`：多声道 WAV `samples[::2]` 错位混合 → `samples[::channels]`
- `routes/waveform.py:61`：ffmpeg 转码固定 60s 超时，3 小时长视频低端机可能失败
- `whisper_cpp_service.py:152,184-187`：`mkdtemp` 目录在系统 TEMP（项目清理扫不到），取消路径永久残留
- `whisper_cpp_service.py:202-203` 等：裸 `except:` 捕获一切含 KeyboardInterrupt
- `whisper_cpp_service.py:180`：进度正则前缀可选 `(?:progress\s*=\s*)?` 等于无过滤
- `whisper_ctranslate2_service.py:10`：模型缓存无淘汰，多模型轮换持续吃内存 → LRU 上限 1-2
- `transcription_service.py:29`：`_jobs` 字典无 TTL，长时间运行内存只增不减（`ffmpeg_task_service` 的 1h TTL 是好范式）
- `hard_subtitle_service.py:134`：`f'{seconds:05.2f}'` 对 59.995 输出 `60.00`，分钟不进位 → 非法时间 `0:01:60.00`
- `routes/translation.py:9-15`：`SYNC_TRANSLATE_TIMEOUT` 是死分支与误导性注释
- `vosk_service.py:147-253`：Vosk 转录为死代码且 `sf.read()` 默认 float64 喂 int16 识别器会得到噪声
- `spark_tts_service.py:11`：库模块内 `logging.basicConfig` 覆盖应用日志配置

**前端**
- `vite.config.js:46-48`：`drop: ['console']` 连 `console.error/warn` 一起删，生产诊断通道静默 → 改 `pure: ['console.log', 'console.debug']`
- `settingsStore.js:157`：`window.matchMedia` 无守卫（jsdom 测试会炸）
- `uiStore.js:149-151`：`showMessage` 多定时器竞争提前关闭新消息
- `useKeyboardShortcuts.js:29`：modalOpen 用 `[style*="display: none"]` 内联样式匹配，脆弱且每次 keydown 查 DOM
- `package.json:13,40`：vue-tsc 死依赖；lint 内置 `--fix` 不适合 CI
- `VideoControls.vue:174-176`：`querySelector('.video-player')` 跨组件 CSS 类耦合
- `VideoControls.vue:241-251`：卸载时 `audioContext.close()`，一旦该组件被 v-if 卸载，已绑定的 video 元素永久静音（当前常驻不触发，潜伏雷）
- `VideoPlayer.vue:181-195`：`handleTimeUpdate` 每帧两次 O(n) 扫描可合并/二分
- `SubtitleList.vue:94`：`:key="viewStart + vi"` 位置键导致滚动时输入框重建丢焦点
- `CommandPalette.vue:91-102`：分组依赖"连续相同 group"，排序后同名组被拆散
- `ModelDownloadModal.vue:184`：200ms 轮询过于激进（5 req/s）
- `main.cjs:110-124`：`stopBackend` 两个平台分支代码完全相同；Windows 上 `kill('SIGTERM')` 不杀子进程树（ffmpeg 可能残留）→ `taskkill /pid /T /F`
- `useAppActions.js:348-352`：退出确认用原生 `confirm`，与全局 ElMessageBox 风格割裂

---

## 四、💡 Suggestion（替代方案）

1. **`file_path` 直读接口收敛**：`transcription.py:14-16`、`waveform.py:201-206` 接受任意本地路径无白名单（当前威胁模型可接受）；若未来开放局域网，建议改"文件注册句柄制"（前端注册路径换 token）
2. **统一响应包装降级**：`response.py:99-112` 每请求完整 parse+serialize 一次；全部路由显式走 `ok()/fail()` 后将兜底降为开发模式
3. **WAV 峰值分块计算**：`waveform.py:127` 整文件读入内存（1 小时 WAV ≈ 600MB）；改分块 + 在线聚合 min/max 峰值内存可降为常数级
4. **ct2 切分加重叠**：`whisper_ctranslate2_service.py:238-275` 15 秒硬切分无重叠，边界单词被截断
5. **uiStore 模式工厂**：25+ 组 `xxxVisible + xxxConfig` 可抽象 `createModalState()` 工厂，代码量减半
6. **waitForBackend 先开窗**：`main.cjs:496-503` 健康检查失败时用户面对 30s 无窗口空窗期，可先显示加载态
7. **波形双 canvas**：波形主体缓存为离屏层，播放头独立 canvas/DOM，timeupdate 只画 2px 竖线
8. **settingsStore 快照配额预检**：`saveSessionSnapshot` 复用 saveDraft 的 4.5MB 预检逻辑
9. **SSE 轮询降级**：`get_transcribe_status` 已存在，可作为 SSE 失败时的降级路径

---

## 五、🎉 Praise（值得保留的实现）

**安全与健壮性**
- 路径安全体系：自研 `sanitize_filename` 保留 Unicode 并注明不用 werkzeug 的原因；`tts.py:147` 删除接口追加 `os.path.commonpath` 双重校验；CORS 收紧为 localhost/`app://` 白名单而非 `*`
- `storage.js:74-87` 配额错误处理：QuotaExceededError 多形态识别 + 序列化失败分支 + 主进程 tmp+rename 原子写——完整无遗漏
- 波形缓存原子写（临时文件 + `os.replace`）与失败静默降级

**工程自觉**
- `waveform.py:73-92` 向量化峰值计算（`np.maximum/minimum.reduceat`），空块/边界全处理，注释解释"为什么"——全项目质量最高的函数
- `FFmpegTaskService`：stderr 环形缓冲防内存膨胀、终态 1h TTL 回收、跨平台工具定位
- `transcription_service`：`MAX_CONCURRENT_JOBS=1` 信号量排队 + 排队期间可取消、tqdm monkey-patch 在锁内安装/恢复
- 崩溃保护三件套（草稿 + 快照 + 恢复询问）链路闭环，错误提示有节流
- preload 的 IPC 监听器返回取消订阅函数且 `App.vue` 正确清理——教科书级
- `SubtitleList` 虚拟滚动（固定行高 + buffer 窗口 + 位移窗口）与行内编辑双提交防重入
- `SettingsDialog` 草稿模式完全符合"取消不动已应用设置"的约定
- `App.vue` 拖放用 dragDepth 计数正确处理 dragenter/leave 抖动
- 统一响应层"显式 ok()/fail() 为主 + after_request 兜底 + SSE/send_file 自动跳过"的渐进式设计

---

## 六、整体评价

### 架构
后端 Flask 四层（routes/services/utils/config）职责清晰，统一响应与全局异常兜底完整；前端 Pinia setup store + composables 分层规范，Vue 3 响应式用法无典型坑。两处架构漂移需要收敛：router 死代码（I-33）与双 HTTP 客户端轨道（I-34），提示存在"新旧方案并存"未清理。

### 亮点
对"持久化可靠性"和"本地安全"有系统性思考——配额防御、原子写、崩溃恢复、CORS 白名单、上传净化、临时目录周期回收层层设防；波形向量化计算、任务排队模型、虚拟滚动等实现高于同类项目平均水平。

### 主要风险（按优先级）
1. **Electron 安全纵深**（B-1/B-2 + I-1/I-2/I-3）：`app://` 路径穿越已实测验证，与导航拦截缺失组合后一旦渲染层被注入即升级为任意本地文件读取。本地单用户应用威胁模型下攻击门槛高，但成本极低（约 20 行修复），无理由不修。
2. **任务生命周期"最后一公里"**（B-3 + I-8/I-9/I-10）：中止标志不清零是必须立即修的功能级故障；下载无超时、stderr 死锁、状态覆盖说明异常/取消分支测试覆盖不足。
3. **错误传播不彻底**（I-7 + I-6）：翻译链路"失败返回 200 + 原文"会把故障伪装成正常结果，建议统一约定"服务层失败必须以非 2xx 暴露"。
4. **撤销栈性能与语义**（I-18/I-32）：每键全量快照使"30 条历史"约定在大文件场景形同虚设。
5. **磁盘治理**（I-11/I-36）：上传副本不删 + 波形缓存键失效，连续处理大视频存在写满磁盘风险。

### 修复路线图建议
- **第一批（发布前必须）**：B-1、B-2、B-3、B-4、I-7、I-24（共约半天工作量，全部为局部修复）
- **第二批（本迭代）**：I-1/I-2/I-3（Electron 加固）、I-8/I-9/I-10（任务健壮性）、I-18/I-32（撤销栈）、I-11（磁盘）
- **第三批（随迭代消化）**：其余 🟡 与值得做的 🟢/💡

---

*报告由 code-review-skill 生成；全部 🔴 级发现已经主审读码复核，🟡 级发现来自并行审查代理并经交叉验证。*
