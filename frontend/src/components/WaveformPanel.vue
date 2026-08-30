<template>
  <div class="waveform-panel">
    <div class="waveform-header">
      <span class="time-info">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
      <span class="file-name">{{ fileInfo }}</span>
    </div>
    <div class="waveform-container">
      <div class="waveform-section">
        <div class="section-label">原视频波形<el-checkbox v-model="showOriginalWaveform" size="small" /></div>
        <div class="waveform-display" ref="displayRef1" @click="handleClick" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @mouseleave="handleMouseUp" @wheel.prevent="handleWheelZoom">
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
        <el-button size="small" @click="scrollLeft" title="左移"><el-icon><ArrowLeft /></el-icon></el-button>
        <el-button size="small" @click="scrollRight" title="右移"><el-icon><ArrowRight /></el-icon></el-button>
      </el-button-group>
      <span class="zoom-label mono">{{ zoomFactor.toFixed(1) }}x</span>
      <el-slider v-model="progressValue" class="waveform-progress" :format-tooltip="formatTime" :disabled="isSliderDisabled" />
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

// ============================================================
// #2 rAF 节流:合并同一事件循环内的多次重绘请求
// ============================================================
let drawPending1 = false
let drawPending2 = false
let rafId = 0

function scheduleDraw(which = 'both') {
  if (which === 'original' || which === 'both') drawPending1 = true
  if (which === 'dubbing' || which === 'both') drawPending2 = true
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = 0
    const p1 = drawPending1; drawPending1 = false
    const p2 = drawPending2; drawPending2 = false
    if (p1) drawWaveform()
    if (p2) drawDubbingWaveform()
  })
}

const ZOOM_MIN = 0.5
const ZOOM_MAX = 20.0

const hasAnyWaveform = computed(() => hasWaveform.value || hasDubbingWaveform.value)
const isSliderDisabled = computed(() => !hasAnyWaveform.value)

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

// watch 仅在引用变化时触发:无论是清空还是切换文件,都必须重置波形状态,
// 否则残留上一个视频的时长/波形数据,播放头与字幕块定位全部按错误时长映射
watch(() => subtitleStore.videoFile, () => {
  hasWaveform.value = false
  waveform.value = []
  duration.value = 0
  currentTime.value = 0
  startTime.value = 0
})

watch(() => subtitleStore.dubbingAudioFile, () => {
  hasDubbingWaveform.value = false
  dubbingWaveform.value = null
  dubbingDuration.value = 0
})

watch(hasWaveform, async (val) => {
  if (val) {
    await nextTick()
    scheduleDraw('original')
  }
})

watch(hasDubbingWaveform, async (val) => {
  if (val) {
    await nextTick()
    scheduleDraw('dubbing')
  }
})

watch(zoomFactor, () => {
  if (hasWaveform.value) scheduleDraw('both')
})

