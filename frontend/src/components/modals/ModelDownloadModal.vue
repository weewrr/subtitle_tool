<template>
  <el-dialog
    v-model="visible"
    title="下载 OpenAI Whisper 模型"
    width="500px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <p class="description">选择要下载的 Whisper 模型：</p>

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

const selectedModel = ref('small')
const isDownloading = ref(false)
const progress = ref(0)
const progressText = ref('准备下载...')
const progressStatus = ref('')
const downloadedModels = ref([])

const modelList = [
  { name: 'tiny', size: '~75 MB', desc: '最快，准确度较低' },
  { name: 'base', size: '~142 MB', desc: '快速，准确度一般' },
  { name: 'small', size: '~466 MB', desc: '平衡速度和准确度' },
  { name: 'medium', size: '~1.5 GB', desc: '较慢，准确度较高' },
  { name: 'large', size: '~2.9 GB', desc: '最慢，准确度最高' }
]

watch(visible, async (val) => {
  if (val) {
    await loadDownloadedModels()
  }
})

async function loadDownloadedModels() {
  try {
    const models = await apiService.listModels()
    downloadedModels.value = models.filter(m => m.downloaded).map(m => m.name)
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
    await apiService.downloadModel(selectedModel.value)

    const statusInterval = setInterval(async () => {
      try {
        const status = await apiService.getModelStatus()
        progress.value = status.progress || 0
        progressText.value = getDownloadStatusText(status.status)

        if (!status.downloading) {
          clearInterval(statusInterval)
          
          if (status.error) {
            ElMessage.error(`下载失败: ${status.error}`)
            progressStatus.value = 'exception'
          } else if (status.status === 'completed') {
            ElMessage.success(`${selectedModel.value} 模型下载完成`)
            await loadDownloadedModels()
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
