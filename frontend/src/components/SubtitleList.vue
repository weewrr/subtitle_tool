<template>
  <div class="subtitle-list">
    <el-table
      ref="tableRef"
      :data="subtitleStore.currentSubtitle.paragraphs"
      highlight-current-row
      @current-change="handleCurrentChange"
      @row-dblclick="handleRowDblClick"
      :height="'100%'"
      border
      size="small"
    >
      <el-table-column prop="number" label="编号" width="60" align="center" />
      <el-table-column label="起始时间" width="120" align="center">
        <template #default="{ row }">
          {{ row.startTime.toDisplayString() }}
        </template>
      </el-table-column>
      <el-table-column label="结束时间" width="120" align="center">
        <template #default="{ row }">
          {{ row.endTime.toDisplayString() }}
        </template>
      </el-table-column>
      <el-table-column label="时长" width="100" align="center">
        <template #default="{ row }">
          {{ row.duration.toDisplayString() }}
        </template>
      </el-table-column>
      <el-table-column prop="text" label="文本" min-width="200" show-overflow-tooltip v-if="!subtitleStore.showTranslation" />
      <el-table-column prop="translation" label="翻译" min-width="200" show-overflow-tooltip v-if="subtitleStore.showTranslation" />
      <template #empty>
        <div class="empty-placeholder" @click="openSubtitleFile">
          <el-icon :size="32"><FolderOpened /></el-icon>
          <span>点击打开字幕文件</span>
        </div>
      </template>
    </el-table>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'

const subtitleStore = useSubtitleStore()
const tableRef = ref(null)

function handleCurrentChange(row) {
  if (row) {
    subtitleStore.selectParagraph(row.number - 1)
  }
}

function handleRowDblClick(row) {
  subtitleStore.selectParagraph(row.number - 1)
}

function openSubtitleFile() {
  document.querySelector('input[type="file"][accept=".srt,.vtt,.sub,.ass,.ssa"]')?.click()
}

watch(() => subtitleStore.selectedParagraphIndex, async (newIndex) => {
  if (newIndex >= 0 && tableRef.value) {
    const row = subtitleStore.currentSubtitle.paragraphs[newIndex]
    if (row) {
      tableRef.value.setCurrentRow(row)
    }
    await nextTick()
    const rows = document.querySelectorAll('.el-table__body-wrapper tbody tr')
    if (rows[newIndex]) {
      rows[newIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }
})
</script>

<style lang="scss" scoped>
.subtitle-list {
  flex: 1;
  border: 1px solid $glass-border;
  overflow: hidden;
  background: $glass-bg;
  backdrop-filter: $glass-blur;
  -webkit-backdrop-filter: $glass-blur;
  border-radius: $border-radius;
  box-shadow: $glass-shadow;

  :deep(.el-table) {
    font-size: $font-size-base;
    background: transparent !important;
    --el-table-bg-color: transparent !important;
    --el-table-tr-bg-color: transparent !important;
    --el-table-header-bg-color: rgba(255, 255, 255, 0.1) !important;
    --el-table-row-hover-bg-color: $hover-bg !important;
    --el-table-current-row-bg-color: $selected-bg !important;
    --el-table-border-color: rgba(255, 255, 255, 0.1) !important;
    --el-table-text-color: $text-color !important;
    --el-table-header-text-color: $text-color !important;
    
    &::before {
      display: none;
    }
    
    .el-table__inner-wrapper {
      background: transparent !important;
    }
    
    .el-table__header-wrapper {
      background: rgba(255, 255, 255, 0.1) !important;
    }
    
    th {
      background: rgba(255, 255, 255, 0.1) !important;
      font-weight: normal;
      color: $text-color !important;
      border-bottom: 1px solid $glass-border !important;
    }

    td {
      background: transparent !important;
      color: $text-color !important;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    .el-table__body-wrapper {
      background: transparent !important;
    }
    
    .el-table__empty-text {
      color: $text-muted !important;
    }

    .el-table__body tr.current-row > td {
      background: $selected-bg !important;
      color: $text-color !important;
    }

    .el-table__body tr:hover > td {
      background: $hover-bg !important;
      color: $text-color !important;
    }
    
    .el-table__empty-block {
      background: transparent !important;
    }
  }

  .empty-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px;
    cursor: pointer;
    color: $text-muted;
    transition: all 0.3s ease;

    &:hover {
      color: $text-color;
      transform: scale(1.05);
    }
  }
}
</style>
