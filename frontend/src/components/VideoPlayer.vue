<template>
  <div class="video-player" ref="containerRef" @click="handleContainerClick">
    <video
      v-if="videoUrl"
      ref="videoRef"
      :src="videoUrl"
      crossorigin="anonymous"
      @timeupdate="handleTimeUpdate"
      @seeked="handleTimeUpdate"
      @loadedmetadata="handleLoadedMetadata"
      @ended="handleEnded"
    ></video>
    <div v-else class="placeholder">
      <el-icon :size="48"><VideoCamera /></el-icon>
      <span>视频预览区域</span>
    </div>

    <!-- 字幕实时叠加预览:所见即所得 -->
    <div v-if="videoUrl" class="subtitle-overlay" :class="{ visible: overlayVisible }" aria-hidden="true">
      <div v-if="overlayText" class="overlay-line">{{ overlayText }}</div>
      <div v-if="overlayTranslation" class="overlay-line translation">{{ overlayTranslation }}</div>
    </div>
    <button
      v-if="videoUrl"
      type="button"
      class="overlay-toggle"
      :class="{ active: overlayVisible }"
      :title="overlayVisible ? '隐藏字幕预览' : '显示字幕预览'"
      :aria-label="overlayVisible ? '隐藏字幕预览' : '显示字幕预览'"
      @click.stop="overlayVisible = !overlayVisible"
    >
      <el-icon :size="14"><View /></el-icon>
    </button>
    <div v-if="videoUrl && isFullscreen" class="fullscreen-controls" @click.stop>
      <el-slider
        v-model="progressValue"
        :max="100"
        :show-tooltip="false"
        @input="handleProgressChange"
        class="progress-slider"
      />
      <div class="controls-bar">
        <el-button
          :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
          :aria-label="isPlaying ? '暂停' : '播放'"
          @click="togglePlay"
        />
        <el-button icon="RefreshLeft" aria-label="回到开头" @click="reset" />
        <span class="time">{{ currentTimeDisplay }} / {{ durationDisplay }}</span>
        <el-button icon="FullScreen" aria-label="退出全屏" @click="toggleFullscreen" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { resolveMediaUrl } from '@/utils/runtime'

const subtitleStore = useSubtitleStore()

const containerRef = ref(null)
const videoRef = ref(null)
const videoUrl = ref('')
const isFullscreen = ref(false)
const isPlaying = ref(false)
const progressValue = ref(0)
const currentTime = ref(0)
const duration = ref(0)

const videoFile = computed(() => subtitleStore.videoFile)

// ============================================================
// 字幕实时叠加预览:按播放时间查找当前字幕
// ============================================================
const overlayVisible = ref(true)
const overlayText = ref('')
const overlayTranslation = ref('')

function updateOverlay(currentTimeMs) {
  const ps = subtitleStore.currentSubtitle.paragraphs
  for (const p of ps) {
    if (currentTimeMs >= p.startTime.totalMilliseconds && currentTimeMs <= p.endTime.totalMilliseconds) {
      overlayText.value = p.text || ''
      overlayTranslation.value = (subtitleStore.showTranslation && p.translation) ? p.translation : ''
      return
    }
  }
  overlayText.value = ''
  overlayTranslation.value = ''
}

// 字幕内容变化(加载/编辑/翻译切换)后立即刷新叠加预览
watch(() => [subtitleStore.currentSubtitle, subtitleStore.showTranslation], () => {
  if (videoRef.value) {
    updateOverlay(videoRef.value.currentTime * 1000)
  }
})

const currentTimeDisplay = computed(() => formatTime(currentTime.value))
const durationDisplay = computed(() => formatTime(duration.value))

