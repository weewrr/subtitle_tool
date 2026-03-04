<template>
  <el-dialog
    v-model="visible"
    :title="modalTitle"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <p class="description">选择要下载的模型：<el-tag size="small" type="warning" style="margin-left: 8px">科学上网</el-tag></p>

    <el-radio-group v-model="selectedModel" class="model-list">
      <el-radio 
        v-for="model in modelList" 
        :key="model.name" 
        :value="model.name"
        :disabled="downloadedModels.includes(model.name)"
        class="model-item"
        :class="{ 'is-downloaded': downloadedModels.includes(model.name) }"
      >
        <div class="model-info">
          <span class="model-name">{{ model.name }}</span>
          <span class="model-size">{{ model.size }}</span>
          <span class="model-desc">{{ model.desc }}</span>
          <span v-if="downloadedModels.includes(model.name)" class="downloaded-tag">已下载</span>
        </div>
      </el-radio>
    </el-radio-group>

    <div v-if="isDownloading" class="progress-section">
      <el-progress :percentage="progress" :status="progressStatus" />
      <p class="progress-text">{{ progressText }}</p>
    </div>

    <template #footer>
      <el-button type="primary" @click="startDownload" :loading="isDownloading" :disabled="downloadedModels.includes(selectedModel)">下载</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { apiService } from '@/services/ApiService'

const uiStore = useUIStore()

const visible = computed({
  get: () => uiStore.modelDownloadModalVisible,
  set: (value) => value ? uiStore.showModelDownloadModal() : uiStore.hideModelDownloadModal()
})

const selectedEngine = computed(() => uiStore.currentEngine)
const selectedModel = ref('small')
const isDownloading = ref(false)
const progress = ref(0)
const progressText = ref('准备下载...')
const progressStatus = ref('')
const downloadedModels = ref([])

const modalTitle = computed(() => {
  if (selectedEngine.value === 'openai') {
    return '下载 OpenAI Whisper 模型'
  } else if (selectedEngine.value === 'whisper-cpp') {
    return '下载 Whisper.cpp 模型'
  } else if (selectedEngine.value === 'whisper-ctranslate2') {
    return '下载 Whisper-CTranslate2 模型'
  }
  return '下载模型'
})

const modelList = computed(() => {
  if (selectedEngine.value === 'openai') {
    return [
      { name: 'tiny', size: '~75 MB', desc: '最快，准确度较低' },
      { name: 'base', size: '~142 MB', desc: '快速，准确度一般' },
      { name: 'small', size: '~466 MB', desc: '平衡速度和准确度' },
      { name: 'medium', size: '~1.5 GB', desc: '较慢，准确度较高' },
      { name: 'large', size: '~2.9 GB', desc: '最慢，准确度最高' }
    ]
  } else if (selectedEngine.value === 'whisper-cpp') {
    return [
      { name: 'ggml-tiny.en', size: '~14 MB', desc: '英文专用，最快，准确度较低' },
      { name: 'ggml-tiny', size: '~39 MB', desc: '多语言，最快，准确度较低' },
      { name: 'ggml-base.en', size: '~29 MB', desc: '英文专用，快速，准确度一般' },
      { name: 'ggml-base', size: '~74 MB', desc: '多语言，快速，准确度一般' },
      { name: 'ggml-small.en', size: '~96 MB', desc: '英文专用，平衡速度和准确度' },
      { name: 'ggml-small', size: '~244 MB', desc: '多语言，平衡速度和准确度' },
      { name: 'ggml-medium.en', size: '~482 MB', desc: '英文专用，较慢，准确度较高' },
      { name: 'ggml-medium', size: '~1.5 GB', desc: '多语言，较慢，准确度较高' },
      { name: 'ggml-large-v3', size: '~2.9 GB', desc: '多语言，最慢，准确度最高' }
    ]
  } else if (selectedEngine.value === 'whisper-ctranslate2') {
    return [
      { name: 'tiny', size: '~39 MB', desc: '最快，准确度较低' },
      { name: 'base', size: '~74 MB', desc: '快速，准确度一般' },
      { name: 'small', size: '~244 MB', desc: '平衡速度和准确度' },
      { name: 'medium', size: '~1.5 GB', desc: '较慢，准确度较高' },
      { name: 'large-v1', size: '~2.9 GB', desc: '慢，准确度高' },
      { name: 'large-v2', size: '~2.9 GB', desc: '慢，准确度高' },
      { name: 'large-v3', size: '~2.9 GB', desc: '最慢，准确度最高' }
    ]
  }
  return []
})

