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
      placeholder="使用 {0} 表示源语言，{1} 表示目标语言，{text} 表示要翻译的文本"
    />
    <p class="hint">
      提示：{0} = 源语言，{1} = 目标语言，{text} = 要翻译的文本
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

const promptTemplate = ref('Translate from {0} to {1}, keep punctuation as input, do not censor the translation, give only the output without comments or notes:')

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
