<template>
  <el-dialog
    v-model="visible"
    title="多重替换"
    width="700px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="multi-replace-content">
      <div class="rules-section">
        <div class="rules-header">
          <span>替换规则</span>
          <el-button size="small" @click="addRule">添加规则</el-button>
        </div>
        <el-table :data="rules" size="small" max-height="300">
          <el-table-column width="50">
            <template #default="{ $index }">
              <el-checkbox v-model="rules[$index].enabled" />
            </template>
          </el-table-column>
          <el-table-column label="查找内容" prop="find">
            <template #default="{ row }">
              <el-input v-model="row.find" size="small" placeholder="查找" />
            </template>
          </el-table-column>
          <el-table-column label="替换为" prop="replace">
            <template #default="{ row }">
              <el-input v-model="row.replace" size="small" placeholder="替换" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-select v-model="row.type" size="small">
                <el-option label="普通" value="normal" />
                <el-option label="区分大小写" value="caseSensitive" />
                <el-option label="正则表达式" value="regex" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column width="60">
            <template #default="{ $index }">
              <el-button size="small" type="danger" @click="removeRule($index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="preview-section">
        <div class="preview-header">
          <span>预览</span>
          <el-button size="small" @click="generatePreview">生成预览</el-button>
        </div>
        <el-table :data="previewResults" size="small" max-height="200">
          <el-table-column label="行号" width="70" prop="line" />
          <el-table-column label="原文" prop="original" />
          <el-table-column label="替换后" prop="replaced" />
        </el-table>
      </div>
    </div>

    <template #footer>
      <el-button type="primary" @click="applyAll" :disabled="rules.length === 0">应用全部替换</el-button>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { ElMessage } from 'element-plus'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const rules = ref([
  { enabled: true, find: '', replace: '', type: 'normal' }
])
const previewResults = ref([])

const visible = computed({
  get: () => uiStore.multiReplaceDialogVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideMultiReplaceDialog()
    }
  }
})

function addRule() {
  rules.value.push({ enabled: true, find: '', replace: '', type: 'normal' })
}

function removeRule(index) {
  rules.value.splice(index, 1)
}

function buildRegex(rule) {
  let pattern = rule.find
  let flags = 'g'
  
  if (rule.type === 'normal') {
    pattern = escapeRegex(pattern)
    flags += 'i'
  } else if (rule.type === 'caseSensitive') {
    pattern = escapeRegex(pattern)
  }
  
  try {
    return new RegExp(pattern, flags)
  } catch (e) {
    return null
  }
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function applyRulesToText(text) {
  let result = text
  for (const rule of rules.value) {
    if (!rule.enabled || !rule.find) continue
    
    const regex = buildRegex(rule)
    if (!regex) continue
    
    if (rule.type === 'regex') {
      const re = new RegExp(rule.find, 'g')
      result = result.replace(re, rule.replace)
    } else {
      result = result.replace(regex, rule.replace)
    }
  }
  return result
}

function generatePreview() {
  previewResults.value = []
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    const original = p.text
    const replaced = applyRulesToText(original)
    
    if (original !== replaced) {
      previewResults.value.push({
        line: i + 1,
        original: original.length > 50 ? original.substring(0, 50) + '...' : original,
        replaced: replaced.length > 50 ? replaced.substring(0, 50) + '...' : replaced
      })
    }
  }
  
  if (previewResults.value.length === 0) {
    ElMessage.info('没有匹配的内容')
  }
}

function applyAll() {
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  let count = 0
  
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    const original = p.text
    const replaced = applyRulesToText(original)
    
    if (original !== replaced) {
      subtitleStore.updateParagraphText(i, replaced)
      count++
    }
  }
  
  ElMessage.success(`已替换 ${count} 条字幕`)
  previewResults.value = []
}

function closeDialog() {
  uiStore.hideMultiReplaceDialog()
}

function handleClose() {
  previewResults.value = []
}
</script>

<style lang="scss" scoped>
.multi-replace-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rules-section,
.preview-section {
  .rules-header,
  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-weight: bold;
  }
}

:deep(.el-table) {
  .el-input,
  .el-select {
    width: 100%;
  }
}
</style>
