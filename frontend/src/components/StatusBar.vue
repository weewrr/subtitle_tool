<template>
  <div class="status-bar">
    已选择 {{ selectedCount }} 行/{{ totalCount }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'

const subtitleStore = useSubtitleStore()

const selectedCount = computed(() => 
  subtitleStore.selectedParagraphIndex >= 0 ? 1 : 0
)

const totalCount = computed(() => subtitleStore.paragraphCount)
</script>

<style lang="scss" scoped>
.status-bar {
  background: $glass-bg;
  backdrop-filter: $glass-blur;
  -webkit-backdrop-filter: $glass-blur;
  border: 1px solid $glass-border;
  border-radius: $border-radius;
  box-shadow: $glass-shadow;
  padding: 4px 8px;
  font-size: $font-size-base;
  text-align: right;
  color: $text-color;
}
</style>
