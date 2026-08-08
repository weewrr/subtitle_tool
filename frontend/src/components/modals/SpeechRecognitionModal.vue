<template>
  <el-dialog v-model="visible" title="音频转文字" width="600px" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="!isTranscribing" :before-close="handleBeforeClose">
    <p class="description">通过 Whisper 语音识别从音频或视频生成字幕</p>
    <el-form label-width="80px" size="small">
      <el-form-item label="引擎"><el-select v-model="engine" style="width: 100%" :disabled="isTranscribing" @change="loadModels"><el-option label="OpenAI Whisper" value="openai" /><el-option label="Whisper.cpp" value="whisper-cpp" /><el-option label="Whisper-CTranslate2（推荐）" value="whisper-ctranslate2" /></el-select></el-form-item>
      <el-form-item label="语言"><el-select v-model="language" style="width: 100%" :disabled="isTranscribing"><el-option label="English" value="English" /><el-option label="Chinese" value="Chinese" /><el-option label="自动检测" value="Auto-detect" /></el-select></el-form-item>
      <el-form-item label="模型"><el-select v-model="selectedModel" style="width: 200px" :disabled="isTranscribing"><el-option v-for="model in models" :key="model.name" :label="model.label" :value="model.name" /></el-select><el-button style="margin-left: 8px" :disabled="isTranscribing" @click="showDownloadModal">...</el-button><el-button :disabled="isTranscribing" @click="openModelFolder">打开模型文件夹</el-button></el-form-item>
    </el-form>
    <el-checkbox v-model="useGpu" :disabled="isTranscribing">GPU 加速</el-checkbox>
    <div v-if="isTranscribing" class="progress-section"><el-progress :percentage="progress" :status="progressStatus" /><p class="progress-text">{{ progressText }}</p></div>
    <template #footer><el-button :disabled="isTranscribing" @click="showBatchMode">批处理模式</el-button><el-button v-if="isTranscribing" type="danger" @click="cancelTask">取消任务</el-button><el-button v-else type="primary" @click="startTranscribe">生成</el-button><el-button :disabled="isTranscribing" @click="close">关闭</el-button></template>
  </el-dialog>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { apiService } from '@/services/ApiService'
import { getBackendBaseUrl } from '@/utils/runtime'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()
const settingsStore = useSettingsStore()
const visible = computed({ get: () => uiStore.speechRecognitionModalVisible, set: value => value ? uiStore.showSpeechRecognitionModal() : uiStore.hideSpeechRecognitionModal() })
const engine = ref('whisper-ctranslate2'), language = ref('Auto-detect'), selectedModel = ref('base'), models = ref([]), useGpu = ref(true)
const isTranscribing = ref(false), progress = ref(0), progressStatus = ref(''), progressText = ref('准备中...')
let taskId = null, eventSource = null, pollTimer = null

watch(visible, value => {
  if (value) {
    // 从全局设置读取默认值，但不覆盖用户单次修改
    const rec = settingsStore.settings.recognition
    engine.value = rec.defaultEngine || 'whisper-ctranslate2'
    if (engine.value === 'faster-whisper') engine.value = 'whisper-ctranslate2' // 映射
    language.value = rec.defaultLanguage === 'auto' ? 'Auto-detect' : rec.defaultLanguage
    useGpu.value = rec.useGpu
    loadModels()
  }
})
onUnmounted(stopTracking)

async function loadModels() {
  try {
    let list
    if (engine.value === 'whisper-cpp') list = await apiService.listWhisperCppModels()
    else if (engine.value === 'whisper-ctranslate2') list = await apiService.listWhisperCTranslate2Models()
    else list = await apiService.listModels()
    models.value = list.map(item => ({ name: item.name, label: `${item.name} (${item.size})${item.downloaded ? ' ✓' : ''}` }))
    if (models.value.length) selectedModel.value = models.value[0].name
  } catch { models.value = []; ElMessage.error('加载模型列表失败') }
}
function showDownloadModal() { uiStore.hideSpeechRecognitionModal(); uiStore.showModelDownloadModal(engine.value) }
async function openModelFolder() { try { const result = await apiService.openModelFolder(); ElMessage.success(result.message || '已打开模型目录') } catch (error) { ElMessage.error(`打开失败: ${error.message}`) } }
function showBatchMode() { uiStore.hideSpeechRecognitionModal(); uiStore.showBatchProcessingModal() }

