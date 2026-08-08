import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'subtitle-tool-settings'
const SETTINGS_VERSION = 1

// 默认设置
const getDefaults = () => ({
  _version: SETTINGS_VERSION,

  // 工作区
  workspace: {
    theme: 'system',           // 'dark' | 'light' | 'system'
    fontScale: 100,            // 50-200 百分比
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
    defaultEngine: 'faster-whisper',  // 'faster-whisper' | 'openai-whisper' | 'whisper-cpp'
    defaultModel: {
      'faster-whisper': 'base',
      'openai-whisper': 'base',
      'whisper-cpp': 'ggml-base'
    },
    defaultLanguage: 'auto',         // 'auto' | 'zh' | 'en' | ...
    useGpu: true,
    preset: 'balanced',              // 'fast' | 'balanced' | 'quality'
    vadFilter: true,                 // VAD 静音过滤
    wordTimestamps: false,           // 词级时间戳
    initialPrompt: '',               // 初始提示词
    cpuThreads: 4
  },

  // 模型与硬件
  modelHardware: {
    gpuFallbackCpu: true,            // GPU 不可用时自动回退 CPU
    gpuConcurrency: 1,               // GPU 任务并发数
    cpuConcurrency: 2,               // CPU 任务并发数
    modelPath: ''                    // 模型存储路径（空=默认）
  },

  // 字幕规则
  subtitleRules: {
    defaultLang: 'zh',               // 默认字幕语言
    defaultTargetLang: 'en',         // 默认翻译目标语言
    maxCharsPerLine: 40,             // 每行最大字符数
    maxDurationMs: 7000,             // 每条最大时长（毫秒）
    minDurationMs: 500,              // 每条最小时长（毫秒）
    splitThreshold: 40,              // 长句拆分阈值（字符数）
    mergeThreshold: 10,              // 短句合并阈值（字符数）
    silenceSplitThreshold: 500,       // 静音切分阈值（毫秒）
    exportFormat: 'srt',             // 默认导出格式
    exportEncoding: 'utf-8',         // 默认导出编码
    exportNaming: '{name}_{lang}.{ext}', // 文件命名规则
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
    exportDir: '',                   // 默认导出目录（空=上次目录）
    tempDir: '',                     // 临时目录（空=默认）
    autoSave: true,
    autoSaveInterval: 60,            // 秒
    versionHistoryCount: 10,         // 版本历史数量
    tempAudioRetention: 7,           // 临时音频保留天数
    tempWaveformRetention: 7,        // 临时波形保留天数
    tempTaskResultRetention: 7,      // 临时任务结果保留天数
    taskQueue: {
      gpuConcurrency: 1,
      cpuConcurrency: 2,
      taskCompleteNotify: true       // 任务完成通知
    }
  }
})

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(getDefaults())
  const draft = ref(null)    // 草稿对象，编辑期间使用
  const loaded = ref(false)

  // 加载设置
  function loadFromStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
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

  // 保存设置
  function saveToStorage(data) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data || settings.value))
    } catch (e) {
      console.error('[Settings] 保存设置失败:', e)
    }
  }

  // 版本迁移
  function migrateSettings(old) {
    console.warn('[Settings] 执行版本迁移，旧版本:', old._version)
    // 当前版本为 1，暂无迁移逻辑；后续版本在此扩展
    const merged = deepMerge(getDefaults(), old)
    merged._version = SETTINGS_VERSION
    settings.value = merged
    saveToStorage()
  }

  // 开始编辑（创建草稿）
  function beginEdit() {
    draft.value = JSON.parse(JSON.stringify(settings.value))
  }

  // 保存草稿
  function saveDraft() {
    if (draft.value) {
      settings.value = JSON.parse(JSON.stringify(draft.value))
      draft.value = null
      saveToStorage()
      applySettings()
      return true
    }
    return false
  }

  // 取消编辑（丢弃草稿）
  function cancelEdit() {
    draft.value = null
  }

  // 恢复默认设置
  function resetToDefaults() {
    draft.value = getDefaults()
  }

  // 确认恢复默认（直接生效）
  function confirmResetDefaults() {
    settings.value = getDefaults()
    saveToStorage()
    applySettings()
  }

  // 应用设置到界面
  function applySettings() {
    applyTheme()
    applyFontScale()
  }

  function applyTheme() {
    const theme = settings.value.workspace.theme
    const root = document.documentElement

    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      root.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
    } else {
      root.setAttribute('data-theme', theme)
    }
  }

  function applyFontScale() {
    const scale = settings.value.workspace.fontScale / 100
    document.documentElement.style.setProperty('--font-scale', scale)
  }

  // 获取当前设置（优先返回草稿）
  function getEffectiveSettings() {
    return draft.value || settings.value
  }

  // 获取某个引擎的默认模型
  function getDefaultModel(engine) {
    return settings.value.recognition.defaultModel[engine] || 'base'
  }

  // 获取预设对应的模型和参数
  function getPresetConfig(preset) {
    const presets = {
      fast: { model: 'tiny', cpuThreads: 8, beamSize: 1 },
      balanced: { model: 'base', cpuThreads: 4, beamSize: 5 },
      quality: { model: 'small', cpuThreads: 2, beamSize: 5 }
    }
    return presets[preset] || presets.balanced
  }

  // 深度合并工具
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

  // 精确清理设置缓存
  function clearSettingsCache() {
    localStorage.removeItem(STORAGE_KEY)
    settings.value = getDefaults()
    applySettings()
  }

  loadFromStorage()

  return {
    settings,
    draft,
    loaded,
    loadFromStorage,
    saveToStorage,
    beginEdit,
    saveDraft,
    cancelEdit,
    resetToDefaults,
    confirmResetDefaults,
    applySettings,
    applyTheme,
    applyFontScale,
    getEffectiveSettings,
    getDefaultModel,
    getPresetConfig,
    clearSettingsCache
  }
})