<template>
  <div class="tts-panel">
    <div class="tts-header">
      <div class="header-left">
        <h4>文本转语音</h4>
        <el-tag v-if="engines.length > 0" size="small" type="success">
          {{ engines.length }} 个引擎可用
        </el-tag>
      </div>
      <div class="header-buttons">
        <el-button size="small" @click="exportAudio" :disabled="!hasGeneratedAudio">
          <el-icon><Headset /></el-icon>导出音频
        </el-button>
        <el-button size="small" @click="closeAudio" :disabled="!hasGeneratedAudio && !isOpenedAudioFile">
          <el-icon><Close /></el-icon>关闭音频
        </el-button>
      </div>
    </div>
    
    <el-form label-width="80px" size="small">
      <el-form-item label="引擎">
        <el-select v-model="ttsEngine" style="width: 100%" @change="onEngineChange">
          <el-option 
            v-for="engine in engines" 
            :key="engine.id" 
            :label="engine.name" 
            :value="engine.id"
          >
            <div class="engine-option">
              <span>{{ engine.name }}</span>
              <span class="engine-desc">{{ engine.description }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item v-if="ttsEngine === 'qwen3-tts'" label="模式">
        <el-select v-model="qwenMode" style="width: 100%">
          <el-option label="ICL (高质量)" value="icl">
            <div class="mode-option">
              <span>ICL (高质量)</span>
              <span class="mode-desc">克隆质量更高，需要参考文本</span>
            </div>
          </el-option>
          <el-option label="xvec_only (快速)" value="xvec_only">
            <div class="mode-option">
              <span>xvec_only (快速)</span>
              <span class="mode-desc">速度更快，参考文本可选</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item label="参考音频">
        <div class="audio-upload-row">
          <el-select v-model="ttsVoice" style="flex: 1" placeholder="选择或上传参考音频" @visible-change="onVoiceDropdownChange">
            <el-option 
              v-for="voice in voices" 
              :key="voice.filename" 
              :label="voice.name" 
              :value="voice.filename"
            />
          </el-select>
          <el-upload
            ref="uploadRef"
            :action="uploadUrl"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :show-file-list="false"
            accept=".wav,.mp3,.ogg,.m4a,.flac"
          >
            <el-button size="small" type="primary">
              <el-icon><Upload /></el-icon>
            </el-button>
          </el-upload>
        </div>
      </el-form-item>
      
      <el-form-item label="音频文本">
        <el-input 
          v-model="promptText" 
          :placeholder="promptTextPlaceholder" 
          style="width: 100%"
        />
      </el-form-item>
      
      <el-form-item>
        <el-button 
          type="primary" 
          @click="generateSpeech" 
          :loading="isGenerating"
          :disabled="!canGenerate"
        >
          {{ isGenerating ? '生成中...' : '生成语音' }}
        </el-button>
        <el-button 
          @click="importAudio"
        >
          导入音频
        </el-button>
        <input 
          type="file" 
          ref="audioInputRef" 
          @change="handleAudioImport" 
          accept="audio/*" 
          style="display: none"
        />
      </el-form-item>
      
      <el-form-item v-if="isGenerating">
        <p class="progress-text">{{ progressText }}</p>
      </el-form-item>
    </el-form>
    
    <audio ref="audioPlayer" v-if="generatedAudioUrl" :src="generatedAudioUrl" controls style="width: 100%; margin-top: 12px;"></audio>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useRecentFilesStore, FILE_TYPES } from '@/stores/recentFilesStore'
import axios from 'axios'
import { getBackendBaseUrl } from '@/utils/runtime'

const subtitleStore = useSubtitleStore()
const recentFilesStore = useRecentFilesStore()

const ttsEngine = ref('spark-tts')
const qwenMode = ref('icl')
const ttsVoice = ref('')
const promptText = ref('')
const isGenerating = ref(false)
const progressText = ref('')
const generatedAudioUrl = ref('')
const engines = ref([])
const audioPlayer = ref(null)
const audioInputRef = ref(null)
const voices = ref([])
const uploadRef = ref(null)
let statusPollingInterval = null

const uploadUrl = computed(() => `${getBackendBaseUrl()}/api/tts/upload-voice`)
const uploadHeaders = computed(() => ({}))

const hasGeneratedAudio = computed(() => !!generatedAudioUrl.value || !!subtitleStore.dubbingAudioFile)

const promptTextPlaceholder = computed(() => {
  if (ttsEngine.value === 'qwen3-tts' && qwenMode.value === 'xvec_only') {
    return '参考音频文本（可选）'
  }
  return '参考音频对应的文本内容（可选，推荐用于同语言克隆）'
})

