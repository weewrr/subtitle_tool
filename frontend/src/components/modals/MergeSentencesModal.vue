<template>
  <el-dialog
    v-model="visible"
    title="合并句子"
    width="800px"
    :close-on-click-modal="false"
  >
    <div class="merge-tips">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          点击行可选中/取消选中，选择连续的字幕后点击"合并选中"，最后点击"确定"保存
        </template>
      </el-alert>
    </div>

    <el-table
      ref="tableRef"
      :data="subtitles"
      border
      size="small"
      max-height="400"
      highlight-current-row
      @row-click="handleRowClick"
      :row-class-name="getRowClassName"
    >
      <el-table-column prop="number" label="编号" width="60" align="center" />
      <el-table-column label="起始时间" width="100" align="center">
        <template #default="{ row }">
          {{ row.startTime?.toDisplayString?.() || '' }}
        </template>
      </el-table-column>
      <el-table-column label="结束时间" width="100" align="center">
        <template #default="{ row }">
          {{ row.endTime?.toDisplayString?.() || '' }}
        </template>
      </el-table-column>
      <el-table-column label="时长" width="80" align="center">
        <template #default="{ row }">
          {{ row.duration?.toDisplayString?.() || '' }}
        </template>
      </el-table-column>
      <el-table-column prop="text" label="文本" min-width="300" />
    </el-table>

    <div class="merge-preview" v-if="selectedRows.length > 1">
      <el-divider content-position="left">合并预览</el-divider>
      <div class="preview-content">
        <div class="preview-item">
          <span class="preview-label">编号:</span>
          <span>{{ previewData.number }}</span>
        </div>
        <div class="preview-item">
          <span class="preview-label">时间:</span>
          <span>{{ previewData.startTime }} --> {{ previewData.endTime }}</span>
        </div>
        <div class="preview-item">
          <span class="preview-label">文本:</span>
          <span>{{ previewData.text }}</span>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="mergeSelected" :disabled="selectedRows.length < 2">
        合并选中
      </el-button>
      <el-button type="primary" @click="confirmMerge" :disabled="!hasChanges">
        确定
      </el-button>
      <el-button @click="close">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { Paragraph, TimeCode } from '@/models/subtitle'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const tableRef = ref(null)
const selectedIds = ref([])
const subtitles = ref([])
const hasChanges = ref(false)

const visible = computed({
  get: () => uiStore.mergeSentencesModalVisible,
  set: (value) => value ? uiStore.showMergeSentencesModal() : uiStore.hideMergeSentencesModal()
})

const selectedRows = computed(() => {
  return subtitles.value.filter(item => selectedIds.value.includes(item.id))
})

const previewData = computed(() => {
  if (selectedRows.value.length < 2) {
    return { number: '', startTime: '', endTime: '', text: '' }
  }

  const sortedRows = [...selectedRows.value].sort((a, b) => a.number - b.number)
  const first = sortedRows[0]
  const last = sortedRows[sortedRows.length - 1]

  return {
    number: `${first.number}-${last.number}`,
    startTime: first.startTime?.toDisplayString?.() || '',
    endTime: last.endTime?.toDisplayString?.() || '',
    text: sortedRows.map(r => r.text).join(' ')
  }
})

watch(visible, (val) => {
  if (val) {
    subtitles.value = subtitleStore.currentSubtitle.paragraphs.map(p => ({
      id: p.id,
      number: p.number,
      startTime: p.startTime,
      endTime: p.endTime,
      duration: p.duration,
      text: p.text,
      translation: p.translation || ''
    }))
    selectedIds.value = []
    hasChanges.value = false
  }
})

function handleRowClick(row) {
  const index = selectedIds.value.indexOf(row.id)
  if (index > -1) {
    selectedIds.value.splice(index, 1)
  } else {
    selectedIds.value.push(row.id)
  }
}

function getRowClassName({ row }) {
  return selectedIds.value.includes(row.id) ? 'selected-row' : ''
}

function mergeSelected() {
  if (selectedRows.value.length < 2) {
    ElMessage.warning('请至少选择两行字幕进行合并')
    return
  }

  const sortedRows = [...selectedRows.value].sort((a, b) => a.number - b.number)

  for (let i = 1; i < sortedRows.length; i++) {
    if (sortedRows[i].number !== sortedRows[i - 1].number + 1) {
      ElMessage.warning('只能合并连续的字幕行')
      return
    }
  }

  const firstIndex = sortedRows[0].number - 1
  const lastIndex = sortedRows[sortedRows.length - 1].number - 1

  const firstParagraph = subtitles.value[firstIndex]
  const lastParagraph = subtitles.value[lastIndex]

  const mergedText = sortedRows.map(r => r.text).join(' ')
  const mergedTranslation = sortedRows.map(r => r.translation).filter(t => t).join(' ')

  const mergedItem = {
    id: firstParagraph.id,
    number: firstParagraph.number,
    startTime: firstParagraph.startTime,
    endTime: lastParagraph.endTime,
    duration: new TimeCode(lastParagraph.endTime.totalMilliseconds - firstParagraph.startTime.totalMilliseconds),
    text: mergedText,
    translation: mergedTranslation
  }

  subtitles.value.splice(firstIndex, lastIndex - firstIndex + 1, mergedItem)

  subtitles.value.forEach((item, index) => {
    item.number = index + 1
  })

  hasChanges.value = true
  selectedIds.value = []

  ElMessage.success(`已合并 ${sortedRows.length} 行字幕，点击"确定"保存`)
}

function confirmMerge() {
  if (!hasChanges.value) {
    ElMessage.warning('没有需要保存的更改')
    return
  }

  subtitleStore.applyMergedSubtitles(subtitles.value)

  ElMessage.success('合并已保存')
  close()
}

function close() {
  uiStore.hideMergeSentencesModal()
}
</script>

<style lang="scss" scoped>
.merge-tips {
  margin-bottom: 12px;
}

.merge-preview {
  margin-top: 12px;

  .preview-content {
    background-color: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
  }

  .preview-item {
    margin-bottom: 8px;
    display: flex;
    align-items: flex-start;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .preview-label {
    font-weight: bold;
    min-width: 50px;
    color: #606266;
  }
}

:deep(.selected-row) {
  background-color: #ecf5ff !important;

  td {
    background-color: #ecf5ff !important;
  }
}
</style>
