<template>
  <el-dialog
    v-model="visible"
    title="分割长句"
    width="900px"
    :close-on-click-modal="false"
    :close-on-press-escape="!isSplitting || stopRequested"
    :show-close="!isSplitting || stopRequested"
  >
    <div class="split-controls">
      <el-select v-model="engine" style="width: 150px">
        <el-option label="Ollama (local LLM)" value="ollama" />
      </el-select>
      <el-button type="success" @click="toggleSplit" :loading="isSplitting && !stopRequested">
        {{ isSplitting ? '停止' : '智能分割全部' }}
      </el-button>
    </div>

    <div class="split-content">
      <div class="split-panel">
        <div class="panel-title">原始字幕 ({{ originalSubtitles.length }} 条)</div>
        <el-table :data="originalSubtitles" border size="small" max-height="300" highlight-current-row>
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column label="时长" width="80" align="center">
            <template #default="{ row }">
              {{ row.duration?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="text" label="文本" />
        </el-table>
      </div>
      <div class="split-panel">
        <div class="panel-title">分割结果</div>
        <el-table :data="splitResults" border size="small" max-height="300">
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column label="时长" width="80" align="center">
            <template #default="{ row }">
              {{ row.duration?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="text" label="文本" />
        </el-table>
      </div>
    </div>

    <el-divider />

    <el-form label-width="40px" size="small" inline>
      <el-form-item label="Url">
        <el-input v-model="apiUrl" style="width: 280px" placeholder="http://localhost:11434/api/chat/" />
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="modelName" style="width: 160px">
          <el-option label="gpt-oss:120b-cloud" value="gpt-oss:120b-cloud" />
          <el-option label="gpt-oss:20b-cloud" value="gpt-oss:20b-cloud" />
          <el-option label="deepseek-v3.1:671b-cloud" value="deepseek-v3.1:671b-cloud" />
          <el-option label="qwen3-coder:480b-cloud" value="qwen3-coder:480b-cloud" />
          <el-option label="qwen3-vl:235b-cloud" value="qwen3-vl:235b-cloud" />
          <el-option label="minimax-m2:cloud" value="minimax-m2:cloud" />
          <el-option label="glm-4.6:cloud" value="glm-4.6:cloud" />
          <el-option label="gpt-oss:120b" value="gpt-oss:120b" />
          <el-option label="gpt-oss:20b" value="gpt-oss:20b" />
          <el-option label="gemma3:27b" value="gemma3:27b" />
          <el-option label="gemma3:12b" value="gemma3:12b" />
          <el-option label="gemma3:4b" value="gemma3:4b" />
          <el-option label="gemma3:1b" value="gemma3:1b" />
          <el-option label="deepseek-r1:8b" value="deepseek-r1:8b" />
          <el-option label="qwen3-coder:30b" value="qwen3-coder:30b" />
          <el-option label="qwen3-vl:30b" value="qwen3-vl:30b" />
          <el-option label="qwen3-vl:8b" value="qwen3-vl:8b" />
          <el-option label="qwen3-vl:4b" value="qwen3-vl:4b" />
          <el-option label="qwen3:30b" value="qwen3:30b" />
          <el-option label="qwen3:8b" value="qwen3:8b" />
          <el-option label="qwen3:4b" value="qwen3:4b" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="showAdvanced">高级</el-button>
      <el-button type="primary" @click="confirmSplit" :disabled="!hasChanges">确定</el-button>
      <el-button @click="handleCancel">{{ isSplitting ? '停止' : '取消' }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { apiService } from '@/services/ApiService'
import { Paragraph, TimeCode } from '@/models/subtitle'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const visible = computed({
  get: () => uiStore.splitLongLinesModalVisible,
  set: (value) => {
    if (!value && isSplitting.value && !stopRequested.value) {
      stopRequested.value = true
      return
    }
    value ? uiStore.showSplitLongLinesModal() : uiStore.hideSplitLongLinesModal()
  }
})

const engine = ref('ollama')
const apiUrl = ref('http://localhost:11434/api/chat/')
const modelName = ref('gemma3:1b')
const isSplitting = ref(false)
const stopRequested = ref(false)
const originalSubtitles = ref([])
const splitResults = ref([])
const hasChanges = ref(false)

watch(visible, (val) => {
  if (val) {
    originalSubtitles.value = subtitleStore.currentSubtitle.paragraphs.map(p => ({
      id: p.id,
      number: p.number,
      startTime: p.startTime,
      endTime: p.endTime,
      duration: p.duration,
      text: p.text,
      translation: p.translation || ''
    }))
    splitResults.value = []
    hasChanges.value = false
  }
})

function toggleSplit() {
  if (isSplitting.value) {
    stopRequested.value = true
    return
  }
  splitAll()
}

async function splitAll() {
  if (originalSubtitles.value.length === 0) {
    ElMessage.warning('没有可处理的字幕')
    return
  }

  isSplitting.value = true
  stopRequested.value = false
  let successCount = 0
  const newResults = []

  try {
    for (const item of originalSubtitles.value) {
      if (stopRequested.value) {
        ElMessage.info('分割已停止')
        break
      }

      const result = await apiService.translate({
        text: item.text,
        task: 'split',
        engine: engine.value,
        model: modelName.value
      })

      if (stopRequested.value) break

      if (result.error) {
        ElMessage.error('分割失败: ' + result.error)
        newResults.push({
          originalNumber: item.number,
          startTime: item.startTime,
          endTime: item.endTime,
          duration: item.duration,
          text: item.text
        })
      } else {
        const responseText = result.translated || result.text || ''
        const splitItems = parseSplitResult(responseText)
        
        if (splitItems.length > 1) {
          const duration = item.endTime.totalMilliseconds - item.startTime.totalMilliseconds
          const totalWeight = splitItems.reduce((sum, s) => sum + s.weight, 0)
          let currentTime = item.startTime.totalMilliseconds

          splitItems.forEach((splitItem, idx) => {
            const segmentDuration = (splitItem.weight / totalWeight) * duration
            const isLast = idx === splitItems.length - 1
            
            newResults.push({
              originalNumber: item.number,
              startTime: new TimeCode(currentTime),
              endTime: new TimeCode(isLast ? item.endTime.totalMilliseconds : currentTime + segmentDuration),
              duration: new TimeCode(segmentDuration),
              text: splitItem.message.trim()
            })
            currentTime += segmentDuration
          })
          successCount++
        } else {
          newResults.push({
            originalNumber: item.number,
            startTime: item.startTime,
            endTime: item.endTime,
            duration: item.duration,
            text: splitItems[0].message.trim()
          })
        }
      }
      
      newResults.forEach((r, index) => {
        r.number = index + 1
      })
      splitResults.value = [...newResults]
    }

    hasChanges.value = successCount > 0

    if (!stopRequested.value && successCount > 0) {
      ElMessage.success('成功分割 ' + successCount + ' 条长句')
    } else if (!stopRequested.value) {
      ElMessage.info('没有需要分割的内容')
    }
  } catch (error) {
    ElMessage.error('分割失败: ' + error.message)
  } finally {
    isSplitting.value = false
    stopRequested.value = false
  }
}

function parseSplitResult(text) {
  try {
    const jsonMatch = text.match(/\[[\s\S]*\]/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0])
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed.map(item => ({
          message: item.message || item.text || '',
          weight: Math.max(1, Math.min(10, parseInt(item.weight) || 5))
        }))
      }
    }
  } catch (e) {
    console.warn('Failed to parse JSON split result:', e)
  }
  
  const lines = text.split(/\n+/).map(l => l.trim()).filter(l => l)
  if (lines.length > 1) {
    return lines.map(l => ({ message: l, weight: 5 }))
  }
  const sentences = text.split(/[。！？.!?]+/).map(s => s.trim()).filter(s => s.length > 0)
  if (sentences.length > 1) {
    return sentences.map(s => ({ message: s, weight: 5 }))
  }
  return [{ message: text, weight: 5 }]
}

function confirmSplit() {
  if (!hasChanges.value || splitResults.value.length === 0) {
    ElMessage.warning('没有需要保存的更改')
    return
  }

  subtitleStore.applySplitResults(splitResults.value)

  ElMessage.success('分割已保存')
  close()
}

function close() {
  uiStore.hideSplitLongLinesModal()
}

function handleCancel() {
  if (isSplitting.value) {
    stopRequested.value = true
  } else {
    close()
  }
}

function showAdvanced() {
  uiStore.showSplitLongLinesAdvancedModal()
}
</script>

<style lang="scss" scoped>
.split-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.split-content {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;

  .split-panel {
    flex: 1;
    overflow: hidden;
  }

  .panel-title {
    font-weight: bold;
    margin-bottom: 8px;
    color: #606266;
  }
}
</style>
