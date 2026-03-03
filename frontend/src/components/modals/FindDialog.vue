<template>
  <el-dialog
    v-model="visible"
    title="查找"
    width="450px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form label-width="80px" size="small">
      <el-form-item label="查找内容">
        <el-input
          v-model="searchText"
          placeholder="输入要查找的内容"
          @keyup.enter="findNext"
          ref="searchInput"
        />
      </el-form-item>
      <el-form-item label="查找类型">
        <el-radio-group v-model="findType">
          <el-radio value="normal">普通</el-radio>
          <el-radio value="caseSensitive">区分大小写</el-radio>
          <el-radio value="regex">正则表达式</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="选项">
        <el-checkbox v-model="wholeWord">全字匹配</el-checkbox>
      </el-form-item>
      <el-form-item label="搜索范围">
        <el-checkbox v-model="searchOriginal">原始文本</el-checkbox>
        <el-checkbox v-model="searchTranslation">翻译文本</el-checkbox>
      </el-form-item>
    </el-form>

    <div v-if="resultInfo" class="result-info">
      {{ resultInfo }}
    </div>

    <template #footer>
      <el-button @click="findNext" :disabled="!searchText">查找下一个</el-button>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { ElMessage } from 'element-plus'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const searchInput = ref(null)
const searchText = ref('')
const findType = ref('normal')
const wholeWord = ref(false)
const searchOriginal = ref(true)
const searchTranslation = ref(true)
const resultInfo = ref('')
const lastIndex = ref(-1)
const lastPosition = ref(-1)

const visible = computed({
  get: () => uiStore.findDialogVisible,
  set: (value) => {
    if (!value) {
      uiStore.hideFindDialog()
    }
  }
})

watch(visible, (val) => {
  if (val) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

function buildSearchRegex() {
  let pattern = searchText.value
  let flags = 'g'
  
  if (findType.value === 'normal') {
    pattern = escapeRegex(pattern)
    flags += 'i'
  } else if (findType.value === 'caseSensitive') {
    pattern = escapeRegex(pattern)
  }
  
  if (wholeWord.value && findType.value !== 'regex') {
    pattern = `\\b${pattern}\\b`
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

function findNext() {
  if (!searchText.value) return
  
  const regex = buildSearchRegex()
  if (!regex) {
    ElMessage.error('无效的正则表达式')
    return
  }
  
  const paragraphs = subtitleStore.currentSubtitle.paragraphs
  if (paragraphs.length === 0) {
    ElMessage.info('没有可搜索的字幕')
    return
  }
  
  let found = false
  let startIndex = lastIndex.value < 0 ? 0 : lastIndex.value
  
  for (let i = 0; i < paragraphs.length; i++) {
    const idx = (startIndex + i) % paragraphs.length
    const p = paragraphs[idx]
    
    let textToSearch = ''
    if (searchOriginal.value) {
      textToSearch += p.text + ' '
    }
    if (searchTranslation.value && p.translation) {
      textToSearch += p.translation
    }
    
    regex.lastIndex = 0
    const match = regex.exec(textToSearch)
    
    if (match) {
      subtitleStore.selectParagraph(idx)
      lastIndex.value = idx
      resultInfo.value = `找到第 ${idx + 1} 条字幕: "${match[0]}"`
      found = true
      
      if (uiStore.findDialogConfig.onFind) {
        uiStore.findDialogConfig.onFind({ index: idx, match: match[0] })
      }
      break
    }
    
    if (i === 0) {
      startIndex = 0
    }
  }
  
  if (!found) {
    ElMessage.info('未找到匹配内容')
    lastIndex.value = -1
  }
}

function closeDialog() {
  uiStore.hideFindDialog()
}

function handleClose() {
  resultInfo.value = ''
  lastIndex.value = -1
}
</script>

<style lang="scss" scoped>
.result-info {
  margin-top: 12px;
  padding: 8px;
  background-color: $bg-color;
  border-radius: 4px;
  font-size: $font-size-sm;
}

:deep(.el-checkbox) {
  margin-right: 16px;
}
</style>
