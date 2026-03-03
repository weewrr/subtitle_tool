<template>
  <div class="video-controls">
    <el-slider
      v-model="progressValue"
      :max="100"
      :disabled="!hasVideo"
      :show-tooltip="false"
      @input="handleProgressChange"
    />
    <div class="video-buttons">
      <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" @click="togglePlay" :disabled="!hasVideo" />
      <el-button icon="RefreshLeft" @click="reset" :disabled="!hasVideo" />
      <el-button :icon="isMuted ? 'Mute' : 'Microphone'" @click="toggleMute" :disabled="!hasVideo" />
      <el-slider
        v-model="volumeDb"
        :min="-20"
        :max="20"
        :disabled="!hasVideo || isMuted"
        :show-tooltip="false"
        class="volume-slider"
        @input="handleVolumeChange"
      />
      <span class="time">{{ currentTimeDisplay }} / {{ durationDisplay }}</span>
      <el-button icon="FullScreen" @click="toggleFullscreen" :disabled="!hasVideo" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'

const subtitleStore = useSubtitleStore()

const isPlaying = ref(false)
const isMuted = ref(false)
const volumeDb = ref(0)
const progressValue = ref(0)
const currentTime = ref(0)
const duration = ref(0)

let audioContext = null
let gainNode = null
let sourceNode = null
let currentVideoElement = null

const hasVideo = computed(() => !!subtitleStore.videoFile)

const currentTimeDisplay = computed(() => formatTime(currentTime.value))
const durationDisplay = computed(() => formatTime(duration.value))

function formatTime(seconds) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

function dbToGain(db) {
  if (db <= -20) return 0
  return Math.pow(10, db / 20)
}

function setupAudioContext(video) {
  if (!video || video === currentVideoElement) return
  
  currentVideoElement = video
  
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
    
    if (sourceNode) {
      sourceNode.disconnect()
    }
    
    sourceNode = audioContext.createMediaElementSource(video)
    gainNode = audioContext.createGain()
    
    sourceNode.connect(gainNode)
    gainNode.connect(audioContext.destination)
    
    gainNode.gain.value = dbToGain(volumeDb.value)
  } catch (e) {
    console.error('Audio context setup failed:', e)
  }
}

function togglePlay() {
  const video = subtitleStore.videoElement
  if (video) {
    if (video.paused) {
      video.play()
      isPlaying.value = true
    } else {
      video.pause()
      isPlaying.value = false
    }
  }
}

function reset() {
  const video = subtitleStore.videoElement
  if (video) {
    video.pause()
    video.currentTime = 0
    isPlaying.value = false
  }
}

function toggleMute() {
  isMuted.value = !isMuted.value
  if (gainNode) {
    gainNode.gain.value = isMuted.value ? 0 : dbToGain(volumeDb.value)
  }
}

function handleVolumeChange(db) {
  if (gainNode && !isMuted.value) {
    gainNode.gain.value = dbToGain(db)
  }
}

function handleProgressChange(value) {
  const video = subtitleStore.videoElement
  if (video && duration.value > 0) {
    video.currentTime = (value / 100) * duration.value
  }
}

function toggleFullscreen() {
  const container = document.querySelector('.video-player')
  if (container) {
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      container.requestFullscreen()
    }
  }
}

watch(() => subtitleStore.videoElement, (video, oldVideo) => {
  if (video) {
    setupVideoListeners(video)
    setupAudioContext(video)
  } else {
    resetControls()
  }
}, { immediate: true })

function resetControls() {
  isPlaying.value = false
  isMuted.value = false
  volumeDb.value = 0
  progressValue.value = 0
  currentTime.value = 0
  duration.value = 0
}

function setupVideoListeners(video) {
  video.addEventListener('timeupdate', () => {
    currentTime.value = video.currentTime
    if (duration.value > 0) {
      progressValue.value = (video.currentTime / duration.value) * 100
    }
  })
  video.addEventListener('loadedmetadata', () => {
    duration.value = video.duration
  })
  video.addEventListener('durationchange', () => {
    duration.value = video.duration
  })
  video.addEventListener('play', () => {
    isPlaying.value = true
    if (audioContext && audioContext.state === 'suspended') {
      audioContext.resume()
    }
  })
  video.addEventListener('pause', () => {
    isPlaying.value = false
  })
  if (video.duration) {
    duration.value = video.duration
  }
}

onUnmounted(() => {
  if (sourceNode) {
    sourceNode.disconnect()
  }
  if (gainNode) {
    gainNode.disconnect()
  }
  if (audioContext) {
    audioContext.close()
  }
})
</script>

<style lang="scss" scoped>
.video-controls {
  background-color: $bg-color;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid $border-color;

  .el-slider {
    width: 100%;
  }

  .video-buttons {
    display: flex;
    align-items: center;
    gap: 8px;

    .el-button {
      padding: 6px 10px;
    }

    .volume-slider {
      width: 100px;
    }

    .time {
      margin-left: auto;
      font-size: $font-size-base;
      white-space: nowrap;
    }
  }
}
</style>
