<template>
  <el-dialog
    v-model="visible"
    :title="config.title"
    width="400px"
    :close-on-click-modal="false"
  >
    <p class="message">{{ config.message }}</p>

    <template #footer>
      <el-button type="primary" @click="handleConfirm">覆盖</el-button>
      <el-button @click="handleCancel">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useUIStore } from '@/stores/uiStore'

const uiStore = useUIStore()

const visible = computed({
  get: () => uiStore.confirmDialogVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideConfirmDialog()
    }
  }
})

const config = computed(() => uiStore.confirmDialogConfig)

function handleConfirm() {
  if (config.value.onConfirm) {
    config.value.onConfirm()
  }
  uiStore.hideConfirmDialog()
}

function handleCancel() {
  if (config.value.onCancel) {
    config.value.onCancel()
  }
  uiStore.hideConfirmDialog()
}
</script>

<style lang="scss" scoped>
.message {
  text-align: center;
  font-size: $font-size-lg;
}
</style>
