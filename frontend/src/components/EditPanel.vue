<template>
  <div class="edit-panel">
    <div class="edit-row">
      <div class="edit-field text-input">
        <label>原文</label>
        <el-input
          v-model="originalText"
          type="textarea"
          :rows="2"
          placeholder="原文"
          @input="handleOriginalInput"
        />
      </div>
    </div>
    <div class="edit-row">
      <div class="edit-field text-input">
        <label>翻译</label>
        <el-input
          v-model="translatedText"
          type="textarea"
          :rows="2"
          placeholder="翻译结果"
          @input="handleTranslationInput"
        />
      </div>
    </div>
    <div class="nav-buttons">
      <el-button @click="prevParagraph" :disabled="!canGoPrev">上一行</el-button>
      <el-button @click="nextParagraph" :disabled="!canGoNext">下一行</el-button>
      <div class="separator"></div>
      <el-button type="primary" @click="translateCurrent" :loading="isTranslating">翻译文本</el-button>
      <el-select v-model="translateEngine" style="width: 120px">
        <el-option label="GPT-4" value="gpt-4" />
        <el-option label="GPT-3.5" value="gpt-3.5" />
        <el-option label="Claude 3" value="claude-3" />
        <el-option label="DeepL" value="deepl" />
      </el-select>
      <el-button @click="showConfig">配置模型</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { apiService } from '@/services/ApiService'

const subtitleStore = useSubtitleStore()
const uiStore = useUIStore()

const originalText = ref('')
const translatedText = ref('')
const translateEngine = ref('deepl')
const isTranslating = ref(false)

const canGoPrev = computed(() => subtitleStore.selectedParagraphIndex > 0)
const canGoNext = computed(() => subtitleStore.selectedParagraphIndex < subtitleStore.paragraphCount - 1)

watch(() => subtitleStore.selectedParagraph, (paragraph) => {
  if (paragraph) {
    originalText.value = paragraph.text
    translatedText.value = paragraph.translation || ''
  } else {
    originalText.value = ''
    translatedText.value = ''
  }
})

function handleOriginalInput() {
  if (subtitleStore.selectedParagraphIndex >= 0) {
    subtitleStore.updateParagraphText(subtitleStore.selectedParagraphIndex, originalText.value)
  }
}

function handleTranslationInput() {
  if (subtitleStore.selectedParagraphIndex >= 0) {
    subtitleStore.updateParagraphTranslation(subtitleStore.selectedParagraphIndex, translatedText.value)
  }
}

function prevParagraph() {
  if (canGoPrev.value) {
    subtitleStore.selectParagraph(subtitleStore.selectedParagraphIndex - 1)
  }
}

function nextParagraph() {
  if (canGoNext.value) {
    subtitleStore.selectParagraph(subtitleStore.selectedParagraphIndex + 1)
  }
}

async function translateCurrent() {
  if (!originalText.value) {
    ElMessage.warning('没有可翻译的文本')
    return
  }

  isTranslating.value = true
  try {
    const result = await apiService.translate({
      text: originalText.value,
      engine: translateEngine.value,
      from: 'en',
      to: 'zh'
    })
    
    if (result.translated) {
      translatedText.value = result.translated
      handleTranslationInput()
      ElMessage.success('翻译完成')
    } else if (result.error) {
      ElMessage.error(`翻译失败: ${result.error}`)
    }
  } catch (error) {
    ElMessage.error(`翻译失败: ${error.message}`)
  } finally {
    isTranslating.value = false
  }
}

function showConfig() {
  ElMessage.info('模型配置功能开发中')
}
</script>

<style lang="scss" scoped>
.edit-panel {
  background-color: $bg-color;
  padding: 8px;
  border: 1px solid $border-color;

  .edit-row {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    margin-bottom: 8px;
  }

  .edit-field {
    display: flex;
    flex-direction: column;
    flex: 1;

    label {
      font-size: $font-size-base;
      margin-bottom: 4px;
      color: $text-secondary;
    }
  }

  .nav-buttons {
    display: flex;
    gap: 4px;
    align-items: center;

    .separator {
      width: 1px;
      height: 20px;
      background-color: $border-color;
      margin: 0 4px;
    }
  }
}
</style>
