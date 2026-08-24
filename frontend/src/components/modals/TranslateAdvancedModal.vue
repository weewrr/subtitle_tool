<template>
  <el-dialog
    v-model="visible"
    title="翻译提示词设置"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-input
      v-model="promptTemplate"
      type="textarea"
      :rows="5"
      placeholder="支持占位符：{0}/{source_language}=源语言, {1}/{target_language}=目标语言, {2}/{duration}=原文语音时长(秒), {text}=待翻译文本"
    />
    <p class="hint">
      提示：{0}/{source_language} = 源语言，{1}/{target_language} = 目标语言，{2}/{duration} = 原文语音时长(秒)，{text} = 要翻译的文本
    </p>

    <template #footer>
      <el-button type="primary" @click="save">保存</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'

const uiStore = useUIStore()

const visible = computed({
  get: () => uiStore.translateAdvancedModalVisible,
  set: (value) => value ? uiStore.showTranslateAdvancedModal() : uiStore.hideTranslateAdvancedModal()
})

const promptTemplate = ref(`Translate from {source_language} to {target_language}.

The original speech duration is approximately {duration} seconds.

Translate the text naturally and concisely, taking the available speaking time into consideration.

Preserve the original meaning and all important information.
Do not add information that is not present in the original text.
Avoid unnecessary words, redundancy, and overly literal expressions.
When multiple natural translations are possible, prefer the more concise expression when it better fits the available duration.

The duration is a soft constraint, not an exact character limit.
Do not sacrifice important meaning, accuracy, grammar, or naturalness just to make the translation shorter.

Use natural expressions appropriate for the target language and context.

Keep the original punctuation structure as much as possible, while allowing natural punctuation adjustments required by the target language.

Do not censor the translation.
Give only the translated text without comments, explanations, notes, or labels.

Text:
{text}`)

function save() {
  localStorage.setItem('translatePromptTemplate', promptTemplate.value)
  ElMessage.success('提示词已保存')
  close()
}

function close() {
  uiStore.hideTranslateAdvancedModal()
}
</script>

<style lang="scss" scoped>
.hint {
  margin-top: 10px;
  color: $text-muted;
  font-size: $font-size-base;
}
</style>
