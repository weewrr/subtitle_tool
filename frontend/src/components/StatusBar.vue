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
  background-color: $bg-color;
  padding: 4px 8px;
  border-top: 1px solid $border-color;
  font-size: $font-size-base;
  text-align: right;
}
</style>
