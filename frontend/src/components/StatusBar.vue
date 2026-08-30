<template>
  <footer class="status-bar">
    <div class="status-group">
      <span class="status-item">
        <span class="status-dot" :class="hasSubtitle ? 'on' : 'off'"></span>
        {{ subtitleStore.currentSubtitle.fileName || '未打开字幕' }}
      </span>
      <span v-if="hasSubtitle" class="status-item">共 {{ totalCount }} 行</span>
      <span v-if="selectedCount > 0" class="status-item highlight">
        已选第 {{ subtitleStore.selectedParagraphIndex + 1 }} 行
      </span>
    </div>
    <div class="status-group">
      <span class="status-item">
        <el-icon :size="12"><VideoCamera /></el-icon>
        {{ subtitleStore.videoFile ? '视频已加载' : '无视频' }}
      </span>
      <span class="status-item">
        <el-icon :size="12"><Headset /></el-icon>
        {{ subtitleStore.dubbingAudioFile ? '配音已就绪' : '无配音' }}
      </span>
      <span v-if="hasTranslation" class="status-item highlight">含翻译</span>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'

const subtitleStore = useSubtitleStore()

const selectedCount = computed(() =>
  subtitleStore.selectedParagraphIndex >= 0 ? 1 : 0
)

const totalCount = computed(() => subtitleStore.paragraphCount)
const hasSubtitle = computed(() => subtitleStore.paragraphCount > 0)
const hasTranslation = computed(() => subtitleStore.hasTranslation)
</script>

<style lang="scss" scoped>
.status-bar {
  flex-shrink: 0;
  height: 26px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--app-surface-muted);
  border-top: 1px solid var(--app-border);
  font-size: $font-size-sm;
  color: var(--app-text-muted);
  user-select: none;

  .status-group {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }

  .status-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;

    .el-icon {
      color: var(--app-text-muted);
    }

    &.highlight {
      color: var(--app-primary);
      font-weight: 600;
    }
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;

    &.on {
      background: var(--app-success);
    }

    &.off {
      background: var(--app-border-strong);
    }
  }
}
</style>
