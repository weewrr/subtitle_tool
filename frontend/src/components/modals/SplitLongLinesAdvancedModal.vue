<template>
  <el-dialog
    v-model="visible"
    title="分割长句提示词设置"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-input
      v-model="promptTemplate"
      type="textarea"
      :rows="5"
      placeholder="使用 {text} 表示要分割的文本"
    />
    <p class="hint">
      提示：{text} = 要分析的文本。模型会自动判断是否需要分割，如不需要则原样输出。
    </p>

    <template #footer>
      <el-button type="primary" @click="save">保存</el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'

const uiStore = useUIStore()

const visible = computed({
  get: () => uiStore.splitLongLinesAdvancedModalVisible,
  set: (value) => value ? uiStore.showSplitLongLinesAdvancedModal() : uiStore.hideSplitLongLinesAdvancedModal()
})

const promptTemplate = ref('Analyze the following subtitle text. If it contains multiple sentences or is too long for a single subtitle line, split it into separate lines (one sentence per line). If it is already appropriate as a single subtitle line, output it unchanged. Only output the result, no explanations:\n\n{text}')

onMounted(() => {
  const saved = localStorage.getItem('splitLongLinesPromptTemplate')
  if (saved) {
    promptTemplate.value = saved
  }
})

function save() {
  localStorage.setItem('splitLongLinesPromptTemplate', promptTemplate.value)
  ElMessage.success('提示词已保存')
  close()
}

function close() {
  uiStore.hideSplitLongLinesAdvancedModal()
}
</script>

<style lang="scss" scoped>
.hint {
  margin-top: 10px;
  color: $text-muted;
  font-size: $font-size-base;
}
</style>