watch(startTime, () => {
  if (hasWaveform.value && !isDragging.value) scheduleDraw('both')
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

  if (hasWaveform.value && subtitleStore.videoElement && !hitTestSubtitle(e)) {
    const rect = displayRef1.value.getBoundingClientRect()
    const x = e.clientX - rect.left
    const clickTime = startTime.value + (x / rect.width) * visibleDuration.value
    subtitleStore.videoElement.currentTime = Math.max(0, Math.min(clickTime, duration.value))
  }
}

// ============================================================
// 字幕块直接操纵:拖左/右边缘改起止时间,拖中间整体平移
// ============================================================
const EDGE_TOLERANCE_PX = 6   // 边缘命中容差
const SNAP_MS = 150           // 邻近边界吸附阈值
const SUB_ZONE_TOP = 24       // 字幕带距底部像素(与 drawSubtitles 保持一致)
const SUB_ZONE_BOTTOM = 4
let subDrag = null            // { mode: 'start'|'end'|'move', index, grabMs, origStart, origEnd }

function timeAtX(x, rect) {
  return startTime.value + (x / rect.width) * visibleDuration.value
}

// 命中检测:返回 {mode, index, grabMs} 或 null
function hitTestSubtitle(e) {
  if (!displayRef1.value) return null
  const rect = displayRef1.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const zoneTop = rect.height - SUB_ZONE_TOP
  const zoneBottom = rect.height - SUB_ZONE_BOTTOM
  if (y < zoneTop || y > zoneBottom) return null

  const ps = subtitleStore.currentSubtitle.paragraphs
  for (let i = 0; i < ps.length; i++) {
    const s = ps[i].startTime.totalMilliseconds / 1000
    const en = ps[i].endTime.totalMilliseconds / 1000
    if (en < startTime.value || s > endTime.value) continue
    const x1 = ((s - startTime.value) / visibleDuration.value) * rect.width
    const x2 = ((en - startTime.value) / visibleDuration.value) * rect.width
    if (x >= x1 - EDGE_TOLERANCE_PX && x <= x2 + EDGE_TOLERANCE_PX) {
      if (x < x1 + EDGE_TOLERANCE_PX) return { mode: 'start', index: i }
      if (x > x2 - EDGE_TOLERANCE_PX) return { mode: 'end', index: i }
      return { mode: 'move', index: i, grabMs: timeAtX(x, rect) * 1000 }
    }
  }
  return null
}

// 吸附:靠近相邻字幕边界时贴齐
function snapTime(ms, index) {
  const ps = subtitleStore.currentSubtitle.paragraphs
  const candidates = []
  if (index > 0) candidates.push(ps[index - 1].endTime.totalMilliseconds)
  if (index < ps.length - 1) candidates.push(ps[index + 1].startTime.totalMilliseconds)
  for (const c of candidates) {
    if (Math.abs(ms - c) < SNAP_MS) return c
  }
  return ms
}

function handleMouseDown(e) {
  if (!hasWaveform.value || e.button !== 0) return

  const hit = hitTestSubtitle(e)
  if (hit) {
    const p = subtitleStore.currentSubtitle.paragraphs[hit.index]
    if (!p) return
    subDrag = {
      ...hit,
      origStart: p.startTime.totalMilliseconds,
      origEnd: p.endTime.totalMilliseconds
    }
    subtitleStore.selectParagraph(hit.index)
    subtitleStore.saveTimeEditHistory() // 拖拽全程只入栈一次
    displayRef1.value.style.cursor = hit.mode === 'move' ? 'grabbing' : 'col-resize'
    e.preventDefault()
    return
  }

  // 空白处:平移视图
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartTime.value = startTime.value
  displayRef1.value.style.cursor = 'grabbing'
}

function handleMouseMove(e) {
  // 字幕块拖拽中
  if (subDrag) {
    applySubDrag(e)
    return
  }

  // 视图平移中
  if (isDragging.value && hasWaveform.value) {
    const rect = displayRef1.value.getBoundingClientRect()
    const deltaX = e.clientX - dragStartX.value
    const deltaTime = (deltaX / rect.width) * visibleDuration.value
    startTime.value = Math.max(0, Math.min(dragStartTime.value - deltaTime, duration.value - visibleDuration.value))
    scheduleDraw('both')
    return
  }

  // 悬停光标反馈:边缘 col-resize / 块内 grab / 空白 default
  if (hasWaveform.value && displayRef1.value) {
    const hit = hitTestSubtitle(e)
    displayRef1.value.style.cursor = hit ? (hit.mode === 'move' ? 'grab' : 'col-resize') : 'default'
  }
}

function applySubDrag(e) {
  const rect = displayRef1.value.getBoundingClientRect()
  const t = timeAtX(e.clientX - rect.left, rect) * 1000
  const durMs = subDrag.origEnd - subDrag.origStart
  const maxMs = duration.value * 1000
  let s = subDrag.origStart
  let en = subDrag.origEnd

  if (subDrag.mode === 'start') {
    s = Math.max(0, Math.min(t, subDrag.origEnd - 100))
    s = Math.min(snapTime(s, subDrag.index), subDrag.origEnd - 100)
  } else if (subDrag.mode === 'end') {
    en = Math.max(subDrag.origStart + 100, Math.min(t, maxMs))
    en = Math.max(snapTime(en, subDrag.index), subDrag.origStart + 100)
  } else {
    let ns = Math.max(0, Math.min(t - subDrag.grabMs + subDrag.origStart, maxMs - durMs))
    ns = snapTime(ns, subDrag.index)
    s = Math.max(0, ns)
    en = s + durMs
  }

  subtitleStore.updateParagraphTime(subDrag.index, s, en, true)

  // 拖边缘时视频实时跳帧预览
  if (subDrag.mode !== 'move' && subtitleStore.videoElement) {
    const preview = (subDrag.mode === 'start' ? s : en) / 1000
    try { subtitleStore.videoElement.currentTime = Math.max(0, Math.min(preview, duration.value)) } catch { /* 拖拽过快时忽略 seek 异常 */ }
  }

  scheduleDraw('original')
}

function handleMouseUp() {
  if (subDrag) {
    subDrag = null
    if (displayRef1.value) displayRef1.value.style.cursor = 'default'
    return
  }
  isDragging.value = false
  if (displayRef1.value && !isDragging.value) {
    displayRef1.value.style.cursor = 'default'
  }
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
      scheduleDraw('dubbing')
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

  // 字幕带几何:与 hitTestSubtitle 的 SUB_ZONE_TOP/SUB_ZONE_BOTTOM 对齐
  const bandH = SUB_ZONE_TOP - SUB_ZONE_BOTTOM
  const y = height - SUB_ZONE_TOP
  const dragIndex = subDrag?.index

  paragraphs.forEach((p, index) => {
    const startSec = p.startTime.totalMilliseconds / 1000
    const endSec = p.endTime.totalMilliseconds / 1000

    if (endSec >= startTime.value && startSec <= endTime.value) {
      const x1 = ((startSec - startTime.value) / visibleDuration.value) * width
      const x2 = ((endSec - startTime.value) / visibleDuration.value) * width
      const rectWidth = Math.max(2, x2 - x1)
      const isDragging = dragIndex === index
      const isSelected = index === subtitleStore.selectedParagraphIndex

      if (isDragging) {
        // 拖拽中:实色高亮
        ctx.fillStyle = 'rgba(13, 148, 136, 0.85)'
        ctx.strokeStyle = '#0d9488'
      } else if (isSelected) {
        ctx.fillStyle = 'rgba(245, 108, 108, 0.55)'
        ctx.strokeStyle = 'rgba(245, 108, 108, 0.95)'
      } else {
        ctx.fillStyle = 'rgba(13, 148, 136, 0.3)'
        ctx.strokeStyle = 'rgba(13, 148, 136, 0.85)'
      }
      ctx.lineWidth = 1
      ctx.fillRect(x1, y, rectWidth, bandH)
      ctx.strokeRect(x1 + 0.5, y + 0.5, rectWidth - 1, bandH - 1)

      // 拖拽把手:选中/拖拽块的两端画竖向抓取线
      if (isDragging || isSelected) {
        ctx.strokeStyle = isDragging ? '#ffffff' : 'rgba(255, 255, 255, 0.75)'
        ctx.lineWidth = 1.5
        const gripInset = 3
        for (const gx of [x1 + gripInset, x2 - gripInset]) {
          if (gx > x1 && gx < x2) {
            ctx.beginPath()
            ctx.moveTo(gx, y + 3)
            ctx.lineTo(gx, y + bandH - 3)
            ctx.stroke()
          }
        }
        ctx.lineWidth = 1
      }
    }
  })
}

function zoomIn() {
  zoomFactor.value = Math.min(ZOOM_MAX, zoomFactor.value * 1.5)
}

// 滚轮缩放:以鼠标位置为锚点,缩放后保持锚点时间不变
function handleWheelZoom(e) {
  if (!hasWaveform.value || !displayRef1.value || duration.value <= 0) return
  const rect = displayRef1.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const anchorTime = startTime.value + (x / rect.width) * visibleDuration.value

  const factor = e.deltaY < 0 ? 1.2 : 1 / 1.2
  const newZoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoomFactor.value * factor))
  if (newZoom === zoomFactor.value) return
  const newVisible = duration.value / newZoom

  let newStart = anchorTime - (x / rect.width) * newVisible
  newStart = Math.max(0, Math.min(newStart, Math.max(0, duration.value - newVisible)))

  zoomFactor.value = newZoom
  startTime.value = newStart
  scheduleDraw('both')
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
    
    scheduleDraw('both')
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
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  drawPending1 = drawPending2 = false
  
  const video = subtitleStore.videoElement
  if (video) {
    video.removeEventListener('timeupdate', handleVideoTimeUpdate)
    video.removeEventListener('play', handleVideoPlay)
    video.removeEventListener('pause', handleVideoPause)
  }
})

