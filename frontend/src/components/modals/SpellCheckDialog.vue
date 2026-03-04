<template>
  <el-dialog
    v-model="visible"
    title="拼写检查"
    width="900px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="!isChecking"
    :before-close="handleBeforeClose"
  >
    <div class="spell-controls">
      <el-select v-model="engine" style="width: 150px" :disabled="isChecking">
        <el-option label="Ollama (local LLM)" value="ollama" />
      </el-select>
      <el-button 
        v-if="!isChecking"
        type="success" 
        @click="startCheck"
      >
        智能检查全部
      </el-button>
      <el-button 
        v-else
        type="danger" 
        @click="stopCheck"
        :loading="stopRequested"
      >
        {{ stopRequested ? '停止中...' : '停止检查' }}
      </el-button>
      <span v-if="isChecking" class="checking-status">
        正在检查: {{ checkResults.length }} / {{ originalSubtitles.length }}
      </span>
      <el-button 
        type="primary" 
        plain
        @click="showAdvancedModal"
        :disabled="isChecking"
      >
        高级
      </el-button>
    </div>

    <div class="spell-content">
      <div class="spell-panel">
        <div class="panel-title">原始字幕 ({{ originalSubtitles.length }} 条)</div>
        <el-table :data="originalSubtitles" border size="small" max-height="300" highlight-current-row>
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="text" label="文本" />
        </el-table>
      </div>
      <div class="spell-panel">
        <div class="panel-title">检查结果</div>
        <el-table :data="checkResults" border size="small" max-height="300">
          <el-table-column prop="number" label="编号" width="60" align="center" />
          <el-table-column label="起始时间" width="100" align="center">
            <template #default="{ row }">
              {{ row.startTime?.toDisplayString?.() || '' }}
            </template>
          </el-table-column>
          <el-table-column prop="text" label="文本" />
          <el-table-column label="修改" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.hasChanges" type="warning" size="small">已修改</el-tag>
              <el-tag v-else type="success" size="small">无错误</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-divider />

    <el-form label-width="40px" size="small" inline>
      <el-form-item label="Url">
        <el-input v-model="apiUrl" style="width: 280px" placeholder="http://localhost:11434/api/chat/" :disabled="isChecking" />
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="modelName" style="width: 160px" :disabled="isChecking">
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
      <el-button type="primary" @click="confirmChanges" :disabled="!hasChanges || isChecking">确定</el-button>
      <el-button @click="handleCancel">{{ isChecking ? '停止并关闭' : '取消' }}</el-button>
    </template>
  </el-dialog>

  <SpellCheckAdvancedModal />
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUIStore } from '@/stores/uiStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { apiService } from '@/services/ApiService'
import { Paragraph, TimeCode } from '@/models/subtitle'
import SpellCheckAdvancedModal from './SpellCheckAdvancedModal.vue'

const uiStore = useUIStore()
const subtitleStore = useSubtitleStore()

const visible = computed({
    get: () => uiStore.spellCheckDialogVisible,
    set: (value) => {
        if (!value && isChecking.value && !stopRequested.value) {
            ElMessage.warning('请先停止检查再关闭')
            return
        }
        value ? uiStore.showSpellCheckDialog() : uiStore.hideSpellCheckDialog()
    }
})

const DEFAULT_PROMPT = `Check the spelling of the following subtitle text and correct any errors.

IMPORTANT RULES:
1. Fix ONLY actual spelling errors - do NOT change correct words
2. Preserve the original text structure and formatting
3. Keep proper nouns and names unchanged (people, places, brands, technical terms)
4. For each correction, provide the original word and the corrected word
5. If no errors found, return empty corrections array

Output ONLY a valid JSON object:
{
  "corrected_text": "the corrected full text",
  "corrections": [
    {
      "original": "misspelled word",
      "corrected": "corrected word"
    }
  ]
}

Text to check:
{text}`

const engine = ref('ollama')
const apiUrl = ref('http://localhost:11434/api/chat/')
const modelName = ref('gemma3:1b')
const isChecking = ref(false)
const stopRequested = ref(false)
const originalSubtitles = ref([])
const checkResults = ref([])
const hasChanges = ref(false)

