<template>
  <el-dialog
    v-model="visible"
    title="导出字幕"
    width="460px"
    :close-on-click-modal="true"
  >
    <div class="export-dialog">
      <div class="field">
        <div class="field-label">导出格式</div>
        <div class="format-grid" role="radiogroup" aria-label="导出格式">
          <button
            v-for="f in formats"
            :key="f.value"
            type="button"
            class="format-card"
            :class="{ active: format === f.value }"
            role="radio"
            :aria-checked="format === f.value"
            @click="format = f.value"
          >
            <span class="format-ext mono">{{ f.value.toUpperCase() }}</span>
            <span class="format-desc">{{ f.label }}</span>
          </button>
        </div>
      </div>

      <div class="field">
        <div class="field-label">字幕内容</div>
        <el-radio-group v-model="useTranslation">
          <el-radio :value="false">原始文本</el-radio>
          <el-radio :value="true" :disabled="!subtitleStore.hasTranslation">翻译文本</el-radio>
        </el-radio-group>
      </div>

      <div class="file-preview">
        <el-icon :size="14"><Document /></el-icon>
        <span class="mono">{{ previewName }}</span>
      </div>

      <p class="hint">导出为 {{ formatName }} 格式;需要完整工作区(含翻译/媒体引用)请使用"保存项目"。</p>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="exporting" @click="doExport">导出</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useAppActions } from '@/composables/useAppActions'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()
const { exportAs } = useAppActions()

const visible = computed({
  get: () => uiStore.exportDialogVisible,
  set: (value) => value ? uiStore.showExportDialog() : uiStore.hideExportDialog()
})

const formats = [
  { value: 'srt', label: '通用字幕,兼容性最好' },
  { value: 'vtt', label: '网页视频(HTML5)标准' },
  { value: 'ass', label: '高级样式与特效' },
  { value: 'txt', label: '带时间码纯文本' }
]

const format = ref('srt')
const useTranslation = ref(false)
const exporting = ref(false)

const formatName = computed(() => formats.find(f => f.value === format.value)?.label || format.value)

const previewName = computed(() => {
  const base = (subtitleStore.currentSubtitle.fileName || 'Untitled').replace(/\.[^/.]+$/, '')
  const suffix = useTranslation.value ? '_translated' : ''
  return `${base}${suffix}.${format.value}`
})

async function doExport() {
  exporting.value = true
  try {
    await exportAs(format.value, useTranslation.value)
    uiStore.hideExportDialog()
  } finally {
    exporting.value = false
  }
}
</script>

<style lang="scss" scoped>
.export-dialog {
  display: flex;
  flex-direction: column;
  gap: 18px;

  .field-label {
    font-size: $font-size-sm;
    font-weight: 600;
    color: var(--app-text-secondary);
    margin-bottom: 8px;
  }

  .format-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .format-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 10px 12px;
    border: 1.5px solid var(--app-border);
    border-radius: $border-radius;
    background: var(--app-surface);
    cursor: pointer;
    text-align: left;
    transition: border-color $transition-fast, background-color $transition-fast;

    &:hover {
      border-color: var(--app-border-strong);
    }

    &.active {
      border-color: var(--app-primary);
      background: var(--app-primary-subtle);
    }

    .format-ext {
      font-size: $font-size-lg;
      font-weight: 700;
      color: var(--app-text-primary);
    }

    .format-desc {
      font-size: $font-size-sm;
      color: var(--app-text-muted);
    }
  }

  .file-preview {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px dashed var(--app-border);
    border-radius: $border-radius;
    color: var(--app-text-secondary);
    font-size: $font-size-base;
    background: var(--app-surface-muted);
  }

  .hint {
    font-size: $font-size-sm;
    color: var(--app-text-muted);
    line-height: 1.5;
  }
}
</style>