watch(() => subtitleStore.dubbingAudioFile, (newFile) => {
  if (newFile && typeof newFile === 'string') {
    const encodedPath = encodeURIComponent(newFile)
    generatedAudioUrl.value = `${getBackendBaseUrl()}/api/video/serve?path=${encodedPath}`
  }
})

const canGenerate = computed(() => {
  return subtitleStore.paragraphCount > 0 && !isGenerating.value && ttsVoice.value
})

function isAudioFile(file) {
  if (!file) return false
  const audioExtensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma']
  const fileName = (typeof file === 'string' ? file : file.name).toLowerCase()
  return audioExtensions.some(ext => fileName.endsWith(ext)) || 
         (typeof file !== 'string' && file.type && file.type.startsWith('audio/'))
}

const isOpenedAudioFile = computed(() => {
  return subtitleStore.videoFile && isAudioFile(subtitleStore.videoFile)
})

onMounted(async () => {
  await fetchEngines()
  await fetchVoices()
})

onUnmounted(() => {
  stopStatusPolling()
})

async function fetchEngines() {
  try {
    const response = await axios.get('/api/tts/engines')
    if (response.data.success) {
      engines.value = response.data.engines
      if (engines.value.length > 0 && !engines.value.find(e => e.id === ttsEngine.value)) {
        ttsEngine.value = engines.value[0].id
      }
    }
  } catch (error) {
    console.error('Failed to fetch engines:', error)
  }
}

async function fetchVoices() {
  try {
    const response = await axios.get('/api/tts/voices')
    if (response.data.success) {
      voices.value = response.data.voices
    }
  } catch (error) {
    console.error('Failed to fetch voices:', error)
  }
}

function onEngineChange() {
  if (ttsEngine.value === 'qwen3-tts') {
    qwenMode.value = 'icl'
  }
}

function onVoiceDropdownChange(visible) {
  if (visible) {
    fetchVoices()
  }
}

function beforeUpload(file) {
  const allowedExtensions = ['.wav', '.mp3', '.ogg', '.m4a', '.flac']
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  
  if (!allowedExtensions.includes(ext)) {
    ElMessage.error('不支持的音频格式，请上传 WAV, MP3, OGG, M4A 或 FLAC 文件')
    return false
  }
  return true
}

function handleUploadSuccess(response) {
  if (response.success) {
    ElMessage.success('上传成功')
    fetchVoices()
    ttsVoice.value = response.voice.filename
  } else {
    ElMessage.error('上传失败: ' + response.error)
  }
}

function handleUploadError(error) {
  ElMessage.error('上传失败: ' + (error.message || '未知错误'))
}

async function generateSpeech() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('没有可用的字幕')
    return
  }
  
  if (!ttsVoice.value) {
    ElMessage.warning('请选择或上传参考音频')
    return
  }
  
  isGenerating.value = true
  progressText.value = '正在准备...'
  
  try {
    const paragraphs = subtitleStore.currentSubtitle.paragraphs
    const subtitles = paragraphs.map(p => ({
      text: p.translation || p.text,
      start_time: p.startTime.totalMilliseconds,
      end_time: p.endTime.totalMilliseconds
    }))
    
    progressText.value = '正在启动生成任务...'
    
    const voice = voices.value.find(v => v.filename === ttsVoice.value)
    const promptSpeechPath = voice ? voice.path : null
    
    console.log('[TtsPanel] Using reference audio:', promptSpeechPath)
    console.log('[TtsPanel] Using engine:', ttsEngine.value)
    console.log('[TtsPanel] Using mode:', qwenMode.value)
    
    const response = await axios.post('/api/tts/generate-subtitles', {
      subtitles: subtitles,
      prompt_speech_path: promptSpeechPath,
      prompt_text: promptText.value.trim() || null,
      engine: ttsEngine.value,
      mode: qwenMode.value
    })
    
    if (response.data.success && response.data.status === 'started') {
      progressText.value = '正在生成语音...'
      startStatusPolling()
    } else if (response.data.error) {
      ElMessage.error('生成失败: ' + response.data.error)
      isGenerating.value = false
    }
  } catch (error) {
    ElMessage.error('生成语音失败: ' + (error.response?.data?.error || error.message))
    isGenerating.value = false
  }
}

