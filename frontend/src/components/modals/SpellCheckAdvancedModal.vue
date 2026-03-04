<template>
  <el-dialog
    v-model="visible"
    title="拼写检查提示词设置"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-input
      v-model="promptTemplate"
      type="textarea"
      :rows="8"
      placeholder="使用 {text} 表示要检查的文本"
    />
    <p class="hint">
      提示：{text} = 要检查的文本
    </p>

    <template #footer>
      <el-button @click="resetPrompt">恢复默认</el-button>
      <el-button type="primary" @click="save">保存</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'

const uiStore = useUIStore()

const visible = computed({
  get: () => uiStore.spellCheckAdvancedModalVisible,
  set: (value) => value ? uiStore.showSpellCheckAdvancedModal() : uiStore.hideSpellCheckAdvancedModal()
})

const DEFAULT_PROMPT = `Check the spelling of the following subtitle text and correct any errors.

IMPORTANT RULES:
1. Fix ONLY actual spelling errors - do NOT change correct words
2. Preserve the original text structure and formatting
3. Keep proper nouns and names unchanged (people, places, brands, technical terms)
4. For each correction, provide the original word and the corrected word
5. If no errors found, return empty corrections array

Output ONLY a valid JSON object:
{
  "corrected_text": "the corrected full text",
  "corrections": [
    {
      "original": "misspelled word",
      "corrected": "corrected word"
    }
  ]
}

Text to check:
{text}`

const promptTemplate = ref(DEFAULT_PROMPT)

watch(visible, (val) => {
  if (val) {
    const saved = localStorage.getItem('spellCheckPromptTemplate')
    if (saved) {
      promptTemplate.value = saved
    } else {
      promptTemplate.value = DEFAULT_PROMPT
    }
  }
})

function resetPrompt() {
  promptTemplate.value = DEFAULT_PROMPT
  ElMessage.success('已恢复默认提示词')
}

function save() {
  localStorage.setItem('spellCheckPromptTemplate', promptTemplate.value)
  ElMessage.success('提示词已保存')
  close()
}

function close() {
  uiStore.hideSpellCheckAdvancedModal()
}
</script>

<style lang="scss" scoped>
.hint {
  margin-top: 10px;
  color: $text-muted;
  font-size: $font-size-base;
}
</style>
