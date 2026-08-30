<template>
  <el-dialog
    v-model="visible"
    title="批处理模式"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <p class="description">批量处理多个视频或音频文件，生成字幕</p>

    <div class="batch-controls">
      <el-button @click="addFiles">添加文件</el-button>
      <el-button @click="clearFiles">清空列表</el-button>
    </div>

    <el-table :data="batchFiles" border size="small" max-height="300">
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="size" label="大小" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ $index }">
          <el-button type="danger" size="small" @click="removeFile($index)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-divider content-position="left">处理设置</el-divider>

    <el-form label-width="60px" size="small" inline>
      <el-form-item label="引擎">
        <el-select v-model="engine" @change="loadModels" style="width: 160px">
          <el-option label="OpenAI Whisper" value="openai" />
          <el-option label="Whisper.cpp" value="whisper-cpp" />
          <el-option label="Whisper-CTranslate2" value="whisper-ctranslate2" />
        </el-select>
      </el-form-item>
      <el-form-item label="语言">
        <el-select v-model="language" style="width: 120px">
          <el-option label="English" value="English" />
          <el-option label="Chinese" value="Chinese" />
          <el-option label="Auto-detect" value="Auto-detect" />
        </el-select>
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="selectedModel" style="width: 160px">
          <el-option
            v-for="model in models"
            :key="model.name"
            :label="model.label"
            :value="model.name"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <div v-if="isProcessing" class="progress-section">
      <el-progress :percentage="progress" />
      <p class="progress-text">{{ progressText }}</p>
    </div>

    <input
      type="file"
      ref="fileInput"
      accept="video/*,audio/*"
      multiple
      style="display: none"
      @change="handleFileSelect"
    />

    <template #footer>
      <el-button type="primary" @click="startProcessing" :loading="isProcessing">开始处理</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useTaskStore } from '@/stores/taskStore'
import { apiService } from '@/services/ApiService'

const uiStore = useUIStore()
const taskStore = useTaskStore()

let dockTaskId = null
let cancelRequested = false

const visible = computed({
  get: () => uiStore.batchProcessingModalVisible,
  set: (value) => value ? uiStore.showBatchProcessingModal() : uiStore.hideBatchProcessingModal()
})

const fileInput = ref(null)
const batchFiles = ref([])
const engine = ref('openai')
const language = ref('Auto-detect')
const selectedModel = ref('base')
const models = ref([])
const isProcessing = ref(false)
const progress = ref(0)
const progressText = ref('')

watch(visible, (val) => {
  if (val) {
    loadModels()
  }
})

async function loadModels() {
  try {
    let modelList = []
    
    if (engine.value === 'vosk') {
      const voskModels = await apiService.listVoskModels()
      modelList = voskModels.map(m => ({ name: m.code, label: m.name }))
    } else {
      const whisperModels = await apiService.listModels()
      modelList = whisperModels.map(m => ({
        name: m.name,
        label: `${m.name} (${m.size})${m.downloaded ? ' ✓' : ''}`
      }))
    }
    
    models.value = modelList
    if (modelList.length > 0) {
      selectedModel.value = modelList[0].name
    }
  } catch (error) {
    ElMessage.error('加载模型列表失败')
  }
}

function addFiles() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const files = e.target.files
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    batchFiles.value.push({
      name: file.name,
      size: formatSize(file.size),
      status: '待处理',
      file: file
    })
  }
  e.target.value = ''
}

function formatSize(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function clearFiles() {
  batchFiles.value = []
}

function removeFile(index) {
  batchFiles.value.splice(index, 1)
}

function getStatusType(status) {
  const typeMap = {
    '待处理': 'info',
    '处理中...': 'warning',
    '完成': 'success',
    '失败': 'danger'
  }
  return typeMap[status] || 'info'
}

async function startProcessing() {
  if (batchFiles.value.length === 0) {
    ElMessage.warning('请先添加文件')
    return
  }

  isProcessing.value = true
  progress.value = 0
  cancelRequested = false

  const total = batchFiles.value.length
  // 任务坞后台运行:弹窗关闭,进度/取消在底部任务坞
  dockTaskId = taskStore.startTask({
    title: '批量识别',
    detail: `共 ${total} 个文件 · ${selectedModel.value}`,
    cancel: () => { cancelRequested = true }
  })
  taskStore.updateTask(dockTaskId, { progress: 0 })
  uiStore.hideBatchProcessingModal()

  try {
    for (let i = 0; i < total; i++) {
      if (cancelRequested) break

      const fileItem = batchFiles.value[i]
      fileItem.status = '处理中...'
      progressText.value = `处理 ${i + 1}/${total} - ${fileItem.name}`
      taskStore.updateTask(dockTaskId, {
        progress: Math.round((i / total) * 100),
        detail: `(${i + 1}/${total}) ${fileItem.name}`
      })

      const task = await apiService.transcribe(fileItem.file, selectedModel.value, language.value, engine.value)

      let isComplete = false
      while (!isComplete) {
        if (cancelRequested) isComplete = true

        const status = await apiService.getTranscribeStatus(task.task_id)
        progress.value = Math.round(((i + (status.progress || 0) / 100) / total) * 100)
        taskStore.updateTask(dockTaskId, { progress: progress.value })

        if (!status.transcribing || cancelRequested) {
          isComplete = true
          fileItem.status = cancelRequested ? '已取消' : (status.error ? '失败' : '完成')
        } else {
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      }
      if (cancelRequested) break
    }

    if (cancelRequested) {
      taskStore.finishTask(dockTaskId, 'cancelled', `已取消 · 完成 ${batchFiles.value.filter(f => f.status === '完成').length}/${total}`)
      ElMessage.info('批量识别已取消')
    } else {
      taskStore.finishTask(dockTaskId, 'success', `完成 · 共 ${total} 个文件`)
      ElMessage.success(`批处理完成，共处理 ${total} 个文件`)
    }
    close()
  } catch (error) {
    if (dockTaskId !== null) taskStore.finishTask(dockTaskId, 'error', error.message)
    ElMessage.error(`批处理失败: ${error.message}`)
  } finally {
    isProcessing.value = false
    dockTaskId = null
  }
}

function close() {
  uiStore.hideBatchProcessingModal()
}

function handleClose() {
  uiStore.showSpeechRecognitionModal()
}
</script>

<style lang="scss" scoped>
.description {
  margin-bottom: 16px;
  color: $text-secondary;
}

.batch-controls {
  margin-bottom: 12px;
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
