<template>
  <el-dialog
    v-model="visible"
    title="音频转文字"
    width="600px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="!isTranscribing"
    :before-close="handleBeforeClose"
  >
    <p class="description">通过 Whisper 语音识别从音频生成文本</p>
    
    <el-form label-width="80px" size="small">
      <el-form-item label="引擎">
        <el-select v-model="engine" @change="loadModels" style="width: 100%">
          <el-option label="OpenAI Whisper" value="openai" />
          <el-option label="Whisper.cpp" value="whisper-cpp" />
          <el-option label="Whisper-CTranslate2" value="whisper-ctranslate2" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-divider content-position="left">语言和模型</el-divider>

    <el-form label-width="80px" size="small">
      <el-form-item label="选择语言">
        <el-select v-model="language" style="width: 100%">
          <el-option label="English" value="English" />
          <el-option label="Chinese" value="Chinese" />
          <el-option label="Auto-detect" value="Auto-detect" />
        </el-select>
      </el-form-item>
      <el-form-item label="选择模型">
        <el-select v-model="selectedModel" style="width: 200px">
          <el-option
            v-for="model in models"
            :key="model.name"
            :label="model.label"
            :value="model.name"
          />
        </el-select>
        <el-button @click="showDownloadModal" style="margin-left: 8px">...</el-button>
        <el-button @click="openModelFolder">打开模型文件夹</el-button>
      </el-form-item>
    </el-form>

    <el-checkbox v-model="useGpu">GPU加速</el-checkbox>

    <div v-if="isTranscribing" class="progress-section">
      <p class="progress-text">{{ progressText }}</p>
    </div>

    <template #footer>
      <el-button @click="showBatchMode" :disabled="isTranscribing">批处理模式</el-button>
      <el-button type="primary" @click="startTranscribe" :loading="isTranscribing" :disabled="isTranscribing">生成</el-button>
      <el-button @click="close" :disabled="isTranscribing">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { apiService } from '@/services/ApiService'
import { getBackendBaseUrl } from '@/utils/runtime'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const visible = computed({
  get: () => uiStore.speechRecognitionModalVisible,
  set: (value) => value ? uiStore.showSpeechRecognitionModal() : uiStore.hideSpeechRecognitionModal()
})

const engine = ref('openai')
const language = ref('Auto-detect')
const selectedModel = ref('base')
const models = ref([])
const useGpu = ref(true)
const isTranscribing = ref(false)
const progressText = ref('准备中...')
let statusPollingInterval = null

watch(visible, (val) => {
  if (val) {
    loadModels()
  }
})

onUnmounted(() => {
  stopStatusPolling()
})

async function loadModels() {
  try {
    let modelList = []
    
    if (engine.value === 'vosk') {
      const voskModels = await apiService.listVoskModels()
      modelList = voskModels.map(m => ({ name: m.code, label: m.name }))
    } else if (engine.value === 'whisper-cpp') {
      const whisperCppModels = await apiService.listWhisperCppModels()
      modelList = whisperCppModels.map(m => ({
        name: m.name,
        label: m.name + ' (' + m.size + ')' + (m.downloaded ? ' ✓' : '')
      }))
    } else if (engine.value === 'whisper-ctranslate2') {
      const whisperCt2Models = await apiService.listWhisperCTranslate2Models()
      modelList = whisperCt2Models.map(m => ({
        name: m.name,
        label: m.name + ' (' + m.size + ')' + (m.downloaded ? ' ✓' : '')
      }))
    } else {
      const whisperModels = await apiService.listModels()
      modelList = whisperModels.map(m => ({
        name: m.name,
        label: m.name + ' (' + m.size + ')' + (m.downloaded ? ' ✓' : '')
      }))
    }
    
    models.value = modelList
    if (modelList.length > 0) {
      selectedModel.value = modelList[0].name
    }
  } catch (error) {
    ElMessage.error('加载模型列表失败')
    models.value = []
  }
}

function showDownloadModal() {
  uiStore.hideSpeechRecognitionModal()
  uiStore.showModelDownloadModal(engine.value)
}

async function openModelFolder() {
  try {
    const result = await apiService.openModelFolder()
    if (result.message) {
      ElMessage.success(result.message)
    }
  } catch (error) {
    ElMessage.error('打开文件夹失败: ' + error.message)
  }
}

function showBatchMode() {
  if (isTranscribing.value) return
  uiStore.hideSpeechRecognitionModal()
  uiStore.showBatchProcessingModal()
}

async function startTranscribe() {
  if (!subtitleStore.videoFile) {
    ElMessage.warning('请先打开视频文件')
    return
  }

  isTranscribing.value = true
  progressText.value = '正在上传文件...'

  try {
    const formData = new FormData()
    formData.append('file', subtitleStore.videoFile)
    formData.append('model', selectedModel.value)
    formData.append('engine', engine.value)
    formData.append('use_gpu', useGpu.value ? 'true' : 'false')
    if (language.value && language.value !== 'Auto-detect') {
      formData.append('language', language.value.toLowerCase())
    }

    const response = await fetch(`${getBackendBaseUrl()}/api/transcribe`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || '上传失败')
    }

    const result = await response.json()
    
    if (result.status === 'started') {
      progressText.value = '任务已启动，正在处理...'
      startStatusPolling()
    } else if (result.error) {
      ElMessage.error('识别失败: ' + result.error)
      isTranscribing.value = false
    }
  } catch (error) {
    ElMessage.error('识别失败: ' + error.message)
    isTranscribing.value = false
  }
}

function startStatusPolling() {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
  }
  
  statusPollingInterval = setInterval(async () => {
    try {
      const status = await apiService.getTranscribeStatus()
      
      if (status.status === 'loading_model') {
        progressText.value = '正在加载模型...'
      } else if (status.status === 'transcribing') {
        progressText.value = '正在识别中...'
      } else if (status.status === 'completed') {
        stopStatusPolling()
        progressText.value = '正在获取结果...'
        
        try {
          const result = await apiService.getTranscribeResult()
          if (result && result.segments && result.segments.length > 0) {
            subtitleStore.loadFromTranscription(
              result.segments,
              subtitleStore.videoFile.name.replace(/\.[^/.]+$/, '') + '.srt'
            )
            ElMessage.success('识别完成，共 ' + result.segments.length + ' 条字幕')
            close()
          } else {
            ElMessage.warning('未识别到语音内容')
            isTranscribing.value = false
          }
        } catch (e) {
          ElMessage.error('获取结果失败: ' + e.message)
          isTranscribing.value = false
        }
      } else if (status.status === 'error') {
        stopStatusPolling()
        ElMessage.error('识别失败: ' + (status.error || '未知错误'))
        isTranscribing.value = false
      }
    } catch (error) {
      console.error('获取状态失败:', error)
    }
  }, 500)
}

function stopStatusPolling() {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
    statusPollingInterval = null
  }
}

function handleBeforeClose(done) {
  if (isTranscribing.value) {
    ElMessage.warning('正在转录中，请等待完成后再关闭')
    return
  }
  done()
}

function close() {
  isTranscribing.value = false
  stopStatusPolling()
  uiStore.hideSpeechRecognitionModal()
}
</script>

<style lang="scss" scoped>
.description {
  margin-bottom: 16px;
  color: $text-secondary;
}

.progress-section {
  margin-top: 16px;
  
  .progress-text {
    margin-top: 8px;
    font-size: $font-size-base;
    color: $text-secondary;
    text-align: center;
  }
}

:deep(.el-checkbox) {
  display: block;
  margin: 8px 0;
}
</style>
