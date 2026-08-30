import { defineStore } from 'pinia'
import { ref, getCurrentScope, onScopeDispose } from 'vue'
import { storageGet, storageSet, storageRemove } from '@/utils/storage'

/**
 * 全局设置(设置对话框 6 大模块,仅存长期偏好;单次识别/导出参数不入库)
 * @typedef {Object} AppSettings
 * @property {number} _version - 设置结构版本(迁移用)
 * @property {{theme:'dark'|'light'|'system',autoRestoreSession:boolean,hotkeys:Object,layout:{videoVisible:boolean,waveformVisible:boolean,subtitleListVisible:boolean,panelSizes:Object}}} workspace - 工作区
 * @property {{defaultEngine:string,defaultModel:Object<string,string>,defaultLanguage:string,useGpu:boolean,preset:string,vadFilter:boolean,wordTimestamps:boolean,initialPrompt:string,cpuThreads:number}} recognition - 识别引擎
 * @property {{gpuFallbackCpu:boolean,gpuConcurrency:number,cpuConcurrency:number,modelPath:string}} modelHardware - 模型与硬件
 * @property {{defaultLang:string,defaultTargetLang:string,maxCharsPerLine:number,maxDurationMs:number,minDurationMs:number,cpsWarn:number,cpsDanger:number,splitThreshold:number,mergeThreshold:number,silenceSplitThreshold:number,exportFormat:string,exportEncoding:string,exportNaming:string,hardSubtitle:Object}} subtitleRules - 字幕规则
 * @property {{exportDir:string,tempDir:string,autoSave:boolean,autoSaveInterval:number,versionHistoryCount:number,tempAudioRetention:number,tempWaveformRetention:number,tempTaskResultRetention:number,taskQueue:{gpuConcurrency:number,cpuConcurrency:number,taskCompleteNotify:boolean}}} fileTask - 文件与任务
 */

/**
 * 翻译引擎模型配置(下拉列表数据源,持久化于 MODEL_CONFIGS_KEY)
 * @typedef {Object} ModelConfig
 * @property {number} id - 自增唯一 ID
 * @property {string} name - 显示名称
 * @property {string} provider - 服务商(openai/deepl/google/...)
 * @property {string} [apiKey] - 密钥
 * @property {string} [baseUrl] - 自定义接入点
 * @property {string} [model] - 模型名
 * @property {*} [props] - 其他透传字段
 */

const STORAGE_KEY = 'subtitle-tool-settings'
const MODEL_CONFIGS_KEY = 'subtitle-tool-model-configs'
const SETTINGS_VERSION = 1