async function startTranscribe() {
  if (!subtitleStore.videoFile) return ElMessage.warning('请先打开视频或音频文件')
  isTranscribing.value = true; progress.value = 0; progressStatus.value = ''; progressText.value = '正在上传文件...'
  try {
    const task = await apiService.transcribe(subtitleStore.videoFile, selectedModel.value, language.value, engine.value, useGpu.value)
    taskId = task.task_id
    progressText.value = '任务已启动...'
    openEventStream()
  } catch (error) { isTranscribing.value = false; ElMessage.error(`识别失败: ${error.message}`) }
}
function openEventStream() {
  closeEventStream()
  eventSource = new EventSource(`${getBackendBaseUrl()}/api/transcribe/${taskId}/events`)
  eventSource.onmessage = event => handleStatus(JSON.parse(event.data))
  eventSource.onerror = () => { closeEventStream(); startPolling() }
}
function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => { try { handleStatus(await apiService.getTranscribeStatus(taskId)) } catch (error) { console.error('获取转录进度失败', error) } }, 1000)
}
async function handleStatus(status) {
  progress.value = Math.round(status.progress || 0)
  const detail = progressDetail(status)
  if (status.status === 'extracting_audio') progressText.value = `正在提取音频... ${detail}`
  else if (status.status === 'loading_model') progressText.value = '正在加载模型...'
  else if (status.status === 'transcribing') progressText.value = `正在识别中... ${detail}`
  else if (status.status === 'generating_subtitles') progressText.value = '正在生成字幕文件...'
  else if (status.status === 'completed') {
    stopTracking(); progress.value = 100; progressStatus.value = 'success'; progressText.value = '正在获取结果...'
    try {
      const result = await apiService.getTranscribeResult(taskId)
      if (!result?.segments?.length) throw new Error('未识别到语音内容')
      subtitleStore.loadFromTranscription(result.segments, subtitleStore.videoFile.name.replace(/\.[^/.]+$/, '') + '.srt')
      ElMessage.success(`识别完成，共 ${result.segments.length} 条字幕`); close()
    } catch (error) { isTranscribing.value = false; ElMessage.error(`获取结果失败: ${error.message}`) }
  } else if (status.status === 'error') { stopTracking(); progressStatus.value = 'exception'; isTranscribing.value = false; ElMessage.error(`识别失败: ${status.error || '未知错误'}`) }
  else if (status.status === 'cancelled') { stopTracking(); isTranscribing.value = false; ElMessage.info('识别任务已取消') }
}
function progressDetail(status) {
  const percent = `${Math.round(status.progress || 0)}%`
  if (!status.media_duration || !status.processed_seconds) return percent
  const time = value => new Date(value * 1000).toISOString().slice(14, 19)
  return `${percent} · ${time(status.processed_seconds)} / ${time(status.media_duration)}${status.eta_seconds ? ` · 预计剩余 ${time(status.eta_seconds)}` : ''}`
}
async function cancelTask() { if (taskId) { await apiService.cancelTranscribe(taskId); progressText.value = '正在取消任务...' } }
function closeEventStream() { if (eventSource) { eventSource.close(); eventSource = null } }
function stopTracking() { closeEventStream(); if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }
function handleBeforeClose(done) { if (isTranscribing.value) return ElMessage.warning('请先取消或等待任务完成'); done() }
function close() { isTranscribing.value = false; stopTracking(); taskId = null; uiStore.hideSpeechRecognitionModal() }
</script>

<style lang="scss" scoped>
.description { margin-bottom: 16px; color: $text-secondary; }
.progress-section {
  margin-top: 16px;
  :deep(.el-progress__text) { color: #fff; }
  .progress-text { margin-top: 8px; font-size: $font-size-base; color: $text-secondary; text-align: center; }
}
:deep(.el-checkbox) { display: block; margin: 8px 0; }
</style>