watch(visible, async (val) => {
  if (val) {
    await loadModels()
  }
})

async function loadModels() {
  try {
    if (selectedEngine.value === 'openai') {
      const models = await apiService.listModels()
      downloadedModels.value = models.filter(m => m.downloaded).map(m => m.name)
    } else if (selectedEngine.value === 'whisper-cpp') {
      const models = await apiService.listWhisperCppModels()
      downloadedModels.value = models.filter(m => m.downloaded).map(m => m.name)
    } else if (selectedEngine.value === 'whisper-ctranslate2') {
      const models = await apiService.listWhisperCTranslate2Models()
      downloadedModels.value = models.filter(m => m.downloaded).map(m => m.name)
    }
    // 重置选中的模型
    if (modelList.value.length > 0) {
      selectedModel.value = modelList.value[0].name
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
  }
}

async function startDownload() {
  if (downloadedModels.value.includes(selectedModel.value)) {
    ElMessage.warning('该模型已下载')
    return
  }
  
  isDownloading.value = true
  progress.value = 0
  progressText.value = '准备下载...'
  progressStatus.value = ''

  try {
    if (selectedEngine.value === 'openai') {
      await apiService.downloadModel(selectedModel.value)
    } else if (selectedEngine.value === 'whisper-cpp') {
      await apiService.downloadWhisperCppModel(selectedModel.value)
    } else if (selectedEngine.value === 'whisper-ctranslate2') {
      await apiService.downloadWhisperCTranslate2Model(selectedModel.value)
    }

    const statusInterval = setInterval(async () => {
      try {
        let status
        if (selectedEngine.value === 'openai') {
          status = await apiService.getModelStatus()
        } else if (selectedEngine.value === 'whisper-cpp') {
          status = await apiService.getWhisperCppModelStatus()
        } else if (selectedEngine.value === 'whisper-ctranslate2') {
          status = await apiService.getWhisperCTranslate2ModelStatus()
        }
        progress.value = status.progress || 0
        progressText.value = getDownloadStatusText(status.status)

        if (!status.downloading) {
          clearInterval(statusInterval)
          
          if (status.error) {
            ElMessage.error(`下载失败: ${status.error}`)
            progressStatus.value = 'exception'
          } else if (status.status === 'completed') {
            ElMessage.success(`${selectedModel.value} 模型下载完成`)
            await loadModels()
            progressStatus.value = 'success'
          }
          isDownloading.value = false
        }
      } catch (error) {
        console.error('轮询状态失败:', error)
      }
    }, 200)
  } catch (error) {
    ElMessage.error(`下载失败: ${error.message}`)
    isDownloading.value = false
  }
}

function getDownloadStatusText(status) {
  const statusMap = {
    'idle': '准备中...',
    'installing_whisper': '正在安装 Whisper...',
    'downloading': '正在下载模型...',
    'completed': '完成',
    'error': '错误'
  }
  return statusMap[status] || '处理中...'
}

function close() {
  uiStore.hideModelDownloadModal()
  uiStore.showSpeechRecognitionModal()
}

function handleClose() {
  uiStore.showSpeechRecognitionModal()
}
</script>

<style lang="scss" scoped>
.description {
  margin-bottom: 12px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;

  .model-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border: 1px solid $border-color;
    border-radius: $border-radius;
    background-color: #fafafa;
    width: 100%;
    margin: 0;

    &:hover {
      background-color: $hover-bg;
    }

    &.is-downloaded {
      background-color: #f0f9eb;
      border-color: #67c23a;
      cursor: not-allowed;
    }

    .model-info {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-left: 8px;

      .model-name {
        font-weight: bold;
      }

      .model-size {
        color: $text-secondary;
      }

      .model-desc {
        font-size: $font-size-sm;
        color: $text-muted;
      }

      .downloaded-tag {
        color: #67c23a;
        font-size: $font-size-sm;
        margin-left: auto;
      }
    }
  }
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
</style>