function handleResize() {
  if (hasWaveform.value || hasDubbingWaveform.value) scheduleDraw('both')
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
  if (hasWaveform.value) scheduleDraw('original')
})

// 时间码被外部修改(键盘微调/行内编辑)时同步重绘
watch(
  () => subtitleStore.currentSubtitle.paragraphs,
  () => {
    if (hasWaveform.value && !subDrag) scheduleDraw('original')
  },
  { deep: true }
)
</script>

<style lang="scss" scoped>
.waveform-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

  .waveform-header {
    padding: 0 12px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--app-surface-muted);
    border-bottom: 1px solid var(--app-border);
    font-size: $font-size-sm;
    color: var(--app-text-muted);

    .time-info {
      font-family: $font-family-mono;
      font-variant-numeric: tabular-nums;
      color: var(--app-primary);
    }

    .file-name {
      color: var(--app-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
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
      border-bottom: 1px solid var(--app-border);

      &:last-child {
        border-bottom: none;
      }

      .section-label {
        padding: 2px 12px;
        font-size: 11px;
        font-weight: 600;
        color: var(--app-text-muted);
        background: var(--app-surface-muted);
        border-bottom: 1px solid var(--app-border);
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
        background: var(--app-media-bg);
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
          color: var(--app-media-text);
          cursor: pointer;
          font-size: 12px;
          transition: color $transition-base;

          &:hover {
            color: var(--app-primary);
          }
        }
      }
    }
  }

  .waveform-controls {
    padding: 6px 12px;
    background: var(--app-surface-muted);
    border-top: 1px solid var(--app-border);
    display: flex;
    align-items: center;
    gap: 8px;

    .zoom-label {
      min-width: 42px;
      font-family: $font-family-mono;
      font-size: $font-size-sm;
      color: var(--app-text-secondary);
      text-align: center;
      font-variant-numeric: tabular-nums;
    }

    .waveform-progress {
      flex: 1;
    }
  }
}
</style>
