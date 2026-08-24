<template>
  <el-dialog
    v-model="visible"
    title="自动翻译"
    width="900px"
    :close-on-click-modal="false"
    :close-on-press-escape="!isTranslating || stopRequested"
    :show-close="!isTranslating || stopRequested"
  >
    <div class="translate-controls">
      <el-select v-model="engine" style="width: 170px" @change="onEngineChange">
        <el-option label="Ollama (local LLM)" value="ollama" />
        <el-option label="DeepSeek" value="deepseek" />
        <el-option label="阿里百炼 (Qwen)" value="bailian" />
      </el-select>
      <span>自:</span>
      <el-select v-model="fromLang" style="width: 120px">
        <el-option label="English" value="en" />
        <el-option label="Chinese" value="zh" />
        <el-option label="Japanese" value="ja" />
        <el-option label="Korean" value="ko" />
      </el-select>
      <span>至:</span>
      <el-select v-model="toLang" style="width: 140px">
        <el-option label="Chinese" value="zh" />
        <el-option label="English" value="en" />
        <el-option label="Japanese" value="ja" />
        <el-option label="Korean" value="ko" />
      </el-select>
      <el-button type="primary" @click="toggleTranslate" :loading="isTranslating && !stopRequested">
        {{ isTranslating ? '停止' : '翻译' }}
      </el-button>
    </div>

    <div class="translate-content">
      <div class="translate-panel">
        <el-table :data="originalSubtitles" border size="small" max-height="280">
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column label="时长" width="80" align="center">
            <template #default="{ row }">
              {{ row.duration?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="text" label="文本" />
        </el-table>
      </div>
      <div class="translate-panel">
        <el-table :data="translatedSubtitles" border size="small" max-height="280">
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column label="时长" width="80" align="center">
            <template #default="{ row }">
              {{ row.duration?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="translated" label="文本" />
        </el-table>
      </div>
    </div>

    <el-divider />

    <el-form label-width="40px" size="small" inline>
      <el-form-item v-if="engine === 'ollama'" label="Url">
        <el-input v-model="apiUrl" style="width: 280px" placeholder="http://localhost:11434/api/chat/" />
      </el-form-item>
      <el-form-item v-if="needsApiKey" label="Key">
        <el-input
          v-model="apiKey"
          type="password"
          show-password
          style="width: 280px"
          :placeholder="engine === 'deepseek' ? 'DeepSeek API Key (sk-...)' : '百炼 API Key (sk-...)'" />
      </el-form-item>
      <el-form-item label="模型">
        <el-select
          v-model="modelName"
          style="width: 220px"
          :filterable="modelEditable"
          :allow-create="modelEditable"
          :default-first-option="modelEditable"
          :placeholder="engine === 'deepseek' ? 'deepseek-chat' : 'qwen-plus'"
        >
          <el-option v-for="m in engineModels" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showAdvanced">高级</el-button>
      <el-button type="primary" @click="confirmTranslate">确定(O)</el-button>
      <el-button @click="handleCancel">{{ isTranslating ? '停止' : '取消(A)' }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { apiService } from '@/services/ApiService'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const visible = computed({
  get: () => uiStore.translateModalVisible,
  set: (value) => {
    if (!value && isTranslating.value && !stopRequested.value) {
      stopRequested.value = true
      return
    }
    value ? uiStore.showTranslateModal() : uiStore.hideTranslateModal()
  }
})

const ENGINE_MODEL_OPTIONS = {
  ollama: [
    { label: 'gpt-oss:120b-cloud', value: 'gpt-oss:120b-cloud' },
    { label: 'gpt-oss:20b-cloud', value: 'gpt-oss:20b-cloud' },
    { label: 'deepseek-v3.1:671b-cloud', value: 'deepseek-v3.1:671b-cloud' },
    { label: 'qwen3-coder:480b-cloud', value: 'qwen3-coder:480b-cloud' },
    { label: 'qwen3-vl:235b-cloud', value: 'qwen3-vl:235b-cloud' },
    { label: 'minimax-m2:cloud', value: 'minimax-m2:cloud' },
    { label: 'glm-4.6:cloud', value: 'glm-4.6:cloud' },
    { label: 'gpt-oss:120b', value: 'gpt-oss:120b' },
    { label: 'gpt-oss:20b', value: 'gpt-oss:20b' },
    { label: 'gemma3:27b', value: 'gemma3:27b' },
    { label: 'gemma3:12b', value: 'gemma3:12b' },
    { label: 'gemma3:4b', value: 'gemma3:4b' },
    { label: 'gemma3:1b', value: 'gemma3:1b' },
    { label: 'deepseek-r1:8b', value: 'deepseek-r1:8b' },
    { label: 'qwen3-coder:30b', value: 'qwen3-coder:30b' },
    { label: 'qwen3-vl:30b', value: 'qwen3-vl:30b' },
    { label: 'qwen3-vl:8b', value: 'qwen3-vl:8b' },
    { label: 'qwen3-vl:4b', value: 'qwen3-vl:4b' },
    { label: 'qwen3:30b', value: 'qwen3:30b' },
    { label: 'qwen3:8b', value: 'qwen3:8b' },
    { label: 'qwen3:4b', value: 'qwen3:4b' }
  ],
  deepseek: [
    { label: 'deepseek-chat (V3)', value: 'deepseek-chat' },
    { label: 'deepseek-reasoner (R1)', value: 'deepseek-reasoner' }
  ],
  bailian: [
    { label: 'qwen-plus', value: 'qwen-plus' },
    { label: 'qwen-turbo', value: 'qwen-turbo' },
    { label: 'qwen-max', value: 'qwen-max' },
    { label: 'qwen-flash', value: 'qwen-flash' }
  ]
}
const ENGINE_DEFAULT_MODEL = {
  ollama: 'gemma3:1b',
  deepseek: 'deepseek-chat',
  bailian: 'qwen-plus'
}

const engine = ref(localStorage.getItem('translateEngine') || 'ollama')
const fromLang = ref('en')
const toLang = ref('zh')
const apiUrl = ref('http://localhost:11434/api/chat/')
const modelName = ref(
  localStorage.getItem(`translateModel_${engine.value}`) || ENGINE_DEFAULT_MODEL[engine.value] || 'gemma3:1b'
)
const apiKey = ref(localStorage.getItem(`translateApiKey_${engine.value}`) || '')
const isTranslating = ref(false)
const stopRequested = ref(false)
const originalSubtitles = ref([])
const translatedSubtitles = ref([])

const needsApiKey = computed(() => engine.value === 'deepseek' || engine.value === 'bailian')
const modelEditable = computed(() => engine.value === 'deepseek' || engine.value === 'bailian')
const engineModels = computed(() => ENGINE_MODEL_OPTIONS[engine.value] || ENGINE_MODEL_OPTIONS.ollama)

function onEngineChange() {
  modelName.value = localStorage.getItem(`translateModel_${engine.value}`) || ENGINE_DEFAULT_MODEL[engine.value] || 'gemma3:1b'
  apiKey.value = localStorage.getItem(`translateApiKey_${engine.value}`) || ''
  localStorage.setItem('translateEngine', engine.value)
}

watch(apiKey, (v) => {
  if (needsApiKey.value && v) {
    localStorage.setItem(`translateApiKey_${engine.value}`, v)
  }
})

watch(modelName, (v) => {
  if (v) {
    localStorage.setItem(`translateModel_${engine.value}`, v)
  }
})

watch(visible, (val) => {
  if (val) {
    apiKey.value = localStorage.getItem(`translateApiKey_${engine.value}`) || ''
    originalSubtitles.value = subtitleStore.currentSubtitle.paragraphs.map(p => ({
      number: p.number,
      startTime: p.startTime,
      duration: p.duration,
      text: p.text
    }))
    translatedSubtitles.value = subtitleStore.currentSubtitle.paragraphs.map(p => ({
      number: p.number,
      startTime: p.startTime,
      duration: p.duration,
      translated: p.translation || ''
    }))
  }
})

function toggleTranslate() {
  if (isTranslating.value) {
    stopRequested.value = true
    return
  }
  startTranslate()
}

async function startTranslate() {
  if (originalSubtitles.value.length === 0) {
    ElMessage.warning('没有可翻译的字幕')
    return
  }

  if (needsApiKey.value && !apiKey.value.trim()) {
    ElMessage.error('请先填写该翻译引擎的 API Key')
    return
  }

  isTranslating.value = true
  stopRequested.value = false

  translatedSubtitles.value = originalSubtitles.value.map(item => ({
    ...item,
    translated: ''
  }))

  try {
    for (let i = 0; i < originalSubtitles.value.length; i++) {
      if (stopRequested.value) {
        ElMessage.info('翻译已停止')
        break
      }

      const item = originalSubtitles.value[i]

      // 原文在视频中的实际语音时长（秒），用于时长感知翻译
      const durationSeconds = item.duration && typeof item.duration.totalMilliseconds === 'number'
        ? Math.round((item.duration.totalMilliseconds / 1000) * 100) / 100
        : null

      const result = await apiService.translate({
        text: item.text,
        from: fromLang.value,
        to: toLang.value,
        engine: engine.value,
        model: modelName.value,
        duration: durationSeconds,
        api_key: needsApiKey.value ? apiKey.value.trim() : undefined
      })

      if (result.error) {
        ElMessage.error('翻译失败: ' + result.error)
        break
      }

      translatedSubtitles.value[i].translated = result.translated
    }

    const successCount = translatedSubtitles.value.filter(t => t.translated).length
    if (!stopRequested.value) {
      ElMessage.success('翻译完成，共 ' + successCount + ' 条字幕')
    }
  } catch (error) {
    ElMessage.error('翻译失败: ' + error.message)
  } finally {
    isTranslating.value = false
    stopRequested.value = false
  }
}

function showAdvanced() {
  uiStore.showTranslateAdvancedModal()
}

function confirmTranslate() {
  if (translatedSubtitles.value.length > 0) {
    subtitleStore.currentSubtitle.paragraphs.forEach((paragraph, index) => {
      if (translatedSubtitles.value[index]) {
        paragraph.translation = translatedSubtitles.value[index].translated
      }
    })
    subtitleStore.showTranslation = true
    ElMessage.success('翻译已应用')
  }
  close()
}

function close() {
  uiStore.hideTranslateModal()
}

function handleCancel() {
  if (isTranslating.value) {
    stopRequested.value = true
  } else {
    close()
  }
}
</script>

<style lang="scss" scoped>
.translate-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.translate-content {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;

  .translate-panel {
    flex: 1;
    overflow: hidden;
  }
}
</style>
