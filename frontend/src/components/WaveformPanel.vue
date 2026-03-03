<template>
  <div class="waveform-panel">
    <div class="waveform-header">
      <span class="time-info">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
      <span class="file-name">{{ fileInfo }}</span>
    </div>
    <div class="waveform-container">
      <div class="waveform-section">
        <div class="section-label">原视频波形<el-checkbox v-model="showOriginalWaveform" size="small" /></div>
        <div class="waveform-display" ref="displayRef1" @click="handleClick" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @mouseleave="handleMouseUp">
          <canvas ref="canvasRef1" v-if="hasWaveform && showOriginalWaveform"></canvas>
          <div v-else class="placeholder" @click.stop="generateWaveform">
            <el-icon :size="24"><DataLine /></el-icon>
            <span>{{ isLoading ? '生成中...' : '点击生成波形' }}</span>
          </div>
        </div>
      </div>
      <div class="waveform-section">
        <div class="section-label">配音波形<el-checkbox v-model="showDubbingWaveform" size="small" /></div>
        <div class="waveform-display" ref="displayRef2">
          <canvas ref="canvasRef2" v-if="hasDubbingWaveform && showDubbingWaveform"></canvas>
          <div v-else class="placeholder" @click.stop="generateDubbingWaveform">
            <el-icon :size="24"><Headset /></el-icon>
            <span>{{ isDubbingLoading ? '生成中...' : (subtitleStore.dubbingAudioFile ? '点击生成波形' : '暂无配音') }}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="waveform-controls">
      <el-button-group>
        <el-button size="small" @click="zoomIn" title="放大"><el-icon><ZoomIn /></el-icon></el-button>
        <el-button size="small" @click="zoomOut" title="缩小"><el-icon><ZoomOut /></el-icon></el-button>
      </el-button-group>
      <el-button-group>
        <el-button size="small" @click="scrollLeft"><el-icon><DArrowLeft /></el-icon></el-button>
        <el-button size="small" @click="scrollRight"><el-icon><DArrowRight /></el-icon></el-button>
      </el-button-group>
      <el-slider v-model="progressValue" class="waveform-progress" :format-tooltip="formatTime" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { apiService } from '@/services/ApiService'

const subtitleStore = useSubtitleStore()

