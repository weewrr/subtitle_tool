<template>
  <el-dialog
    v-model="visible"
    title="转到字幕编号"
    width="350px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form label-width="80px" size="small" @submit.prevent="goToLine">
      <el-form-item label="行号">
        <el-input
          v-model.number="lineNumber"
          type="number"
          :min="1"
          :max="maxLine"
          placeholder="输入行号"
          ref="lineInput"
          @keyup.enter="goToLine"
        />
      </el-form-item>
      <el-form-item>
        <span class="range-info">范围: 1 - {{ maxLine }}</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button type="primary" @click="goToLine">转到</el-button>
      <el-button @click="closeDialog">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { ElMessage } from 'element-plus'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const lineInput = ref(null)
const lineNumber = ref(1)

const visible = computed({
  get: () => uiStore.goToLineDialogVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideGoToLineDialog()
    }
  }
})

const maxLine = computed(() => subtitleStore.paragraphCount)

watch(visible, (val) => {
  if (val) {
    lineNumber.value = 1
    nextTick(() => {
      lineInput.value?.focus()
    })
  }
})

function goToLine() {
  const line = lineNumber.value
  
  if (!Number.isInteger(line) || line < 1 || line > maxLine.value) {
    ElMessage.error(`请输入有效的行号 (1-${maxLine.value})`)
    return
  }
  
  subtitleStore.selectParagraph(line - 1)
  
  if (uiStore.goToLineDialogConfig.onGoTo) {
    uiStore.goToLineDialogConfig.onGoTo(line - 1)
  }
  
  ElMessage.success(`已跳转到第 ${line} 条字幕`)
  closeDialog()
}

function closeDialog() {
  uiStore.hideGoToLineDialog()
}

function handleClose() {
  lineNumber.value = 1
}
</script>

<style lang="scss" scoped>
.range-info {
  color: $text-secondary;
  font-size: $font-size-sm;
}
</style>