watch(visible, (val) => {
    if (val) {
        originalSubtitles.value = subtitleStore.currentSubtitle.paragraphs.map(p => ({
            id: p.id,
            number: p.number,
            startTime: p.startTime,
            endTime: p.endTime,
            text: p.text,
            translation: p.translation || ''
        }))
        checkResults.value = []
        hasChanges.value = false
        stopRequested.value = false
    }
})

function handleBeforeClose(done) {
    if (isChecking.value && !stopRequested.value) {
        ElMessage.warning('请先停止检查再关闭')
        return
    }
    done()
}

function startCheck() {
    checkAll()
}

function stopCheck() {
    stopRequested.value = true
    ElMessage.info('正在停止检查...')
}

function showAdvancedModal() {
    uiStore.showSpellCheckAdvancedModal()
}

function getPromptTemplate() {
    const saved = localStorage.getItem('spellCheckPromptTemplate')
    return saved || DEFAULT_PROMPT
}

async function checkAll() {
    if (originalSubtitles.value.length === 0) {
        ElMessage.warning('没有可处理的字幕')
        return
    }

    isChecking.value = true
    stopRequested.value = false
    let changeCount = 0
    const newResults = []
    const promptTemplate = getPromptTemplate()

    try {
        for (const item of originalSubtitles.value) {
            if (stopRequested.value) {
                ElMessage.info('检查已停止')
                break
            }

            const result = await apiService.spellCheckAI({
                text: item.text,
                engine: engine.value,
                model: modelName.value,
                prompt_template: promptTemplate
            })

            if (stopRequested.value) break

            if (result.error) {
                ElMessage.error('检查失败: ' + result.error)
                newResults.push({
                    id: item.id,
                    originalNumber: item.number,
                    startTime: item.startTime,
                    endTime: item.endTime,
                    text: item.text,
                    hasChanges: false
                })
            } else {
                const responseText = result.translated || result.text || ''
                const parsed = parseSpellCheckResult(responseText, item.text)
                
                newResults.push({
                    id: item.id,
                    originalNumber: item.number,
                    startTime: item.startTime,
                    endTime: item.endTime,
                    text: parsed.correctedText,
                    originalText: item.text,
                    corrections: parsed.corrections,
                    hasChanges: parsed.corrections.length > 0
                })
                
                if (parsed.corrections.length > 0) {
                    changeCount++
                }
            }
            
            newResults.forEach((r, index) => {
                r.number = index + 1
            })
            checkResults.value = [...newResults]
        }

        hasChanges.value = changeCount > 0

        if (!stopRequested.value && changeCount > 0) {
            ElMessage.success(`发现 ${changeCount} 条字幕有拼写错误`)
        } else if (!stopRequested.value) {
            ElMessage.info('拼写检查完成，未发现错误')
        }
    } catch (error) {
        ElMessage.error('检查失败: ' + error.message)
    } finally {
        isChecking.value = false
        stopRequested.value = false
    }
}

function parseSpellCheckResult(responseText, originalText) {
    try {
        const jsonMatch = responseText.match(/\{[\s\S]*\}/)
        if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0])
            return {
                correctedText: parsed.corrected_text || originalText,
                corrections: parsed.corrections || []
            }
        }
    } catch (e) {
        console.warn('Failed to parse spell check result:', e)
    }
    
    return {
        correctedText: originalText,
        corrections: []
    }
}

function confirmChanges() {
    if (!hasChanges.value || checkResults.value.length === 0) {
        ElMessage.warning('没有需要保存的更改')
        return
    }

    const paragraphs = subtitleStore.currentSubtitle.paragraphs
    
    checkResults.value.forEach((result, index) => {
        if (result.hasChanges && result.text !== result.originalText) {
            subtitleStore.updateParagraphText(index, result.text)
        }
    })

    ElMessage.success('拼写检查已保存')
    close()
}

function close() {
    uiStore.hideSpellCheckDialog()
}

function handleCancel() {
    if (isChecking.value) {
        stopRequested.value = true
        ElMessage.info('正在停止检查...')
        const checkInterval = setInterval(() => {
            if (!isChecking.value) {
                clearInterval(checkInterval)
                close()
            }
        }, 100)
    } else {
        close()
    }
}
</script>

<style lang="scss" scoped>
.spell-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.checking-status {
    color: #409eff;
    font-size: 14px;
}

.spell-content {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;

    .spell-panel {
        flex: 1;
        overflow: hidden;
    }

    .panel-title {
        font-weight: bold;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid #e0e0e0;
    }
}
</style>