const displayRef1 = ref(null)
const displayRef2 = ref(null)
const canvasRef1 = ref(null)
const canvasRef2 = ref(null)
const progressValue = ref(0)
const hasWaveform = ref(false)
const hasDubbingWaveform = ref(false)
const isLoading = ref(false)
const isDubbingLoading = ref(false)
const waveform = ref([])
const dubbingWaveform = ref(null)
const duration = ref(0)
const dubbingDuration = ref(0)
const startTime = ref(0)
const currentTime = ref(0)
const zoomFactor = ref(1.0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartTime = ref(0)
const showOriginalWaveform = ref(true)
const showDubbingWaveform = ref(true)

const ZOOM_MIN = 0.5
const ZOOM_MAX = 20.0

const fileInfo = computed(() => {
  if (subtitleStore.videoFile) {
    if (typeof subtitleStore.videoFile === 'string') {
      return subtitleStore.videoFile.split(/[/\\]/).pop()
    }
    return subtitleStore.videoFile.name
  }
  return '未加载视频'
})

const visibleDuration = computed(() => {
  if (!duration.value) return 0
  return duration.value / zoomFactor.value
})

const endTime = computed(() => {
  return Math.min(startTime.value + visibleDuration.value, duration.value)
})

watch(() => subtitleStore.videoFile, (val) => {
  if (!val) {
    hasWaveform.value = false
    waveform.value = []
    duration.value = 0
    currentTime.value = 0
    startTime.value = 0
  }
})

watch(() => subtitleStore.dubbingAudioFile, (val) => {
  if (!val) {
    hasDubbingWaveform.value = false
    dubbingWaveform.value = null
    dubbingDuration.value = 0
  }
})

watch(hasWaveform, async (val) => {
  if (val) {
    await nextTick()
    drawWaveform()
  }
})

watch(hasDubbingWaveform, async (val) => {
  if (val) {
    await nextTick()
    drawDubbingWaveform()
  }
})

watch(zoomFactor, () => {
  if (hasWaveform.value) {
    drawWaveform()
    if (hasDubbingWaveform.value) {
      drawDubbingWaveform()
    }
  }
})

watch(startTime, () => {
  if (hasWaveform.value && !isDragging.value) {
    drawWaveform()
    if (hasDubbingWaveform.value) {
      drawDubbingWaveform()
    }
  }
})

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '00:00.000'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

function handleClick(e) {
  if (!hasWaveform.value && !isLoading.value) {
    generateWaveform()
    return
  }
  
  if (hasWaveform.value && subtitleStore.videoElement) {
    const rect = displayRef1.value.getBoundingClientRect()
    const x = e.clientX - rect.left
    const clickTime = startTime.value + (x / rect.width) * visibleDuration.value
    subtitleStore.videoElement.currentTime = Math.max(0, Math.min(clickTime, duration.value))
  }
}

function handleMouseDown(e) {
  if (hasWaveform.value && e.button === 0) {
    isDragging.value = true
    dragStartX.value = e.clientX
    dragStartTime.value = startTime.value
  }
}

function handleMouseMove(e) {
  if (isDragging.value && hasWaveform.value) {
    const rect = displayRef1.value.getBoundingClientRect()
    const deltaX = e.clientX - dragStartX.value
    const deltaTime = (deltaX / rect.width) * visibleDuration.value
    startTime.value = Math.max(0, Math.min(dragStartTime.value - deltaTime, duration.value - visibleDuration.value))
    drawWaveform()
    if (hasDubbingWaveform.value) {
      drawDubbingWaveform()
    }
  }
}

function handleMouseUp() {
  isDragging.value = false
}

async function generateWaveform() {
  if (!subtitleStore.videoFile) {
    ElMessage.warning('请先打开视频文件')
    return
  }

  isLoading.value = true
  
  try {
    const result = await apiService.generateWaveform(subtitleStore.videoFile, 200)
    
    if (result.error) {
      ElMessage.error('生成波形失败: ' + result.error)
      return
    }
    
    if (result.waveform && result.waveform.data) {
      waveform.value = result.waveform.data
      duration.value = result.waveform.duration
      hasWaveform.value = true
      startTime.value = 0
      ElMessage.success('波形生成成功')
    }
  } catch (error) {
    ElMessage.error('生成波形失败: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

async function generateDubbingWaveform() {
  if (!subtitleStore.dubbingAudioFile) {
    ElMessage.warning('请先导入配音音频')
    return
  }

  isDubbingLoading.value = true
  
  try {
    const result = await apiService.generateWaveform(subtitleStore.dubbingAudioFile, 200)
    
    if (result.error) {
      ElMessage.error('生成配音波形失败: ' + result.error)
      return
    }
    
    if (result.waveform && result.waveform.data) {
      dubbingWaveform.value = result.waveform.data
      dubbingDuration.value = result.waveform.duration
      hasDubbingWaveform.value = true
      ElMessage.success('配音波形生成成功')
      
      await nextTick()
      drawDubbingWaveform()
    }
  } catch (error) {
    ElMessage.error('生成配音波形失败: ' + error.message)
  } finally {
    isDubbingLoading.value = false
  }
}

function drawWaveform() {
  const canvas = canvasRef1.value
  if (!canvas || waveform.value.length === 0 || duration.value <= 0) return
  
  const ctx = canvas.getContext('2d')
  const display = displayRef1.value
  const dpr = window.devicePixelRatio || 1
  
  const width = display.clientWidth
  const height = display.clientHeight
  
  if (width <= 0 || height <= 0) return
  
  canvas.width = width * dpr
  canvas.height = height * dpr
  canvas.style.width = width + 'px'
  canvas.style.height = height + 'px'
  ctx.scale(dpr, dpr)
  
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, width, height)
  
  drawGridLines(ctx, width, height)
  
  const centerY = height / 2
  const samplesPerPixel = waveform.value.length / duration.value
  const startSample = Math.floor(startTime.value * samplesPerPixel)
  const endSample = Math.ceil(endTime.value * samplesPerPixel)
  const samplesVisible = Math.max(1, endSample - startSample)
  
  ctx.strokeStyle = '#4a9eff'
  ctx.lineWidth = 1
  ctx.beginPath()
  
  for (let x = 0; x < width; x++) {
    const sampleIndex = startSample + Math.floor((x / width) * samplesVisible)
    if (sampleIndex >= 0 && sampleIndex < waveform.value.length) {
      const amplitude = waveform.value[sampleIndex]
      const halfHeight = amplitude * height * 0.4
      
      ctx.moveTo(x, centerY - halfHeight)
      ctx.lineTo(x, centerY + halfHeight)
    }
  }
  ctx.stroke()
  
  ctx.strokeStyle = '#333'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()
  
  drawSubtitles(ctx, width, height)
  
  if (duration.value > 0 && currentTime.value > 0) {
    const playheadX = ((currentTime.value - startTime.value) / visibleDuration.value) * width
    if (playheadX >= 0 && playheadX <= width) {
      ctx.strokeStyle = '#f56c6c'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(playheadX, 0)
      ctx.lineTo(playheadX, height)
      ctx.stroke()
      ctx.lineWidth = 1
    }
  }
}

function drawDubbingWaveform() {
  const canvas = canvasRef2.value
  if (!canvas || !dubbingWaveform.value || dubbingDuration.value <= 0) return
  
  const ctx = canvas.getContext('2d')
  const display = displayRef2.value
  const dpr = window.devicePixelRatio || 1
  
  const width = display.clientWidth
  const height = display.clientHeight
  
  if (width <= 0 || height <= 0) return
  
  canvas.width = width * dpr
  canvas.height = height * dpr
  canvas.style.width = width + 'px'
  canvas.style.height = height + 'px'
  ctx.scale(dpr, dpr)
  
  ctx.fillStyle = '#1a2e1a'
  ctx.fillRect(0, 0, width, height)
  
  drawGridLines(ctx, width, height, '#2a4a2a')
  
  const centerY = height / 2
  const dubbingVisibleDuration = dubbingDuration.value / zoomFactor.value
  const samplesPerPixel = dubbingWaveform.value.length / dubbingDuration.value
  const startSample = Math.floor(startTime.value * samplesPerPixel)
  const endSample = Math.ceil((startTime.value + dubbingVisibleDuration) * samplesPerPixel)
  const samplesVisible = Math.max(1, endSample - startSample)
  
  ctx.strokeStyle = '#4aff9e'
  ctx.lineWidth = 1
  ctx.beginPath()
  
  for (let x = 0; x < width; x++) {
    const sampleIndex = startSample + Math.floor((x / width) * samplesVisible)
    if (sampleIndex >= 0 && sampleIndex < dubbingWaveform.value.length) {
      const amplitude = dubbingWaveform.value[sampleIndex]
      const halfHeight = amplitude * height * 0.4
      
      ctx.moveTo(x, centerY - halfHeight)
      ctx.lineTo(x, centerY + halfHeight)
    }
  }
  ctx.stroke()
  
  ctx.strokeStyle = '#335'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()
  
  if (dubbingDuration.value > 0 && currentTime.value > 0) {
    const dubbingVisibleDuration = dubbingDuration.value / zoomFactor.value
    const playheadX = ((currentTime.value - startTime.value) / dubbingVisibleDuration) * width
    if (playheadX >= 0 && playheadX <= width) {
      ctx.strokeStyle = '#f56c6c'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(playheadX, 0)
      ctx.lineTo(playheadX, height)
      ctx.stroke()
      ctx.lineWidth = 1
    }
  }
}

function drawGridLines(ctx, width, height, color = '#2a2a4a') {
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  
  const gridSpacingSeconds = getGridSpacing()
  const startGrid = Math.floor(startTime.value / gridSpacingSeconds) * gridSpacingSeconds
  
  for (let t = startGrid; t <= endTime.value; t += gridSpacingSeconds) {
    const x = ((t - startTime.value) / visibleDuration.value) * width
    if (x >= 0 && x <= width) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
      ctx.stroke()
    }
  }
  
  ctx.strokeStyle = color + '44'
  ctx.beginPath()
  ctx.moveTo(0, height / 4)
  ctx.lineTo(width, height / 4)
  ctx.moveTo(0, height * 3 / 4)
  ctx.lineTo(width, height * 3 / 4)
  ctx.stroke()
}

function getGridSpacing() {
  const visible = visibleDuration.value
  if (visible < 5) return 0.5
  if (visible < 15) return 1
  if (visible < 30) return 2
  if (visible < 60) return 5
  if (visible < 120) return 10
  if (visible < 300) return 30
  return 60
}

function drawSubtitles(ctx, width, height) {
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  if (!paragraphs || paragraphs.length === 0) return
  
  ctx.fillStyle = 'rgba(64, 158, 255, 0.3)'
  ctx.strokeStyle = 'rgba(64, 158, 255, 0.8)'
  ctx.lineWidth = 1
  
  paragraphs.forEach((p, index) => {
    const startSec = p.startTime.totalMilliseconds / 1000
    const endSec = p.endTime.totalMilliseconds / 1000
    
    if (endSec >= startTime.value && startSec <= endTime.value) {
      const x1 = ((startSec - startTime.value) / visibleDuration.value) * width
      const x2 = ((endSec - startTime.value) / visibleDuration.value) * width
      const rectWidth = Math.max(2, x2 - x1)
      
      const y = height - 20
      
      if (index === subtitleStore.selectedParagraphIndex) {
        ctx.fillStyle = 'rgba(245, 108, 108, 0.4)'
        ctx.strokeStyle = 'rgba(245, 108, 108, 0.8)'
      } else {
        ctx.fillStyle = 'rgba(64, 158, 255, 0.3)'
        ctx.strokeStyle = 'rgba(64, 158, 255, 0.8)'
      }
      
      ctx.fillRect(x1, y, rectWidth, 15)
      ctx.strokeRect(x1, y, rectWidth, 15)
    }
  })
}

function zoomIn() {
  zoomFactor.value = Math.min(ZOOM_MAX, zoomFactor.value * 1.5)
}

function zoomOut() {
  zoomFactor.value = Math.max(ZOOM_MIN, zoomFactor.value / 1.5)
}

function scrollLeft() {
  const scrollAmount = visibleDuration.value * 0.2
  startTime.value = Math.max(0, startTime.value - scrollAmount)
}

function scrollRight() {
  const scrollAmount = visibleDuration.value * 0.2
  startTime.value = Math.min(duration.value - visibleDuration.value, startTime.value + scrollAmount)
}

function handleVideoTimeUpdate() {
  const video = subtitleStore.videoElement
  if (video && hasWaveform.value) {
    currentTime.value = video.currentTime
    progressValue.value = (video.currentTime / duration.value) * 100
    
    const centerOffset = visibleDuration.value / 2
    const newStartTime = video.currentTime - centerOffset
    
    if (Math.abs(newStartTime - startTime.value) > visibleDuration.value * 0.1) {
      startTime.value = Math.max(0, Math.min(newStartTime, duration.value - visibleDuration.value))
    }
    
    drawWaveform()
    if (hasDubbingWaveform.value) {
      drawDubbingWaveform()
    }
  }
}

function handleVideoPlay() {}

function handleVideoPause() {}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  
  const video = subtitleStore.videoElement
  if (video) {
    video.addEventListener('timeupdate', handleVideoTimeUpdate)
    video.addEventListener('play', handleVideoPlay)
    video.addEventListener('pause', handleVideoPause)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  const video = subtitleStore.videoElement
  if (video) {
    video.removeEventListener('timeupdate', handleVideoTimeUpdate)
    video.removeEventListener('play', handleVideoPlay)
    video.removeEventListener('pause', handleVideoPause)
  }
})

function handleResize() {
  if (hasWaveform.value) {
    drawWaveform()
    if (hasDubbingWaveform.value) {
      drawDubbingWaveform()
    }
  }
}

watch(() => subtitleStore.videoElement, (video, oldVideo) => {
  if (oldVideo) {
    oldVideo.removeEventListener('timeupdate', handleVideoTimeUpdate)
    oldVideo.removeEventListener('play', handleVideoPlay)
    oldVideo.removeEventListener('pause', handleVideoPause)
  }
  if (video) {
    video.addEventListener('timeupdate', handleVideoTimeUpdate)
    video.addEventListener('play', handleVideoPlay)
    video.addEventListener('pause', handleVideoPause)
  }
})

watch(() => subtitleStore.selectedParagraphIndex, () => {
  if (hasWaveform.value) {
    drawWaveform()
  }
})
</script>

<style lang="scss" scoped>
.waveform-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

  .waveform-header {
    padding: 4px 8px;
    background-color: $bg-color;
    border-bottom: 1px solid $border-color;
    font-size: $font-size-base;
    color: $text-muted;
    display: flex;
    justify-content: space-between;
    
    .time-info {
      font-family: monospace;
      color: #409eff;
    }
    
    .file-name {
      color: $text-muted;
    }
  }

  .waveform-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    
    .waveform-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
      border-bottom: 1px solid $border-color;
      
      &:last-child {
        border-bottom: none;
      }
      
      .section-label {
        padding: 2px 8px;
        font-size: 11px;
        color: $text-muted;
        background-color: rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
        
        .el-checkbox {
          margin-left: auto;
          margin-top: 0;
          margin-bottom: 0;
          height: 14px;
          line-height: 14px;
        }
      }
      
      .waveform-display {
        flex: 1;
        background-color: #1a1a2e;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 0;
        cursor: pointer;
        user-select: none;

        canvas {
          width: 100%;
          height: 100%;
        }

        .placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          color: #666;
          cursor: pointer;
          font-size: 12px;
          
          &:hover {
            color: #409eff;
          }
        }
      }
    }
  }

  .waveform-controls {
    padding: 4px 8px;
    background-color: $bg-color;
    border-top: 1px solid $border-color;
    display: flex;
    align-items: center;
    gap: 8px;

    .waveform-progress {
      flex: 1;
    }
  }
}
</style>
