<template>
  <el-dialog
    v-model="visible"
    title="查找重复行"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="duplicate-content">
      <div class="result-info" v-if="duplicates.length > 0">
        找到 {{ duplicates.length }} 组重复行
      </div>
      
      <el-table :data="duplicates" size="small" max-height="400" @row-click="selectDuplicate">
        <el-table-column label="行号" width="100">
          <template #default="{ row }">
            {{ row.lineIndexes.map(i => i + 1).join(', ') }}
          </template>
        </el-table-column>
        <el-table-column label="文本" prop="text" />
        <el-table-column label="次数" width="60">
          <template #default="{ row }">
            {{ row.count }}
          </template>
        </el-table-column>
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
  get: () => uiStore.findDuplicateLinesVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideFindDuplicateLinesDialog()
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
  const textMap = new Map()
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    const normalizedText = normalizeText(p.text)
    
    if (!normalizedText) continue
    
    if (textMap.has(normalizedText)) {
      textMap.get(normalizedText).push(i)
    } else {
      textMap.set(normalizedText, [i])
    }
  }
  
  for (const [text, indexes] of textMap) {
    if (indexes.length > 1) {
      duplicates.value.push({
        text: text.length > 80 ? text.substring(0, 80) + '...' : text,
        fullText: text,
        lineIndexes: indexes,
        count: indexes.length
      })
    }
  }
  
  duplicates.value.sort((a, b) => b.count - a.count)
  
  if (duplicates.value.length === 0) {
    ElMessage.success('未找到重复行')
  }
}

function normalizeText(text) {
  return text
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function selectDuplicate(row) {
  subtitleStore.selectParagraph(row.lineIndexes[0])
}

function closeDialog() {
  uiStore.hideFindDuplicateLinesDialog()
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
