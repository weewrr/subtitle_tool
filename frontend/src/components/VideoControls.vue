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
      <el-button
        :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
        :aria-label="isPlaying ? '暂停' : '播放'"
        @click="togglePlay"
        :disabled="!hasVideo"
      />
      <el-button icon="RefreshLeft" aria-label="回到开头" @click="reset" :disabled="!hasVideo" />
      <el-button
        :icon="isMuted ? 'Mute' : 'Microphone'"
        :aria-label="isMuted ? '取消静音' : '静音'"
        @click="toggleMute"
        :disabled="!hasVideo"
      />
      <el-slider
        v-model="volumeDb"
        :min="-20"
        :max="20"
        :disabled="!hasVideo || isMuted"
        :show-tooltip="false"
        class="volume-slider"
        aria-label="音量"
        @input="handleVolumeChange"
      />
      <span class="time">{{ currentTimeDisplay }} / {{ durationDisplay }}</span>
      <el-button icon="FullScreen" aria-label="全屏" @click="toggleFullscreen" :disabled="!hasVideo" />
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
let boundListenerElement = null
// Web Audio 链路失败(如元素已被绑定过/上下文异常)时,回退到原生 video.volume
let useWebAudio = true

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

// 回退模式:把 dB 滑块压缩映射到原生 0~1 音量(原生无法放大,>0dB 按 1 处理)
function applyNativeVolume(video) {
  if (!video) return
  video.muted = isMuted.value
  video.volume = Math.min(1, Math.max(0, dbToGain(volumeDb.value)))
}

function applyGain() {
  const target = isMuted.value ? 0 : dbToGain(volumeDb.value)
  if (useWebAudio && gainNode) {
    gainNode.gain.value = target
  } else if (currentVideoElement) {
    currentVideoElement.muted = isMuted.value
    currentVideoElement.volume = Math.min(1, Math.max(0, target))
  }
}

function setupAudioContext(video) {
  if (!video || video === currentVideoElement) return

  currentVideoElement = video
  useWebAudio = true

  try {
    if (!audioContext || audioContext.state === 'closed') {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }

    if (sourceNode) {
      try { sourceNode.disconnect() } catch (e) { /* 已断开时忽略 */ }
    }

    // 注意:createMediaElementSource 对同一元素只能成功一次,重复绑定会抛错
    sourceNode = audioContext.createMediaElementSource(video)
    gainNode = audioContext.createGain()

    sourceNode.connect(gainNode)
    gainNode.connect(audioContext.destination)

    gainNode.gain.value = isMuted.value ? 0 : dbToGain(volumeDb.value)

    // 无手势环境下 AudioContext 创建即为 suspended 状态,画面正常但无声,需主动恢复
    if (audioContext.state === 'suspended') {
      audioContext.resume().catch(() => {})
    }
  } catch (e) {
    // 元素已被绑定过或其他异常:回退到原生音量控制,保证有声
    console.warn('Web Audio 不可用,回退原生音量:', e)
    useWebAudio = false
    sourceNode = null
    gainNode = null
    applyNativeVolume(video)
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
  applyGain()
}

function handleVolumeChange() {
  if (!isMuted.value) {
    applyGain()
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

watch(() => subtitleStore.videoElement, (video) => {
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
  currentVideoElement = null
  boundListenerElement = null
}

function setupVideoListeners(video) {
  // 同一元素只绑定一次,避免 watch 重复触发时叠加监听器
  if (video === boundListenerElement) return
  boundListenerElement = video

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
    // 播放时兜底恢复 suspended 的 AudioContext(画面动但无声的常见原因)
    if (useWebAudio && audioContext && audioContext.state === 'suspended') {
      audioContext.resume().catch(() => {})
    }
    // 播放中途若已回退原生模式,确保音量生效
    if (!useWebAudio) {
      applyNativeVolume(video)
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
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;

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
      font-family: $font-family-mono;
      font-size: $font-size-sm;
      white-space: nowrap;
      color: var(--app-text-secondary);
      font-variant-numeric: tabular-nums;
    }
  }
}
</style>