function startStatusPolling() {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
  }
  
  statusPollingInterval = setInterval(async () => {
    try {
      const response = await axios.get('/api/tts/status')
      const status = response.data.status
      
      if (status.status === 'preparing') {
        progressText.value = '正在准备...'
      } else if (status.status === 'generating') {
        progressText.value = '正在生成语音...'
      } else if (status.status === 'completed') {
        stopStatusPolling()
        progressText.value = '正在获取结果...'
        
        try {
          const resultResponse = await axios.get('/api/tts/result')
          if (resultResponse.data.success) {
            const outputPath = resultResponse.data.output_path
            generatedAudioUrl.value = getBackendBaseUrl() + '/api/tts/download/' + encodeURIComponent(outputPath.split(/[/\\]/).pop()) + '?t=' + Date.now()
            progressText.value = '生成完成'
            ElMessage.success('语音生成成功')
          } else {
            ElMessage.error('获取结果失败')
          }
        } catch (e) {
          ElMessage.error('获取结果失败: ' + e.message)
        }
        isGenerating.value = false
      } else if (status.status === 'error') {
        stopStatusPolling()
        ElMessage.error('生成失败: ' + (status.error || '未知错误'))
        isGenerating.value = false
      } else if (status.status === 'aborted') {
        stopStatusPolling()
        ElMessage.info('生成已取消')
        isGenerating.value = false
      }
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  }, 1000)
}

function stopStatusPolling() {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
    statusPollingInterval = null
  }
}

function importAudio() {
  if (window.electronAPI) {
    importAudioElectron()
  } else if (audioInputRef.value) {
    audioInputRef.value.click()
  }
}

async function importAudioElectron() {
  const result = await window.electronAPI.selectAudioFile()
  if (result.success) {
    subtitleStore.setDubbingAudioFile(result.filePath)
    ElMessage.success(`已导入音频: ${result.fileName}`)
    recentFilesStore.addRecentFile(result.filePath, result.fileName, FILE_TYPES.AUDIO)
  }
}

function handleAudioImport(event) {
  const file = event.target.files[0]
  if (!file) return
  
  const validTypes = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/m4a', 'audio/aac', 'audio/flac', 'audio/mp3']
  const isValidType = validTypes.some(type => file.type === type) || file.name.match(/\.(mp3|wav|ogg|m4a|aac|flac)$/i)
  
  if (!isValidType) {
    ElMessage.error('请选择有效的音频文件 (MP3, WAV, OGG, M4A, AAC, FLAC)')
    return
  }
  
  const url = URL.createObjectURL(file)
  generatedAudioUrl.value = url
  subtitleStore.setDubbingAudioFile(file)
  ElMessage.success(`已导入音频: ${file.name}`)
  
  if (file.path) {
    recentFilesStore.addRecentFile(file.path, file.name, FILE_TYPES.AUDIO)
  }
  
  event.target.value = ''
}

function closeAudio() {
  if (generatedAudioUrl.value) {
    URL.revokeObjectURL(generatedAudioUrl.value)
    generatedAudioUrl.value = ''
    subtitleStore.setDubbingAudioFile(null)
    ElMessage.success('已关闭音频')
    return
  }
  
  if (subtitleStore.videoFile && isAudioFile(subtitleStore.videoFile)) {
    subtitleStore.setVideoFile(null)
    subtitleStore.setVideoElement(null)
    ElMessage.success('已关闭音频文件')
    return
  }
  
  ElMessage.info('当前没有打开的音频')
}

async function exportAudio() {
  if (!generatedAudioUrl.value) {
    ElMessage.warning('没有可导出的音频')
    return
  }
  
  try {
    ElMessage.info('正在准备导出...')
    
    const response = await fetch(generatedAudioUrl.value)
    const blob = await response.blob()
    
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'dubbed_audio.wav'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    setTimeout(() => URL.revokeObjectURL(url), 100)
    
    ElMessage.success('音频导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('音频导出失败: ' + error.message)
  }
}
</script>

<style lang="scss" scoped>
.tts-panel {
  flex: 1;
  padding: 12px;
  overflow: auto;

  .tts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      h4 {
        margin: 0;
        font-size: $font-size-lg;
        color: $text-color;
      }
    }

    .header-buttons {
      display: flex;
      gap: 8px;
    }
  }

  .audio-upload-row {
    display: flex;
    gap: 8px;
    width: 100%;
  }

  .el-form-item {
    margin-bottom: 12px;
  }
  
  .progress-text {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
    text-align: center;
  }
  
  .engine-option, .mode-option {
    display: flex;
    flex-direction: column;
    gap: 2px;
    
    .engine-desc, .mode-desc {
      font-size: 11px;
      color: #909399;
    }
  }
}
</style>
