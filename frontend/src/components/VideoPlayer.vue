<template>
  <div class="video-player" ref="containerRef" @click="handleContainerClick">
    <video
      v-if="videoUrl"
      ref="videoRef"
      :src="videoUrl"
      @timeupdate="handleTimeUpdate"
      @loadedmetadata="handleLoadedMetadata"
      @ended="handleEnded"
    ></video>
    <div v-else class="placeholder">
      <el-icon :size="48"><VideoCamera /></el-icon>
      <span>视频预览区域</span>
    </div>
    <div v-if="videoUrl && isFullscreen" class="fullscreen-controls" @click.stop>
      <el-slider
        v-model="progressValue"
        :max="100"
        :show-tooltip="false"
        @input="handleProgressChange"
        class="progress-slider"
      />
      <div class="controls-bar">
        <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" @click="togglePlay" />
        <el-button icon="RefreshLeft" @click="reset" />
        <span class="time">{{ currentTimeDisplay }} / {{ durationDisplay }}</span>
        <el-button icon="FullScreen" @click="toggleFullscreen" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { getBackendBaseUrl } from '@/utils/runtime'

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

const currentTimeDisplay = computed(() => formatTime(currentTime.value))
const durationDisplay = computed(() => formatTime(duration.value))

function formatTime(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

watch(videoFile, (newFile) => {
  if (newFile) {
    if (typeof newFile === 'string') {
      const encodedPath = encodeURIComponent(newFile)
      videoUrl.value = `${getBackendBaseUrl()}/api/video/serve?path=${encodedPath}`
    } else {
      videoUrl.value = URL.createObjectURL(newFile)
    }
  } else {
    if (videoUrl.value && typeof videoFile.value !== 'string') {
      URL.revokeObjectURL(videoUrl.value)
    }
    videoUrl.value = ''
  }
})

function handleFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function handleKeyDown(event) {
  if (!videoRef.value) return
  
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
  background-color: #1a1a1a;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  cursor: pointer;
  position: relative;
  border-radius: 4px;
  overflow: hidden;

  video {
    max-width: 100%;
    max-height: 100%;
    display: block;
    object-fit: contain;
  }
  
  &:fullscreen {
    width: 100vw;
    height: 100vh;
    
    video {
      height: 100%;
    }
  }

  .placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    color: #666;
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

      .el-button {
        padding: 6px 10px;
      }

      .time {
        margin-left: auto;
        color: white;
        font-size: 14px;
        white-space: nowrap;
      }
    }
  }
}
</style>
