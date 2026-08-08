<template>
  <el-dialog
    v-model="dialogVisible"
    title="文本转语音添加到视频"
    width="560px"
    :close-on-click-modal="!isProcessing"
    :close-on-press-escape="!isProcessing"
    :show-close="!isProcessing"
    @close="handleClose"
  >
    <div class="tts-video-modal">
      <el-alert
        title="将原视频声音静音，并合并 TTS 配音音频导出为新视频"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <div class="resource-list">
        <div class="resource-item">
          <el-icon class="resource-icon"><VideoPlay /></el-icon>
          <div class="resource-info">
            <div class="resource-label">视频</div>
            <div class="resource-value" :title="videoName">{{ videoName || '未加载' }}</div>
          </div>
          <el-tag v-if="videoName" type="success" size="small">已加载</el-tag>
          <el-tag v-else type="info" size="small">未加载</el-tag>
        </div>
        <div class="resource-item">
          <el-icon class="resource-icon"><Headset /></el-icon>
          <div class="resource-info">
            <div class="resource-label">配音音频</div>
            <div class="resource-value" :title="audioName">{{ audioName || '未加载' }}</div>
          </div>
          <el-tag v-if="audioName" type="success" size="small">已加载</el-tag>
          <el-tag v-else type="info" size="small">未加载</el-tag>
        </div>
      </div>

      <div v-if="isProcessing" class="progress-section">
        <el-progress :percentage="progress" :status="progressStatus" />
        <p class="progress-text">{{ progressText }}</p>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" :disabled="isProcessing">关闭</el-button>
        <el-button
          v-if="isProcessing"
          type="danger"
          @click="abortGeneration"
        >停止</el-button>
        <el-button
          v-else
          type="primary"
          :disabled="!canGenerate"
          @click="handleGenerate"
        >开始生成</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Headset } from '@element-plus/icons-vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { getBackendBaseUrl } from '@/utils/runtime'
import axios from 'axios'

const subtitleStore = useSubtitleStore()
const uiStore = useUIStore()

const dialogVisible = ref(false)
const isProcessing = ref(false)
const progress = ref(0)
const progressStatus = ref('')
const progressText = ref('准备中...')
let pollingInterval = null

const videoFile = computed(() => subtitleStore.videoFile)
const audioFile = computed(() => subtitleStore.dubbingAudioFile)

// 兼容 Electron（字符串路径）和浏览器（File 对象）
function getFileName(file) {
  if (!file) return ''
  if (typeof file === 'string') {
    const parts = file.replace(/\\/g, '/').split('/')
    return parts[parts.length - 1] || file
  }
  return file.name || ''
}

const videoName = computed(() => getFileName(videoFile.value))
const audioName = computed(() => getFileName(audioFile.value))
const canGenerate = computed(() => !!videoFile.value && !!audioFile.value)

watch(() => uiStore.addTtsToVideoModalVisible, (val) => {
  if (val) {
    resetState()
    dialogVisible.value = true
  } else {
    dialogVisible.value = false
  }
})

watch(dialogVisible, (val) => {
  if (!val) {
    uiStore.hideAddTtsToVideoModal()
    if (isProcessing.value) {
      // 对话框关闭时停止轮询，但不中止后端任务
      stopPolling()
    }
  }
})

function resetState() {
  isProcessing.value = false
  progress.value = 0
  progressStatus.value = ''
  progressText.value = '准备中...'
}

function handleClose() {
  if (isProcessing.value) return
  dialogVisible.value = false
}

async function handleGenerate() {
  if (!videoFile.value) {
    ElMessage.warning('请先打开视频文件')
    return
  }
  if (!audioFile.value) {
    ElMessage.warning('请先在文本转语音区域加载配音音频')
    return
  }

  isProcessing.value = true
  progress.value = 0
  progressStatus.value = ''
  progressText.value = '正在提交任务...'

  try {
    const formData = new FormData()
    // 视频文件
    if (typeof videoFile.value === 'string') {
      formData.append('video_path', videoFile.value)
    } else {
      formData.append('video', videoFile.value)
    }
    // 音频文件
    if (typeof audioFile.value === 'string') {
      formData.append('audio_path', audioFile.value)
    } else {
      formData.append('audio', audioFile.value)
    }

    await axios.post('/api/tts-video/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    progressText.value = '正在处理视频...'
    startStatusPolling()
  } catch (error) {
    isProcessing.value = false
    ElMessage.error('生成失败: ' + (error.response?.data?.error || error.message))
  }
}

function startStatusPolling() {
  stopPolling()
  const pollStatus = async () => {
    if (!isProcessing.value) {
      stopPolling()
      return
    }
    try {
      const response = await axios.get('/api/tts-video/status')
      const status = response.data
      progress.value = Math.round(status.progress || 0)

      if (status.status === 'completed') {
        isProcessing.value = false
        progress.value = 100
        progressStatus.value = 'success'
        progressText.value = '生成成功，正在下载结果...'
        stopPolling()
        await downloadAndUpdateVideo()
        ElMessage.success('配音视频已生成并更新到视频区域')
        setTimeout(() => {
          dialogVisible.value = false
        }, 1000)
      } else if (status.status === 'error') {
        isProcessing.value = false
        progressStatus.value = 'exception'
        progressText.value = '生成失败'
        stopPolling()
        ElMessage.error('生成失败: ' + (status.error || '未知错误'))
      } else if (status.status === 'aborted') {
        isProcessing.value = false
        progressStatus.value = ''
        progressText.value = '已停止'
        stopPolling()
        ElMessage.info('已停止生成')
      } else if (status.status === 'processing') {
        progressStatus.value = ''
        progressText.value = `正在合并配音... ${progress.value}%`
      }
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  }
  pollingInterval = setInterval(pollStatus, 1000)
  pollStatus()
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

async function abortGeneration() {
  try {
    await axios.post('/api/tts-video/abort')
    progressText.value = '正在停止...'
  } catch (error) {
    console.error('停止失败:', error)
  }
}

async function downloadAndUpdateVideo() {
  try {
    const response = await axios.get('/api/tts-video/download', {
      responseType: 'blob'
    })
    const blob = new Blob([response.data], { type: 'video/mp4' })
    const baseName = getFileName(videoFile.value).replace(/\.[^/.]+$/, '') || 'video'
    const file = new File([blob], `${baseName}_tts.mp4`, { type: 'video/mp4' })
    subtitleStore.setVideoFile(file)
  } catch (error) {
    console.error('下载并更新视频失败:', error)
    ElMessage.error('更新视频失败: ' + (error.message || '未知错误'))
  }
}

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.tts-video-modal {
  .resource-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
  }

  .resource-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border: 1px solid var(--el-border-color);
    border-radius: 6px;
    background: var(--el-fill-color-light);

    .resource-icon {
      font-size: 24px;
      color: var(--el-color-primary);
      flex-shrink: 0;
    }

    .resource-info {
      flex: 1;
      min-width: 0;
    }

    .resource-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-bottom: 2px;
    }

    .resource-value {
      font-size: 13px;
      color: var(--el-text-color-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .progress-section {
    margin-top: 8px;

    .progress-text {
      margin-top: 8px;
      font-size: 13px;
      color: var(--el-text-color-secondary);
      text-align: center;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