function formatTime(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

watch(videoFile, async (newFile) => {
  if (newFile) {
    if (typeof newFile === 'string') {
      // Electron 走 media:// 自定义协议直读本地磁盘,根除 CORS 导致的 Web Audio 静音
      // 浏览器端回退为后端 HTTP 转发
      videoUrl.value = await resolveMediaUrl(newFile)
      // URL 切换后下一帧 video 元素已重建,把 store 的引用也刷新,避免 VideoControls 拿旧元素
      await nextTick()
      if (videoRef.value) subtitleStore.setVideoElement(videoRef.value)
    } else {
      videoUrl.value = URL.createObjectURL(newFile)
    }
  } else {
    if (videoUrl.value && typeof videoFile.value !== 'string') {
      URL.revokeObjectURL(videoUrl.value)
    }
    videoUrl.value = ''
    // v-if 即将销毁 video 元素,同步清空 store,避免其他组件拿到已销毁的元素
    subtitleStore.setVideoElement(null)
  }
})

function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function handleKeyDown(event) {
  if (!videoRef.value) return

  // 焦点在输入类控件时不劫持方向键,避免编辑字幕文本时触发视频跳转
  const target = event.target
  if (target instanceof HTMLElement &&
      (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) {
    return
  }

  if (event.key === 'ArrowLeft') {
    videoRef.value.currentTime = Math.max(0, videoRef.value.currentTime - 5)
  } else if (event.key === 'ArrowRight') {
    videoRef.value.currentTime = Math.min(duration.value, videoRef.value.currentTime + 5)
  }
}

onMounted(() => {
  if (videoRef.value) {
    subtitleStore.setVideoElement(videoRef.value)
  }
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  if (videoUrl.value) {
    URL.revokeObjectURL(videoUrl.value)
  }
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('keydown', handleKeyDown)
})

function handleContainerClick(event) {
  if (event.target.closest('.fullscreen-controls')) return
  
  if (!videoUrl.value) {
    document.querySelector('input[type="file"][accept="video/*"]')?.click()
  } else if (videoRef.value) {
    togglePlay()
  }
}

function handleTimeUpdate() {
  if (videoRef.value) {
    const currentTimeMs = videoRef.value.currentTime * 1000
    updateOverlay(currentTimeMs)
    syncSubtitle(currentTimeMs)
    currentTime.value = videoRef.value.currentTime
    if (duration.value > 0) {
      progressValue.value = (videoRef.value.currentTime / duration.value) * 100
    }
    emit('timeupdate', {
      currentTime: videoRef.value.currentTime,
      duration: videoRef.value.duration
    })
  }
}

function handleLoadedMetadata() {
  if (videoRef.value) {
    subtitleStore.setVideoElement(videoRef.value)
    duration.value = videoRef.value.duration
    emit('loaded', {
      duration: videoRef.value.duration
    })
  }
}

function handleEnded() {
  isPlaying.value = false
  emit('ended')
}

function handleProgressChange(value) {
  if (videoRef.value && duration.value > 0) {
    videoRef.value.currentTime = (value / 100) * duration.value
  }
}

function syncSubtitle(currentTimeMs) {
  for (let i = 0; i < subtitleStore.currentSubtitle.paragraphs.length; i++) {
    const p = subtitleStore.currentSubtitle.paragraphs[i]
    if (currentTimeMs >= p.startTime.totalMilliseconds &&
        currentTimeMs <= p.endTime.totalMilliseconds) {
      if (subtitleStore.selectedParagraphIndex !== i) {
        subtitleStore.selectParagraph(i)
      }
      break
    }
  }
}

const emit = defineEmits(['timeupdate', 'loaded', 'ended'])

function play() {
  videoRef.value?.play()
  isPlaying.value = true
}

function pause() {
  videoRef.value?.pause()
  isPlaying.value = false
}

function togglePlay() {
  if (videoRef.value) {
    if (videoRef.value.paused) {
      videoRef.value.play()
      isPlaying.value = true
      return true
    } else {
      videoRef.value.pause()
      isPlaying.value = false
      return false
    }
  }
  return false
}

function seek(time) {
  if (videoRef.value) {
    videoRef.value.currentTime = time
  }
}

function setVolume(volume) {
  if (videoRef.value) {
    videoRef.value.volume = Math.min(1, Math.max(0, volume / 100))
  }
}

function toggleFullscreen() {
  if (containerRef.value) {
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      containerRef.value.requestFullscreen()
    }
  }
}

function reset() {
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.currentTime = 0
    isPlaying.value = false
  }
}

defineExpose({
  play,
  pause,
  togglePlay,
  seek,
  setVolume,
  toggleFullscreen,
  reset,
  videoRef
})
</script>

<style lang="scss" scoped>
.video-player {
  background: var(--app-media-bg);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-sm);
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  cursor: pointer;
  position: relative;
  overflow: hidden;

  video {
    max-width: 100%;
    max-height: 100%;
    display: block;
    object-fit: contain;
  }

  // 字幕实时叠加预览
  .subtitle-overlay {
    position: absolute;
    left: 50%;
    bottom: 6%;
    transform: translateX(-50%);
    max-width: 86%;
    text-align: center;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s ease;
    z-index: 2;

    &.visible {
      opacity: 1;
    }

    .overlay-line {
      display: block;
      padding: 2px 10px;
      font-size: 20px;
      line-height: 1.4;
      color: #fff;
      text-shadow: 0 0 4px rgba(0, 0, 0, 0.9), 0 1px 3px rgba(0, 0, 0, 0.9), 0 -1px 3px rgba(0, 0, 0, 0.9);
      white-space: pre-wrap;
      word-break: break-word;

      &.translation {
        font-size: 16px;
        color: #ffe9a8;
        margin-top: 2px;
      }
    }
  }

  .overlay-toggle {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: $border-radius-sm;
    background: rgba(8, 13, 20, 0.55);
    color: rgba(255, 255, 255, 0.75);
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s ease, background-color 0.2s ease, color 0.2s ease;
    z-index: 3;

    &.active {
      color: #fff;
    }

    &:hover {
      background: rgba(8, 13, 20, 0.8);
      color: #fff;
    }
  }

  &:hover .overlay-toggle {
    opacity: 1;
  }

  &:fullscreen {
    width: 100vw;
    height: 100vh;
    border-radius: 0;

    video {
      height: 100%;
    }
  }

  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    color: var(--app-media-text);
    transition: color $transition-base;

    &:hover {
      color: var(--app-primary);
    }
  }

  .fullscreen-controls {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(8, 13, 20, 0.82);
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    padding: 16px 20px 10px;
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

      .el-button {
        padding: 6px 10px;
      }

      .time {
        margin-left: auto;
        color: #e6edec;
        font-family: $font-family-mono;
        font-size: 14px;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
      }
    }
  }
}
</style>
