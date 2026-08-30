<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleUpdateVisible"
    title="本地 AI 字幕工作台 · 控制中心"
    width="760px"
    :close-on-click-modal="false"
    @open="onOpen"
    @close="onCancel"
  >
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 工作区 -->
      <el-tab-pane label="工作区" name="workspace">
        <div class="settings-section">
          <el-form label-width="130px" size="small">
            <el-form-item label="主题">
              <el-select v-model="draft.workspace.theme">
                <el-option label="深色" value="dark" />
                <el-option label="浅色" value="light" />
                <el-option label="跟随系统" value="system" />
              </el-select>
            </el-form-item>
            <el-form-item label="自动恢复会话">
              <el-switch v-model="draft.workspace.autoRestoreSession" />
              <span class="hint">启动时恢复上次打开的媒体和字幕</span>
            </el-form-item>
            <el-form-item label="快捷键">
              <el-button size="small" @click="resetHotkeys">恢复默认快捷键</el-button>
              <span class="hint">快捷键说明（待完善）</span>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 识别引擎 -->
      <el-tab-pane label="识别引擎" name="recognition">
        <div class="settings-section">
          <el-form label-width="140px" size="small">
            <el-form-item label="默认引擎">
              <el-select v-model="draft.recognition.defaultEngine" @change="onEngineChange">
                <el-option label="faster-whisper（推荐）" value="faster-whisper" />
                <el-option label="OpenAI Whisper" value="openai-whisper" />
                <el-option label="Whisper.cpp" value="whisper-cpp" />
              </el-select>
            </el-form-item>
            <el-form-item label="识别预设">
              <el-radio-group v-model="draft.recognition.preset" @change="onPresetChange">
                <el-radio label="fast">极速</el-radio>
                <el-radio label="balanced">平衡</el-radio>
                <el-radio label="quality">高质量</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="默认模型">
              <el-select v-model="draft.recognition.defaultModel[draft.recognition.defaultEngine]">
                <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
              </el-select>
            </el-form-item>
            <el-form-item label="默认语言">
              <el-select v-model="draft.recognition.defaultLanguage">
                <el-option label="自动检测" value="auto" />
                <el-option label="中文" value="zh" />
                <el-option label="English" value="en" />
                <el-option label="日本語" value="ja" />
                <el-option label="한국어" value="ko" />
                <el-option label="Deutsch" value="de" />
                <el-option label="Français" value="fr" />
                <el-option label="Español" value="es" />
              </el-select>
            </el-form-item>
            <el-form-item label="GPU 加速">
              <el-switch v-model="draft.recognition.useGpu" />
            </el-form-item>
            <el-form-item label="VAD 静音过滤">
              <el-switch v-model="draft.recognition.vadFilter" />
              <span class="hint">自动过滤无声片段</span>
            </el-form-item>
            <el-form-item label="词级时间戳">
              <el-switch v-model="draft.recognition.wordTimestamps" />
              <span class="hint">提高精度但增加处理时间</span>
            </el-form-item>
            <el-form-item label="初始提示词">
              <el-input
                v-model="draft.recognition.initialPrompt"
                type="textarea"
                :rows="2"
                placeholder="可选，提供上下文提升识别准确率"
              />
            </el-form-item>
            <el-divider />
            <div class="engine-recommendations">
              <p class="rec-title">引擎推荐说明</p>
              <el-alert type="info" :closable="false" class="rec-alert">
                <template #title>
                  <strong>faster-whisper</strong> — CTranslate2 加速，速度快、内存占用低，推荐日常使用
                </template>
              </el-alert>
              <el-alert type="info" :closable="false" class="rec-alert" style="margin-top: 6px">
                <template #title>
                  <strong>OpenAI Whisper</strong> — 官方实现，兼容性最好，适合需要原始模型行为的场景
                </template>
              </el-alert>
              <el-alert type="info" :closable="false" class="rec-alert" style="margin-top: 6px">
                <template #title>
                  <strong>Whisper.cpp</strong> — 纯 C++ 实现，无需 GPU，适合低配机器和离线部署
                </template>
              </el-alert>
            </div>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 模型与硬件 -->
      <el-tab-pane label="模型与硬件" name="model">
        <div class="settings-section">
          <el-form label-width="140px" size="small">
            <el-form-item label="GPU 推理">
              <el-switch v-model="draft.recognition.useGpu" />
            </el-form-item>
            <el-form-item label="CPU 线程数">
              <el-input-number
                v-model="draft.recognition.cpuThreads"
                :min="1" :max="32"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="GPU 任务并发数">
              <el-input-number
                v-model="draft.modelHardware.gpuConcurrency"
                :min="1" :max="8"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="GPU 不可用时回退 CPU">
              <el-switch v-model="draft.modelHardware.gpuFallbackCpu" />
            </el-form-item>
            <el-divider />
            <el-form-item label="已安装模型">
              <div v-if="installedModels.length === 0" class="muted">暂无已安装模型</div>
              <el-tag v-for="m in installedModels" :key="m.name" style="margin: 2px 4px">
                {{ m.name }} ({{ m.size_mb }} MB)
              </el-tag>
            </el-form-item>
            <el-form-item label="模型存储路径">
              <span class="path-text">{{ modelPath }}</span>
              <el-button size="small" style="margin-left: 8px" @click="openDir('model')">打开</el-button>
            </el-form-item>
            <el-divider />
            <el-form-item label="环境状态">
              <div v-if="envLoading" class="muted">加载中...</div>
              <div v-else class="env-status">
                <div class="env-row">
                  <span class="env-label">Python</span>
                  <el-tag :type="envInfo.python?.installed ? 'success' : 'danger'" size="small">{{ envInfo.python?.installed ? '已安装' : '未安装' }}</el-tag>
                </div>
                <div class="env-row">
                  <span class="env-label">FFmpeg</span>
                  <el-tag :type="envInfo.ffmpeg?.installed ? 'success' : 'danger'" size="small">{{ envInfo.ffmpeg?.installed ? '已安装' : '未安装' }}</el-tag>
                </div>
                <div class="env-row">
                  <span class="env-label">GPU</span>
                  <el-tag :type="envInfo.gpu?.available ? 'success' : 'warning'" size="small">{{ envInfo.gpu?.available ? envInfo.gpu.name : '未检测到' }}</el-tag>
                </div>
                <div class="env-row">
                  <span class="env-label">CUDA</span>
                  <el-tag :type="envInfo.cuda?.available ? 'success' : 'warning'" size="small">{{ envInfo.cuda?.available ? '可用' : '不可用' }}</el-tag>
                </div>
                <div class="env-row">
                  <span class="env-label">PyTorch</span>
                  <el-tag :type="envInfo.pytorch?.installed ? 'success' : 'danger'" size="small">{{ envInfo.pytorch?.installed ? envInfo.pytorch.version : '未安装' }}</el-tag>
                </div>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="small" :loading="envLoading" @click="runDiagnostics">运行环境自检</el-button>
              <el-button size="small" @click="openDir('temp')">打开临时目录</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Tab 4: 字幕规则 -->
      <el-tab-pane label="字幕规则" name="subtitle">
        <div class="settings-section">
          <el-form label-width="140px" size="small">
            <el-form-item label="默认字幕语言">
              <el-select v-model="draft.subtitleRules.defaultLang">
                <el-option label="中文" value="zh" />
                <el-option label="English" value="en" />
                <el-option label="日本語" value="ja" />
                <el-option label="한국어" value="ko" />
              </el-select>
            </el-form-item>
            <el-form-item label="默认翻译目标语言">
              <el-select v-model="draft.subtitleRules.defaultTargetLang">
                <el-option label="English" value="en" />
                <el-option label="中文" value="zh" />
                <el-option label="日本語" value="ja" />
                <el-option label="한국어" value="ko" />
              </el-select>
            </el-form-item>
            <el-divider />
            <el-form-item label="每行最大字符数">
              <el-input-number
                v-model="draft.subtitleRules.maxCharsPerLine"
                :min="10" :max="100"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="每条最大时长(ms)">
              <el-input-number
                v-model="draft.subtitleRules.maxDurationMs"
                :min="1000" :max="15000" :step="500"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="每条最小时长(ms)">
              <el-input-number
                v-model="draft.subtitleRules.minDurationMs"
                :min="100" :max="3000" :step="100"
                controls-position="right"
              />
            </el-form-item>
            <el-divider content-position="left">阅读速度警告 (CPS)</el-divider>
            <el-form-item label="CPS 警告阈值">
              <el-input-number
                v-model="draft.subtitleRules.cpsWarn"
                :min="5" :max="40" :step="1"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="CPS 危险阈值">
              <el-input-number
                v-model="draft.subtitleRules.cpsDanger"
                :min="8" :max="60" :step="1"
                controls-position="right"
              />
            </el-form-item>
            <el-divider />
            <el-form-item label="长句拆分阈值(字符)">
              <el-input-number
                v-model="draft.subtitleRules.splitThreshold"
                :min="20" :max="80"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="短句合并阈值(字符)">
              <el-input-number
                v-model="draft.subtitleRules.mergeThreshold"
                :min="5" :max="30"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="静音切分阈值(ms)">
              <el-input-number
                v-model="draft.subtitleRules.silenceSplitThreshold"
                :min="100" :max="2000" :step="100"
                controls-position="right"
              />
            </el-form-item>
            <el-divider />
            <p class="section-title">默认硬字幕样式</p>
            <el-form-item label="字体">
              <el-select v-model="draft.subtitleRules.hardSubtitle.fontFamily">
                <el-option label="Arial" value="Arial" />
                <el-option label="微软雅黑" value="Microsoft YaHei" />
                <el-option label="宋体" value="SimSun" />
                <el-option label="黑体" value="SimHei" />
              </el-select>
            </el-form-item>
            <el-form-item label="字号">
              <el-input-number
                v-model="draft.subtitleRules.hardSubtitle.fontSize"
                :min="12" :max="72"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="字体颜色">
              <el-color-picker v-model="draft.subtitleRules.hardSubtitle.fontColor" />
            </el-form-item>
            <el-form-item label="描边颜色">
              <el-color-picker v-model="draft.subtitleRules.hardSubtitle.outlineColor" />
            </el-form-item>
            <el-form-item label="描边宽度">
              <el-input-number
                v-model="draft.subtitleRules.hardSubtitle.outlineWidth"
                :min="0" :max="10"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="阴影颜色">
              <el-color-picker v-model="draft.subtitleRules.hardSubtitle.shadowColor" />
            </el-form-item>
            <el-form-item label="底部边距">
              <el-input-number
                v-model="draft.subtitleRules.hardSubtitle.bottomMargin"
                :min="0" :max="100"
                controls-position="right"
              />
            </el-form-item>
            <el-divider />
            <p class="section-title">默认导出设置</p>
            <el-form-item label="默认导出格式">
              <el-select v-model="draft.subtitleRules.exportFormat">
                <el-option label="SRT" value="srt" />
                <el-option label="VTT" value="vtt" />
                <el-option label="ASS" value="ass" />
                <el-option label="SUB" value="sub" />
              </el-select>
            </el-form-item>
            <el-form-item label="默认导出编码">
              <el-select v-model="draft.subtitleRules.exportEncoding">
                <el-option label="UTF-8" value="utf-8" />
                <el-option label="UTF-8 BOM" value="utf-8-bom" />
                <el-option label="GBK" value="gbk" />
              </el-select>
            </el-form-item>
            <el-form-item label="文件命名规则">
              <el-input v-model="draft.subtitleRules.exportNaming" placeholder="{name}_{lang}.{ext}" />
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Tab 5: 文件与任务 -->
      <el-tab-pane label="文件与任务" name="file">
        <div class="settings-section">
          <el-form label-width="150px" size="small">
            <el-form-item label="默认导出目录">
              <span class="path-text">{{ draft.fileTask.exportDir || '使用上次目录' }}</span>
            </el-form-item>
            <el-form-item label="临时目录">
              <span class="path-text">{{ draft.fileTask.tempDir || '使用默认目录' }}</span>
            </el-form-item>
            <el-divider />
            <el-form-item label="自动保存">
              <el-switch v-model="draft.fileTask.autoSave" />
            </el-form-item>
            <el-form-item label="保存间隔(秒)">
              <el-input-number
                v-model="draft.fileTask.autoSaveInterval"
                :min="10" :max="600" :step="10"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="版本历史数量">
              <el-input-number
                v-model="draft.fileTask.versionHistoryCount"
                :min="0" :max="50"
                controls-position="right"
              />
            </el-form-item>
            <el-divider />
            <el-form-item label="临时音频保留(天)">
              <el-input-number
                v-model="draft.fileTask.tempAudioRetention"
                :min="1" :max="30"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="临时波形保留(天)">
              <el-input-number
                v-model="draft.fileTask.tempWaveformRetention"
                :min="1" :max="30"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="任务结果保留(天)">
              <el-input-number
                v-model="draft.fileTask.tempTaskResultRetention"
                :min="1" :max="30"
                controls-position="right"
              />
            </el-form-item>
            <el-divider />
            <el-form-item label="缓存占用">
              <div v-if="cacheLoading" class="muted">加载中...</div>
              <div v-else>
                <span>总计 {{ cacheStats.total_mb }} MB</span>
                <span class="hint" style="margin-left: 12px">
                  音频 {{ cacheStats.temp_audio_mb }} MB · 波形 {{ cacheStats.temp_waveform_mb }} MB · 任务 {{ cacheStats.temp_task_results_mb }} MB
                </span>
              </div>
            </el-form-item>
            <el-form-item label="缓存清理">
              <el-button size="small" type="danger" plain @click="confirmClean('audio')">清理临时音频</el-button>
              <el-button size="small" type="danger" plain @click="confirmClean('waveform')">清理波形缓存</el-button>
              <el-button size="small" type="danger" plain @click="confirmClean('task')">清理任务结果</el-button>
            </el-form-item>
            <el-divider />
            <p class="section-title">任务队列策略</p>
            <el-form-item label="GPU 任务并发数">
              <el-input-number
                v-model="draft.fileTask.taskQueue.gpuConcurrency"
                :min="1" :max="8"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="CPU 任务并发数">
              <el-input-number
                v-model="draft.fileTask.taskQueue.cpuConcurrency"
                :min="1" :max="8"
                controls-position="right"
              />
            </el-form-item>
            <el-form-item label="任务完成通知">
              <el-switch v-model="draft.fileTask.taskQueue.taskCompleteNotify" />
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Tab 6: 诊断与关于 -->
      <el-tab-pane label="诊断与关于" name="diagnostics">
        <div class="settings-section">
          <div v-if="diagnosticsLoading" class="loading-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在加载诊断信息...
          </div>
          <div v-else-if="diagnosticsError" class="error-hint">
            <el-alert type="error" :closable="false" :title="diagnosticsError" />
            <el-button type="primary" size="small" style="margin-top: 8px" @click="loadDiagnosticsData">重试</el-button>
          </div>
          <el-form v-else label-width="120px" size="small">
            <el-form-item label="应用版本">
              <span>{{ versionInfo.app_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="前端版本">
              <span>{{ versionInfo.frontend_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="后端版本">
              <span>{{ versionInfo.backend_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="Python">
              <span>{{ versionInfo.python_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="FFmpeg">
              <span>{{ versionInfo.ffmpeg_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="CUDA">
              <span>{{ versionInfo.cuda_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="faster-whisper">
              <span>{{ versionInfo.faster_whisper_version || '-' }}</span>
            </el-form-item>
            <el-form-item label="openai-whisper">
              <span>{{ versionInfo.openai_whisper_version || '-' }}</span>
            </el-form-item>
            <el-divider />
            <el-form-item label="后端健康">
              <el-tag :type="healthStatus === 'ok' ? 'success' : 'danger'" size="small">
                {{ healthStatus === 'ok' ? '正常' : '异常' }}
              </el-tag>
            </el-form-item>
            <el-form-item label="最近错误">
              <div v-if="recentErrors.length === 0" class="muted">无近期错误</div>
              <div v-for="(err, i) in recentErrors" :key="i" class="error-item">{{ err }}</div>
            </el-form-item>
            <el-divider />
            <el-form-item>
              <el-button type="primary" size="small" @click="copyDiagnostics">复制诊断信息</el-button>
              <el-button size="small" @click="openLogs">打开日志目录</el-button>
              <el-button size="small" type="danger" plain @click="confirmReset">恢复默认设置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button type="primary" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSettingsStore } from '@/stores/settingsStore'
import { apiService } from '@/services/ApiService'
import { useUIStore } from '@/stores/uiStore'

defineProps({
  visible: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible'])

const settingsStore = useSettingsStore()
const uiStore = useUIStore()

const activeTab = ref('workspace')
const draft = ref(JSON.parse(JSON.stringify(settingsStore.settings)))

// 模型与引擎数据
const envLoading = ref(false)
const envInfo = ref({})
const installedModels = ref([])
const modelPath = ref('')

// 缓存数据
const cacheLoading = ref(false)
const cacheStats = ref({ total_mb: 0, temp_audio_mb: 0, temp_waveform_mb: 0, temp_task_results_mb: 0 })

// 版本与健康
const versionInfo = ref({})
const healthStatus = ref('unknown')
const recentErrors = ref([])
const diagnosticsLoading = ref(false)
const diagnosticsError = ref('')

const availableModels = ['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 'large', 'large-v2', 'large-v3']

// 弹窗打开时创建草稿、加载数据
function onOpen() {
  settingsStore.beginEdit()
  draft.value = settingsStore.getEffectiveSettings()
  activeTab.value = uiStore.initialSettingsTab
  loadEnvInfo()
  loadCacheStats()
}

// 切换 Tab 时懒加载数据
watch(activeTab, (tab) => {
  if (tab === 'diagnostics' && !versionInfo.value.app_version) {
    loadDiagnosticsData()
  }
})

// 加载环境信息
async function loadEnvInfo() {
  try {
    const res = await apiService.getDiagnostics()
    if (res) {
      envInfo.value = res
      if (res.models) {
        const allModels = [
          ...res.models.whisper.map(m => ({ ...m, engine: 'whisper' })),
          ...res.models.whisper_cpp.map(m => ({ ...m, engine: 'whisper-cpp' })),
          ...res.models.whisper_ctranslate2.map(m => ({ ...m, engine: 'whisper-ctranslate2' }))
        ]
        installedModels.value = allModels
      }
      if (res.paths) {
        modelPath.value = res.paths.model_path || ''
      }
    }
  } catch (e) {
    console.error('加载环境信息失败:', e)
  }
}

// 加载缓存统计
async function loadCacheStats() {
  cacheLoading.value = true
  try {
    const res = await apiService.getCacheStats()
    if (res) {
      cacheStats.value = res
    }
  } catch (e) {
    console.error('加载缓存统计失败:', e)
  }
  cacheLoading.value = false
}

// 加载版本信息
async function loadVersionInfo() {
  try {
    const res = await apiService.getVersionInfo()
    if (res) {
      versionInfo.value = res
    } else {
      diagnosticsError.value = '获取版本信息失败'
    }
  } catch (e) {
    diagnosticsError.value = e.message || '后端服务未连接，请检查后端是否启动'
    console.error('加载版本信息失败:', e)
  }
}

// 加载健康检查
async function loadHealthCheck() {
  try {
    const res = await apiService.getHealthCheck()
    healthStatus.value = res?.overall ? 'ok' : 'error'
  } catch (e) {
    healthStatus.value = 'error'
    console.error('健康检查失败:', e)
  }
}

// 加载诊断信息（版本+健康）
async function loadDiagnosticsData() {
  diagnosticsLoading.value = true
  diagnosticsError.value = ''
  await Promise.all([loadVersionInfo(), loadHealthCheck()])
  diagnosticsLoading.value = false
}

// 运行环境自检
async function runDiagnostics() {
  envLoading.value = true
  try {
    const res = await apiService.getDiagnostics()
    if (res) {
      envInfo.value = res
      if (res.models) {
        const allModels = [
          ...res.models.whisper.map(m => ({ ...m, engine: 'whisper' })),
          ...res.models.whisper_cpp.map(m => ({ ...m, engine: 'whisper-cpp' })),
          ...res.models.whisper_ctranslate2.map(m => ({ ...m, engine: 'whisper-ctranslate2' }))
        ]
        installedModels.value = allModels
      }
      ElMessage.success('环境自检完成')
      if (res.overall_status === 'error') {
        ElMessage.warning('发现环境问题，请查看详情')
      }
    } else {
      ElMessage.error('环境自检失败')
    }
  } catch (e) {
    ElMessage.error('环境自检失败: ' + e.message)
  }
  envLoading.value = false
}

// 引擎切换
function onEngineChange() {
  // 引擎切换时，draft 中的模型字段会自动通过 v-model 反映
}

// 预设切换
function onPresetChange(preset) {
  const config = settingsStore.getPresetConfig(preset)
  if (config.model) {
    draft.value.recognition.defaultModel[draft.value.recognition.defaultEngine] = config.model
  }
  if (config.cpuThreads) {
    draft.value.recognition.cpuThreads = config.cpuThreads
  }
}

// 打开目录
async function openDir(type) {
  try {
    await apiService.openDirectory(type)
    ElMessage.success('已打开目录')
  } catch (e) {
    ElMessage.error('打开目录失败: ' + e.message)
  }
}

// 打开日志目录
async function openLogs() {
  try {
    await apiService.openLogsDirectory()
    ElMessage.success('已打开日志目录')
  } catch (e) {
    ElMessage.error('打开日志目录失败: ' + e.message)
  }
}

// 复制诊断信息
async function copyDiagnostics() {
  try {
    const res = await apiService.getDiagnosticText()
    if (res && res.text) {
      await navigator.clipboard.writeText(res.text)
      ElMessage.success('诊断信息已复制到剪贴板')
    } else {
      ElMessage.error('获取诊断信息失败')
    }
  } catch (e) {
    ElMessage.error('复制诊断信息失败: ' + e.message)
  }
}

// 缓存清理（带二次确认）
async function confirmClean(type) {
  const labels = { audio: '临时音频', waveform: '波形缓存', task: '任务结果' }
  try {
    await ElMessageBox.confirm(
      `确定要清理所有${labels[type]}吗？此操作不可恢复。`,
      `清理${labels[type]}`,
      { confirmButtonText: '确认清理', cancelButtonText: '取消', type: 'warning' }
    )
    let res
    if (type === 'audio') res = await apiService.cleanTempAudio()
    else if (type === 'waveform') res = await apiService.cleanWaveformCache()
    else if (type === 'task') res = await apiService.cleanTaskResults()

    ElMessage.success(`已清理 ${res?.deleted || 0} 个文件`)
    loadCacheStats()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('清理失败: ' + (e.message || ''))
    }
  }
}

// 恢复默认快捷键
function resetHotkeys() {
  draft.value.workspace.hotkeys = {}
  ElMessage.success('已恢复默认快捷键')
}

// 恢复默认设置（在诊断页使用）
async function confirmReset() {
  try {
    await ElMessageBox.confirm(
      '确定要恢复所有设置为默认值吗？此操作将重置所有配置，不可恢复。',
      '恢复默认设置',
      { confirmButtonText: '确认恢复', cancelButtonText: '取消', type: 'warning' }
    )
    settingsStore.resetToDefaults()
    draft.value = settingsStore.getEffectiveSettings()
    ElMessage.success('已恢复默认设置，请点击保存使其生效')
  } catch (e) {
    // 用户取消
  }
}

// 保存
async function onSave() {
  const ok = await settingsStore.saveDraft()
  if (ok) {
    ElMessage.success('设置已保存')
    emit('update:visible', false)
  } else {
    ElMessage.error(settingsStore.lastSaveError?.message || '设置保存失败,请检查本地存储')
  }
}

// 取消
function onCancel() {
  settingsStore.cancelEdit()
  draft.value = JSON.parse(JSON.stringify(settingsStore.settings))
  emit('update:visible', false)
}

function handleUpdateVisible(value) {
  emit('update:visible', value)
}
</script>

<style lang="scss" scoped>
.settings-section {
  padding: 0;
  max-height: 500px;
  overflow-y: auto;
}

.hint {
  margin-left: 8px;
  font-size: $font-size-sm;
  color: $text-muted;
}

.muted {
  color: $text-muted;
  font-size: $font-size-sm;
}

.unit-hint {
  margin-left: 4px;
  font-size: $font-size-sm;
  color: $text-muted;
}

.path-text {
  font-size: $font-size-sm;
  color: $text-secondary;
  word-break: break-all;
}

.section-title {
  font-weight: bold;
  color: $text-color;
  margin-bottom: 8px;
  padding-left: 0;
}

.engine-recommendations {
  .rec-title {
    font-weight: bold;
    color: $text-color;
    margin-bottom: 6px;
  }
  .rec-alert {
    background: var(--app-hover-bg);
    border: 1px solid $glass-border;
    :deep(.el-alert__title) {
      color: $text-color !important;
    }
    :deep(.el-alert__content) {
      color: $text-secondary !important;
    }
  }
}

.env-status {
  .env-row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
    .env-label {
      width: 80px;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

.error-item {
  font-size: $font-size-sm;
  color: $danger-color;
  margin-bottom: 2px;
}

.loading-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: $text-secondary;
  font-size: $font-size-base;
  justify-content: center;
}

.error-hint {
  padding: 20px 0;
}

:deep(.el-dialog) {
  background: $glass-bg !important;
  backdrop-filter: $glass-blur !important;
  -webkit-backdrop-filter: $glass-blur !important;
  border: 1px solid $glass-border !important;
  border-radius: $border-radius !important;
  box-shadow: $glass-shadow !important;
}

:deep(.el-dialog__header) {
  background: var(--app-surface-muted) !important;
  border-bottom: 1px solid $glass-border !important;
  color: $text-color !important;
}

:deep(.el-dialog__body) {
  color: $text-color !important;
}

:deep(.el-dialog__title) {
  color: $text-color !important;
}

:deep(.el-tabs--border-card) {
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius-md;
}

:deep(.el-tabs__nav-wrap) {
  display: flex;
  justify-content: center;
}

:deep(.el-tabs__content) {
  padding: 16px 20px;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-divider) {
  margin: 12px 0;
  border-color: var(--app-border);
}

:deep(.el-tag) {
  background: var(--app-hover-bg);
  border-color: $glass-border;
  color: $text-color;
}
</style>