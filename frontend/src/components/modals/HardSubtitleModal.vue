<template>
  <el-dialog
    v-model="dialogVisible"
    title="生成带硬字幕的视频"
    width="900px"
    :close-on-click-modal="!isProcessing"
    :close-on-press-escape="!isProcessing"
    @close="handleClose"
    top="3vh"
    custom-class="hard-subtitle-dialog"
  >
    <div class="hard-subtitle-modal">
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="panel">
            <div class="panel-title">设置</div>
            <el-form label-position="top" size="small">
              <el-row :gutter="10">
                <el-col :span="12">
                  <el-form-item label="字体大小">
                    <el-input-number v-model="styleConfig.fontSize" :min="25" :max="75" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="轮廓">
                    <el-input-number v-model="styleConfig.outline" :min="0" :max="20" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="10">
                <el-col :span="12">
                  <el-form-item label="字体系列">
                    <el-select v-model="styleConfig.fontName" style="width: 100%">
                      <el-option label="Arial" value="Arial" />
                      <el-option label="Microsoft YaHei UI" value="Microsoft YaHei UI" />
                      <el-option label="SimHei" value="SimHei" />
                      <el-option label="SimSun" value="SimSun" />
                      <el-option label="KaiTi" value="KaiTi" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item>
                    <el-checkbox v-model="styleConfig.bold">粗体</el-checkbox>
                    <el-checkbox v-model="styleConfig.useOutlineColor" style="margin-left: 10px">实边框(使用轮廓色)</el-checkbox>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="10">
                <el-col :span="12">
                  <el-form-item label="文字颜色">
                    <el-color-picker v-model="styleConfig.textColor" show-alpha />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="边框颜色">
                    <el-color-picker v-model="styleConfig.outlineColor" show-alpha />
                  </el-form-item>
                </el-col>
              </el-row>

            </el-form>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="panel video-panel">
            <div class="video-preview">
              <div class="preview-placeholder" v-if="!videoFile">
                <el-icon><VideoPlay /></el-icon>
                <div>视频预览</div>
              </div>
              <div v-else class="video-container" ref="videoContainer" @click="handleContainerClick">
                <div class="video-player-wrapper">
                  <video
                    ref="videoPreview"
                    :src="videoUrl"
                    @timeupdate="handleTimeUpdate"
                    @play="handleVideoPlayState"
                    @pause="handleVideoPauseState"
                    @loadedmetadata="handleVideoLoadedMetadata"
                  />
                  <div class="subtitle-overlay" ref="subtitleOverlay">
                    <div
                      v-if="currentSubtitle"
                      class="subtitle-text"
                      :style="subtitleStyle"
                      @mousedown="startDragSubtitle"
                    >
                      {{ currentSubtitle }}
                    </div>
                  </div>
                </div>
                <div v-if="isFullscreen" class="fullscreen-controls" @click.stop>
                  <el-slider
                    v-model="previewProgress"
                    :max="100"
                    :show-tooltip="false"
                    @input="handlePreviewProgressChange"
                    @mousedown="isDraggingProgress = true"
                    @mouseup="isDraggingProgress = false"
                    class="progress-slider"
                  />
                  <div class="controls-bar">
                    <div class="left-controls">
                      <el-button
                        :icon="previewIsPlaying ? VideoPause : VideoPlay"
                        @click="toggleVideoPlay"
                        size="small"
                      />
                      <el-button
                        :icon="RefreshLeft"
                        @click="resetPreviewVideo"
                        size="small"
                      />
                    </div>
                    <span class="time">{{ previewCurrentTime }} / {{ previewDuration }}</span>
                    <el-button
                      class="fullscreen-btn"
                      :icon="FullScreen"
                      @click="toggleFullScreen"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
            <div v-if="videoFile && !isFullscreen" class="preview-video-controls" style="display: flex; flex-direction: column; gap: 8px; width: 100%; padding: 8px; box-sizing: border-box;">
              <el-slider
                v-model="previewProgress"
                :max="100"
                :disabled="!videoFile"
                :show-tooltip="false"
                @input="handlePreviewProgressChange"
                @mousedown="isDraggingProgress = true"
                @mouseup="isDraggingProgress = false"
                style="width: 100%;"
              />
              <div class="preview-buttons" style="display: flex; align-items: center; flex-wrap: nowrap; width: 100%; gap: 8px;">
                <div class="left-controls" style="display: flex; align-items: center; flex-wrap: nowrap; gap: 8px;">
                  <el-button
                    :icon="previewIsPlaying ? VideoPause : VideoPlay"
                    @click="toggleVideoPlay"
                    :disabled="!videoFile"
                    size="small"
                    style="flex-shrink: 0;"
                  />
                  <el-button
                    :icon="RefreshLeft"
                    @click="resetPreviewVideo"
                    :disabled="!videoFile"
                    size="small"
                    style="flex-shrink: 0;"
                  />
                </div>
                <span class="preview-time" style="margin: 0 8px; white-space: nowrap; flex-shrink: 0; font-size: 12px;">{{ previewCurrentTime }} / {{ previewDuration }}</span>
                <el-button
                  class="fullscreen-btn"
                  :icon="FullScreen"
                  @click="toggleFullScreen"
                  :disabled="!videoFile"
                  size="small"
                  style="margin-left: auto; flex-shrink: 0;"
                />
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" :disabled="isProcessing">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="isProcessing" :disabled="!videoFile">
          {{ isProcessing ? (canStop ? '停止' : '处理中...') : '确定' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, RefreshLeft, FullScreen } from '@element-plus/icons-vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { getBackendBaseUrl } from '@/utils/runtime'
import axios from 'axios'

const emit = defineEmits(['close'])

const subtitleStore = useSubtitleStore()
const uiStore = useUIStore()

const dialogVisible = ref(false)
const isProcessing = ref(false)
const canStop = ref(false)
const videoPreview = ref(null)
const videoContainer = ref(null)
const subtitleOverlay = ref(null)
const currentSubtitle = ref('')
const currentTime = ref(0)
const previewIsPlaying = ref(false)
const previewProgress = ref(0)
const previewCurrentTime = ref('00:00:00.000')
const previewDuration = ref('00:00:00.000')
const previewDurationSeconds = ref(0)
const videoResolution = ref({ width: 1280, height: 720 })
const isFullscreen = ref(false)
const subtitlePosition = ref({ y: 10 })
const isDraggingSubtitle = ref(false)
const isDraggingProgress = ref(false)
const generatedVideoUrl = ref('')
let subtitleWatchers = []

const videoFile = computed(() => subtitleStore.videoFile)
const videoUrl = computed(() => {
  if (generatedVideoUrl.value) {
    return generatedVideoUrl.value
  }
  if (!videoFile.value) return ''
  if (typeof videoFile.value === 'string') {
    const encodedPath = encodeURIComponent(videoFile.value)
    return `${getBackendBaseUrl()}/api/video/serve?path=${encodedPath}`
  }
  return URL.createObjectURL(videoFile.value)
})

const subtitleStyle = computed(() => {
  const outlineSize = styleConfig.value.useOutlineColor ? Math.max(1, Math.floor(styleConfig.value.outline / 2)) : 0
  let textShadow = ''
  
  if (outlineSize > 0) {
    const shadows = []
    for (let x = -outlineSize; x <= outlineSize; x++) {
      for (let y = -outlineSize; y <= outlineSize; y++) {
        if (x !== 0 || y !== 0) {
          shadows.push(`${x}px ${y}px 0 ${styleConfig.value.outlineColor}`)
        }
      }
    }
    textShadow = shadows.join(', ')
  }
  
  let fontSize = 15
  if (isFullscreen.value && videoContainer.value) {
    const displayHeight = videoContainer.value.offsetHeight
    const videoHeight = videoResolution.value.height || 1080
    const scale = displayHeight / videoHeight
    fontSize = Math.round(styleConfig.value.fontSize * scale)
  }
  
  return {
    fontFamily: styleConfig.value.fontName,
    fontSize: `${fontSize}px`,
    fontWeight: styleConfig.value.bold ? 'bold' : 'normal',
    color: styleConfig.value.textColor,
    textShadow: textShadow || 'none',
    textAlign: 'center',
    lineHeight: '1.4',
    bottom: `${subtitlePosition.value.y}px`,
    cursor: 'move',
    userSelect: 'none'
  }
})

const styleConfig = ref({
  fontSize: 30,
  outline: 6,
  fontName: 'Microsoft YaHei UI',
  bold: false,
  useOutlineColor: false,
  textColor: '#FFFFFF',
  outlineColor: '#000000'
})

function formatTime(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function handleKeyDown(event) {
  if (!videoPreview.value) return
  
  if (event.key === 'ArrowLeft') {
    videoPreview.value.currentTime = Math.max(0, videoPreview.value.currentTime - 5)
  } else if (event.key === 'ArrowRight') {
    videoPreview.value.currentTime = Math.min(previewDurationSeconds.value, videoPreview.value.currentTime + 5)
  }
}

function handleContainerClick(event) {
  if (event.target.closest('.fullscreen-controls') || event.target.closest('.preview-video-controls')) return
  
  if (videoPreview.value) {
    toggleVideoPlay()
  }
}

function open() {
  dialogVisible.value = true
  resetState()
  addEventListeners()
}

function close() {
  dialogVisible.value = false
  uiStore.hideHardSubtitleModal()
  removeEventListeners()
  if (videoPreview.value) {
    videoPreview.value.pause()
    videoPreview.value.currentTime = 0
  }
  previewIsPlaying.value = false
  previewProgress.value = 0
  previewCurrentTime.value = '00:00:00.000'
  subtitlePosition.value = { y: 10 }
}

function resetState() {
  isProcessing.value = false
  canStop.value = false
  currentSubtitle.value = ''
  currentTime.value = 0
  generatedVideoUrl.value = ''
}

function handleClose() {
  if (isProcessing.value) {
    return
  }
  
  close()
  emit('close')
}

function handleVideoPlayState() {
  previewIsPlaying.value = true
}

function handleVideoPauseState() {
  previewIsPlaying.value = false
}

function handleVideoLoadedMetadata() {
  if (videoPreview.value) {
    previewDurationSeconds.value = videoPreview.value.duration
    previewDuration.value = formatTime(videoPreview.value.duration)
    videoResolution.value = {
      width: videoPreview.value.videoWidth || 1280,
      height: videoPreview.value.videoHeight || 720
    }
  }
}

function toggleVideoPlay() {
  if (videoPreview.value) {
    if (videoPreview.value.ended) {
      videoPreview.value.currentTime = 0
      videoPreview.value.play()
    } else if (videoPreview.value.paused) {
      videoPreview.value.play()
    } else {
      videoPreview.value.pause()
    }
  }
}

function toggleFullScreen() {
  if (!videoContainer.value) return
  
  if (!document.fullscreenElement) {
    videoContainer.value.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

function startDragSubtitle(event) {
  if (!subtitleOverlay.value) return
  
  isDraggingSubtitle.value = true
  const startY = event.clientY
  const startPosition = subtitlePosition.value.y
  
  event.preventDefault()
  
  function handleMouseMove(e) {
    if (!isDraggingSubtitle.value) return
    
    const deltaY = startY - e.clientY
    const containerHeight = subtitleOverlay.value.parentElement.offsetHeight
    const maxBottom = containerHeight - 50
    
    subtitlePosition.value.y = Math.max(5, Math.min(maxBottom, startPosition + deltaY))
  }
  
  function handleMouseUp() {
    isDraggingSubtitle.value = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
  
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

function addEventListeners() {
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('keydown', handleKeyDown)
}

function removeEventListeners() {
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('keydown', handleKeyDown)
}

function resetPreviewVideo() {
  if (videoPreview.value) {
    videoPreview.value.pause()
    videoPreview.value.currentTime = 0
    previewIsPlaying.value = false
    previewProgress.value = 0
    previewCurrentTime.value = formatTime(0)
  }
}

function handlePreviewProgressChange(value) {
  if (videoPreview.value && previewDurationSeconds.value > 0) {
    const newTime = (value / 100) * previewDurationSeconds.value
    videoPreview.value.currentTime = Math.min(newTime, previewDurationSeconds.value - 0.1)
  }
}

function handleTimeUpdate() {
  if (!videoPreview.value) return
  
  const time = videoPreview.value.currentTime
  currentTime.value = time
  
  previewCurrentTime.value = formatTime(time)
  if (previewDurationSeconds.value > 0 && !isDraggingProgress.value) {
    previewProgress.value = (time / previewDurationSeconds.value) * 100
  }
  
  if (generatedVideoUrl.value) {
    currentSubtitle.value = ''
    return
  }

  if (!subtitleStore.currentSubtitle || subtitleStore.paragraphCount === 0) {
    currentSubtitle.value = ''
    return
  }

  let foundSubtitle = null
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    const startSeconds = p.startTime.totalMilliseconds / 1000
    const endSeconds = p.endTime.totalMilliseconds / 1000
    
    if (time >= startSeconds && time <= endSeconds) {
      foundSubtitle = p.translation || p.text
      break
    }
  }
  
  if (currentSubtitle.value !== foundSubtitle) {
    currentSubtitle.value = foundSubtitle || ''
  }
}

let pollingInterval = null

async function handleGenerate() {
  if (!videoFile.value) {
    ElMessage.warning('请先打开视频文件')
    return
  }

  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }

  if (isProcessing.value && canStop.value) {
    abortGeneration()
    return
  }

  isProcessing.value = true
  canStop.value = true

  try {
    const subtitles = subtitleStore.currentSubtitle.paragraphs.map(p => ({
      start: p.startTime.toSRTString(),
      end: p.endTime.toSRTString(),
      text: p.translation || p.text
    }))

    const config = {
      style: {
        font_name: styleConfig.value.fontName,
        font_size: styleConfig.value.fontSize,
        bold: styleConfig.value.bold,
        outline: styleConfig.value.outline,
        use_outline_color: styleConfig.value.useOutlineColor,
        text_color: styleConfig.value.textColor,
        outline_color: styleConfig.value.outlineColor,
        margin_bottom: subtitlePosition.value.y,
        width: videoResolution.value.width,
        height: videoResolution.value.height
      },
      video_encoding: 'libx264',
      preset: 'medium',
      crf: 23,
      audio_encoding: 'copy'
    }

    let response
    if (typeof videoFile.value === 'string') {
      response = await axios.post('/api/hard-subtitle/generate-from-path', {
        video_path: videoFile.value,
        subtitle: subtitles,
        config: config
      })
    } else {
      const formData = new FormData()
      formData.append('video', videoFile.value)
      formData.append('subtitle', JSON.stringify(subtitles))
      formData.append('config', JSON.stringify(config))
      response = await axios.post('/api/hard-subtitle/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }

    if (response.data.status === 'started') {
      startStatusPolling()
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.response?.data?.error || error.message))
    isProcessing.value = false
    canStop.value = false
  }
}

function startStatusPolling() {
  // 清除之前的 polling 间隔，避免多个 polling 进程同时运行
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
  
  const pollStatus = async () => {
    if (!isProcessing.value) {
      if (pollingInterval) {
        clearInterval(pollingInterval)
        pollingInterval = null
      }
      return
    }
    
    try {
      const response = await axios.get('/api/hard-subtitle/status')
      const status = response.data

      if (status.status === 'completed') {
        isProcessing.value = false
        canStop.value = false
        ElMessage.success('生成成功!')
        
        generatedVideoUrl.value = '/api/hard-subtitle/download?t=' + Date.now()
        if (videoPreview.value) {
          videoPreview.value.load()
          videoPreview.value.currentTime = 0
        }
        previewProgress.value = 0
        previewCurrentTime.value = '00:00:00.000'
        previewIsPlaying.value = false
        
        // 下载生成的视频并更新到 subtitleStore
        downloadAndUpdateVideo()
        
        // 清除 polling 间隔
        if (pollingInterval) {
          clearInterval(pollingInterval)
          pollingInterval = null
        }
        
        setTimeout(() => {
          close()
          emit('close')
        }, 1000)
      } else if (status.status === 'error') {
        isProcessing.value = false
        canStop.value = false
        ElMessage.error('生成失败: ' + (status.error || '未知错误'))
        
        // 清除 polling 间隔
        if (pollingInterval) {
          clearInterval(pollingInterval)
          pollingInterval = null
        }
      } else if (status.status === 'aborted') {
        isProcessing.value = false
        canStop.value = false
        ElMessage.info('已停止生成')
        
        // 清除 polling 间隔
        if (pollingInterval) {
          clearInterval(pollingInterval)
          pollingInterval = null
        }
      }
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  }
  
  // 使用 setInterval 代替 setTimeout，确保只有一个 polling 进程
  pollingInterval = setInterval(pollStatus, 1000) // 增加间隔到 1 秒，减少请求频率
  
  // 立即执行一次，避免等待第一个间隔
  pollStatus()
}

async function abortGeneration() {
  try {
    await axios.post('/api/hard-subtitle/abort')
    canStop.value = false
  } catch (error) {
    console.error('停止失败:', error)
  }
}

async function downloadAndUpdateVideo() {
  try {
    // 下载生成的视频
    const response = await axios.get('/api/hard-subtitle/download', {
      responseType: 'blob'
    })
    
    // 创建 Blob 对象
    const blob = new Blob([response.data], { type: 'video/mp4' })
    
    // 创建 File 对象
    const fileName = videoFile.value ? videoFile.value.name.replace(/\.[^/.]+$/, '') + '_hard_subtitle.mp4' : 'hard_subtitle.mp4'
    const file = new File([blob], fileName, { type: 'video/mp4' })
    
    // 更新 subtitleStore 中的视频文件
    subtitleStore.setVideoFile(file)
    
    // 通知用户视频已更新
    ElMessage.success('视频已更新为带硬字幕版本')
  } catch (error) {
    console.error('下载并更新视频失败:', error)
    ElMessage.error('更新视频失败: ' + (error.message || '未知错误'))
  }
}

onUnmounted(() => {
  subtitleWatchers.forEach(w => w())
  removeEventListeners()
})

defineExpose({ open, close })
</script>

<style lang="scss" scoped>
.hard-subtitle-modal {
  display: flex;
  flex-direction: column;
  height: 100%;

  .el-row {
    flex: 1;
  }

  .el-col {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .panel {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    padding: 15px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .video-panel {
    flex: 1.2;
  }

  .panel-title {
    font-weight: bold;
    margin-bottom: 10px;
    font-size: 14px;
  }

  .time-input {
    display: flex;
    align-items: center;
    gap: 4px;

    .el-input-number {
      width: 60px;
    }

    span {
      font-size: 14px;
    }
  }

  .video-preview {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f5f7fa;
    border-radius: 4px;
    position: relative;
    overflow: hidden;
    min-height: 200px;

    .preview-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      color: #909399;
      gap: 8px;

      .el-icon {
        font-size: 48px;
      }
    }

    .video-container {
      position: relative;
      width: 100%;
      background-color: #1a1a1a;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-radius: 4px;
      
      &:fullscreen {
        width: 100vw;
        height: 100vh;
        
        .video-player-wrapper {
          height: calc(100vh - 80px);
        }
        
        video {
          height: 100%;
        }
      }
    }

    .video-player-wrapper {
      position: relative;
      width: 100%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      line-height: 0;

      video {
        max-width: 100%;
        max-height: 100%;
        display: block;
        object-fit: contain;
      }
    }

    .subtitle-overlay {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      top: 0;
      padding: 0 10px;
      pointer-events: none;
      display: flex;
      justify-content: center;
      align-items: flex-end;
      z-index: 100;
    }

    .subtitle-text {
      display: inline-block;
      padding: 4px 12px;
      white-space: pre-wrap;
      max-width: 90%;
      text-align: center;
      border-radius: 4px;
      word-break: break-word;
      pointer-events: auto;
      position: absolute;
    }

    .preview-video-controls {
      background-color: #f5f7fa;
      padding: 8px;
      display: flex !important;
      flex-direction: row !important;
      align-items: center !important;
      gap: 12px !important;
      border: 1px solid #dcdfe6;
      border-top: none;
      margin-top: 10px;
      width: 100% !important;

      .el-slider {
        flex: 1 !important;
        min-width: 200px;
      }

      .preview-buttons {
        display: flex !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
        min-width: 300px;

        .left-controls {
          display: flex !important;
          align-items: center !important;
          flex-wrap: nowrap !important;

          :deep(.el-button) {
            padding: 6px 10px !important;
            margin-right: 12px !important;
            flex-shrink: 0 !important;
          }
        }

        .preview-time {
          margin: 0 12px !important;
          font-size: 12px !important;
          white-space: nowrap !important;
          color: #606266 !important;
          flex-shrink: 0 !important;
        }

        :deep(.fullscreen-btn) {
          padding: 6px 10px !important;
          margin-left: auto !important;
          flex-shrink: 0 !important;
        }
      }
    }

    .fullscreen-controls {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
      padding: 20px 20px 10px;
      display: flex;
      flex-direction: column;
      gap: 10px;

      .progress-slider {
        width: 100%;
      }

      .controls-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        flex-wrap: nowrap;

        .left-controls {
          display: flex;
          align-items: center;
          flex-wrap: nowrap;

          :deep(.el-button) {
            padding: 6px 10px;
            margin-right: 12px;
          }
        }

        .time {
          margin: 0 12px;
          color: white;
          font-size: 14px;
          white-space: nowrap;
        }

        :deep(.fullscreen-btn) {
          padding: 6px 10px;
          margin-left: auto;
        }
      }
    }
  }

  .note {
    margin-top: 15px;
    color: #909399;
    font-size: 12px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

<style lang="scss">
.hard-subtitle-modal .el-form-item {
  margin-bottom: 10px;
}

.hard-subtitle-dialog {
  max-height: 90vh;
  
  .el-dialog__body {
    max-height: calc(90vh - 100px);
    overflow-y: auto;
  }
}
</style>
