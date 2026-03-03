<template>
  <el-dialog
    v-model="visible"
    title="查找重复词"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="duplicate-content">
      <div class="result-info" v-if="duplicates.length > 0">
        找到 {{ duplicates.length }} 处重复词
      </div>
      
      <el-table :data="duplicates" size="small" max-height="400" @row-click="selectDuplicate">
        <el-table-column label="行号" width="70">
          <template #default="{ row }">
            {{ row.lineIndex + 1 }}
          </template>
        </el-table-column>
        <el-table-column label="重复词" width="150" prop="word" />
        <el-table-column label="上下文" prop="context" />
      </el-table>
    </div>

    <template #footer>
      <el-button @click="findDuplicates" :disabled="!hasSubtitle">重新查找</el-button>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { ElMessage } from 'element-plus'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const duplicates = ref([])

const visible = computed({
  get: () => uiStore.findDuplicateWordsVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideFindDuplicateWordsDialog()
    }
  }
})

const hasSubtitle = computed(() => subtitleStore.paragraphCount > 0)

watch(visible, (val) => {
  if (val) {
    findDuplicates()
  }
})

function findDuplicates() {
  duplicates.value = []
  
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  const regex = /\b(\w+)\s+\1\b/gi
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    let match
    
    regex.lastIndex = 0
    while ((match = regex.exec(p.text)) !== null) {
      duplicates.value.push({
        lineIndex: i,
        word: match[1],
        fullMatch: match[0],
        index: match.index,
        context: getContext(p.text, match.index, match[0].length)
      })
    }
  }
  
  if (duplicates.value.length === 0) {
    ElMessage.success('未找到重复词')
  }
}

function getContext(text, index, length) {
  const start = Math.max(0, index - 30)
  const end = Math.min(text.length, index + length + 30)
  let context = text.substring(start, end)
  if (start > 0) context = '...' + context
  if (end < text.length) context = context + '...'
  return context
}

function selectDuplicate(row) {
  subtitleStore.selectParagraph(row.lineIndex)
}

function closeDialog() {
  uiStore.hideFindDuplicateWordsDialog()
}

function handleClose() {
  duplicates.value = []
}
</script>

<style lang="scss" scoped>
.duplicate-content {
  .result-info {
    margin-bottom: 12px;
    padding: 8px;
    background-color: $bg-color;
    border-radius: 4px;
    font-size: $font-size-sm;
  }
}
</style>