/** @returns {AppSettings} 默认设置 */
const getDefaults = () => ({
  _version: SETTINGS_VERSION,

  // 工作区
  workspace: {
    theme: 'system',           // 'dark' | 'light' | 'system'
    autoRestoreSession: true,  // 自动恢复上次打开的媒体和字幕
    hotkeys: {},               // 快捷键（预留）
    layout: {
      videoVisible: true,
      waveformVisible: true,
      subtitleListVisible: true,
      panelSizes: {}           // 面板尺寸
    }
  },

  // 识别引擎
  recognition: {
    defaultEngine: 'faster-whisper',
    defaultModel: {
      'faster-whisper': 'base',
      'openai-whisper': 'base',
      'whisper-cpp': 'ggml-base'
    },
    defaultLanguage: 'auto',
    useGpu: true,
    preset: 'balanced',
    vadFilter: true,
    wordTimestamps: false,
    initialPrompt: '',
    cpuThreads: 4
  },

  // 模型与硬件
  modelHardware: {
    gpuFallbackCpu: true,
    gpuConcurrency: 1,
    cpuConcurrency: 2,
    modelPath: ''
  },

  // 字幕规则
  subtitleRules: {
    defaultLang: 'zh',
    defaultTargetLang: 'en',
    maxCharsPerLine: 40,
    maxDurationMs: 7000,
    minDurationMs: 500,
    cpsWarn: 15,
    cpsDanger: 20,
    splitThreshold: 40,
    mergeThreshold: 10,
    silenceSplitThreshold: 500,
    exportFormat: 'srt',
    exportEncoding: 'utf-8',
    exportNaming: '{name}_{lang}.{ext}',
    hardSubtitle: {
      fontFamily: 'Arial',
      fontSize: 24,
      fontColor: '#FFFFFF',
      outlineColor: '#000000',
      outlineWidth: 2,
      shadowColor: '#000000',
      shadowOffset: 0,
      bottomMargin: 10
    }
  },

  // 文件与任务
  fileTask: {
    exportDir: '',
    tempDir: '',
    autoSave: true,
    autoSaveInterval: 60,
    versionHistoryCount: 10,
    tempAudioRetention: 7,
    tempWaveformRetention: 7,
    tempTaskResultRetention: 7,
    taskQueue: {
      gpuConcurrency: 1,
      cpuConcurrency: 2,
      taskCompleteNotify: true
    }
  }
})

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(getDefaults())
  const draft = ref(null)
  const loaded = ref(false)
  const modelConfigVisible = ref(false)
  const modelConfigs = ref([])
  let modelConfigNextId = 1

  // 设置保存失败的最近一次原因(供 UI 层 toast 消费),{ message, quota: boolean } | null
  const lastSaveError = ref(null)

  // ============================================================
  // matchMedia:跟随系统主题的监听,并在 store 作用域销毁时移除
  // ============================================================
  let mqHandler = null
  let mq = null

  function updateThemeAttribute(theme) {
    const root = document.documentElement
    if (theme === 'system') {
      const prefersDark = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) || false
      root.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
    } else {
      root.setAttribute('data-theme', theme)
    }
  }

  function applyTheme() {
    updateThemeAttribute(settings.value.workspace.theme)
  }

  function applySettings() {
    applyTheme()
  }

  function bindSystemThemeListener() {
    if (typeof window === 'undefined') return
    if (mqHandler) return
    mq = window.matchMedia('(prefers-color-scheme: dark)')
    mqHandler = () => {
      if (settings.value.workspace.theme === 'system') {
        updateThemeAttribute('system')
      }
    }
    try {
      mq.addEventListener('change', mqHandler)
    } catch (_) {
      // Safari 旧版 fallback
      if (mq.addListener) mq.addListener(mqHandler)
    }
    // 若 store 存在作用域(如在组件 setup 中首次创建),组件销毁时解绑
    try {
      if (getCurrentScope()) {
        onScopeDispose(unbindSystemThemeListener)
      }
    } catch { /* ignore */ }
  }

  function unbindSystemThemeListener() {
    if (!mqHandler) return
    if (mq) {
      try { mq.removeEventListener('change', mqHandler) } catch (_) {
        if (mq.removeListener) mq.removeListener(mqHandler)
      }
    }
    mqHandler = null
    mq = null
  }

  bindSystemThemeListener()

  // ============================================================
  // 加载 / 保存(双写 localStorage + 统一存储,写入失败可查)
  // ============================================================
  async function loadFromStorage() {
    try {
      // 优先从统一存储加载（Electron IPC 或浏览器 localStorage）
      let raw = null
      try {
        raw = await storageGet(STORAGE_KEY)
      } catch { /* 统一存储不可用时回退 */ }

      if (!raw) {
        try { raw = localStorage.getItem(STORAGE_KEY) } catch { /* ignore */ }
      }

      if (raw) {
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
        if (parsed._version !== SETTINGS_VERSION) {
          migrateSettings(parsed)
        } else {
          settings.value = deepMerge(getDefaults(), parsed)
        }
      }
    } catch (e) {
      console.error('[Settings] 加载设置失败:', e)
    }
    loaded.value = true
  }

  // 保存设置（双写：localStorage + 统一存储）,返回 { success, error }
  async function saveToStorage(data) {
    const payload = data || settings.value
    const jsonObj = JSON.parse(JSON.stringify(payload))
    const jsonStr = JSON.stringify(jsonObj)

    // 1) localStorage 兜底写(非严格)
    try {
      localStorage.setItem(STORAGE_KEY, jsonStr)
    } catch (e) {
      console.warn('[Settings] localStorage 设置保存失败:', e)
    }

    // 2) 统一存储为主:真正的错误冒泡到这里
    let unifiedResult = { success: true }
    try {
      unifiedResult = await storageSet(STORAGE_KEY, jsonObj) || { success: true }
    } catch (e) {
      unifiedResult = { success: false, error: e.message || '统一存储写入异常', quota: false }
    }

    if (unifiedResult.success) {
      lastSaveError.value = null
    } else {
      lastSaveError.value = {
        message: `设置保存失败: ${unifiedResult.error || '未知原因'}`,
        quota: !!unifiedResult.quota
      }
    }
    return unifiedResult
  }

  function migrateSettings(old) {
    console.warn('[Settings] 执行版本迁移，旧版本:', old._version)
    const merged = deepMerge(getDefaults(), old)
    merged._version = SETTINGS_VERSION
    settings.value = merged
    saveToStorage()
  }

  function beginEdit() {
    draft.value = JSON.parse(JSON.stringify(settings.value))
  }

  async function saveDraft() {
    if (draft.value) {
      settings.value = JSON.parse(JSON.stringify(draft.value))
      draft.value = null
      const r = await saveToStorage()
      applySettings()
      return r.success
    }
    return false
  }

  function cancelEdit() {
    draft.value = null
  }

  function resetToDefaults() {
    draft.value = getDefaults()
  }

  async function confirmResetDefaults() {
    settings.value = getDefaults()
    await saveToStorage()
    applySettings()
  }

  function getEffectiveSettings() {
    return draft.value || settings.value
  }

  function getDefaultModel(engine) {
    return settings.value.recognition.defaultModel[engine] || 'base'
  }

  function getPresetConfig(preset) {
    const presets = {
      fast: { model: 'tiny', cpuThreads: 8, beamSize: 1 },
      balanced: { model: 'base', cpuThreads: 4, beamSize: 5 },
      quality: { model: 'small', cpuThreads: 2, beamSize: 5 }
    }
    return presets[preset] || presets.balanced
  }

  function deepMerge(target, source) {
    const result = { ...target }
    for (const key of Object.keys(source)) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = deepMerge(result[key] || {}, source[key])
      } else {
        result[key] = source[key]
      }
    }
    return result
  }

  async function clearSettingsCache() {
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
    try { await storageRemove(STORAGE_KEY) } catch { /* ignore */ }
    settings.value = getDefaults()
    applySettings()
  }

  // ============================================================
  // 模型配置弹窗
  // ============================================================
  function showModelConfig() { modelConfigVisible.value = true }
  function hideModelConfig() { modelConfigVisible.value = false }

  async function loadModelConfigs() {
    try {
      let raw = null
      try {
        raw = await storageGet(MODEL_CONFIGS_KEY)
      } catch { /* 回退 */ }

      if (!raw) {
        try { raw = localStorage.getItem(MODEL_CONFIGS_KEY) } catch { /* ignore */ }
      }

      if (raw) {
        const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
        modelConfigs.value = parsed.configs || []
        modelConfigNextId = parsed.nextId || 1
      }
    } catch (e) {
      console.error('[Settings] 加载模型配置失败:', e)
    }
  }

  async function saveModelConfigs() {
    const data = { configs: modelConfigs.value, nextId: modelConfigNextId }
    try {
      localStorage.setItem(MODEL_CONFIGS_KEY, JSON.stringify(data))
    } catch (e) {
      console.warn('[Settings] localStorage 保存模型配置失败:', e)
    }
    try {
      const r = await storageSet(MODEL_CONFIGS_KEY, data) || { success: true }
      if (!r.success) {
        console.warn('[Settings] 模型配置保存失败:', r.error)
      }
    } catch (e) {
      console.warn('[Settings] 模型配置保存异常:', e)
    }
  }

  /** @param {Omit<ModelConfig,'id'>} config */
  async function addModelConfig(config) {
    modelConfigs.value.push({ id: modelConfigNextId++, ...config })
    await saveModelConfigs()
  }

  async function updateModelConfig(id, data) {
    const idx = modelConfigs.value.findIndex(c => c.id === id)
    if (idx !== -1) {
      modelConfigs.value[idx] = { ...modelConfigs.value[idx], ...data }
      await saveModelConfigs()
    }
  }

  async function removeModelConfig(id) {
    modelConfigs.value = modelConfigs.value.filter(c => c.id !== id)
    await saveModelConfigs()
  }

  async function updateRecognitionSettings(data) {
    settings.value.recognition.defaultEngine = data.engine
    settings.value.recognition.preset = data.preset
    settings.value.recognition.defaultModel[data.engine] = data.model
    settings.value.recognition.defaultLanguage = data.language
    settings.value.recognition.useGpu = data.useGpu
    settings.value.recognition.vadFilter = data.vadFilter
    settings.value.recognition.wordTimestamps = data.wordTimestamps
    await saveToStorage()
  }

  // 异步初始化（不阻塞 store 创建）
  loadFromStorage()
  loadModelConfigs()
  applySettings()

  return {
    settings,
    draft,
    loaded,
    lastSaveError,
    loadFromStorage,
    saveToStorage,
    beginEdit,
    saveDraft,
    cancelEdit,
    resetToDefaults,
    confirmResetDefaults,
    applySettings,
    applyTheme,
    getEffectiveSettings,
    getDefaultModel,
    getPresetConfig,
    clearSettingsCache,
    modelConfigVisible,
    showModelConfig,
    hideModelConfig,
    updateRecognitionSettings,
    modelConfigs,
    addModelConfig,
    updateModelConfig,
    removeModelConfig,
    // 生命周期暴露,测试/清理用
    _disposeThemeListener: unbindSystemThemeListener
  }
})
