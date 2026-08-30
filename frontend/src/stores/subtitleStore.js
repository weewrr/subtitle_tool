import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Subtitle, Paragraph, TimeCode, SubtitleFormats } from '@/models/subtitle'

/**
 * 段落的可序列化形态(.stproj / 会话快照共用)
 * @typedef {Object} ParagraphPlain
 * @property {number} start - 起始毫秒
 * @property {number} end - 结束毫秒
 * @property {string} text - 原文
 * @property {string} translation - 译文
 * @property {string} [style] - ASS 样式
 * @property {string} [actor] - ASS 说话人
 * @property {string} [marginL] - ASS 左边距
 * @property {string} [marginR] - ASS 右边距
 * @property {string} [marginV] - ASS 垂直边距
 * @property {string} [effect] - ASS 特效
 */

/**
 * 媒体重连信息(项目文件只存路径,不打包媒体本体)
 * @typedef {Object} ProjectMedia
 * @property {string|null} videoPath - 视频本地路径(Electron)
 * @property {string|null} dubbingAudioPath - 配音音频本地路径
 */

/**
 * .stproj 项目文件 / 会话快照 / 草稿的统一负载结构
 * @typedef {Object} SubtitleProject
 * @property {string} app - 固定 'subtitle-tool'
 * @property {string} format - 固定 'stproj'
 * @property {number} version - 格式版本
 * @property {string} savedAt - ISO 保存时间
 * @property {{fileName:string,header:string,footer:string,paragraphs:ParagraphPlain[]}} subtitle - 字幕数据
 * @property {ProjectMedia} media - 媒体路径
 * @property {{showTranslation:boolean,selectedParagraphIndex:number}} view - 视图状态
 * @property {{undo:Array,redo:Array}} [history] - 撤销/重做栈(可选)
 * @property {boolean} [snapshot] - 会话快照标记
 * @property {boolean} [draft] - 草稿标记
 */

export const useSubtitleStore = defineStore('subtitle', () => {
  const currentSubtitle = ref(new Subtitle())
  const selectedParagraphIndex = ref(-1)
  const isModified = ref(false)
  const videoFile = ref(null)
  const videoElement = ref(null)
  const showTranslation = ref(false)
  const dubbingAudioFile = ref(null)

  const selectedParagraph = computed(() => {
    if (selectedParagraphIndex.value >= 0 && selectedParagraphIndex.value < currentSubtitle.value.paragraphs.length) {
      return currentSubtitle.value.paragraphs[selectedParagraphIndex.value]
    }
    return null
  })

  const paragraphCount = computed(() => currentSubtitle.value.paragraphs.length)

  const hasTranslation = computed(() => {
    return currentSubtitle.value.paragraphs.some(p => p.translation && p.translation.trim().length > 0)
  })

  function selectParagraph(index) {
    selectedParagraphIndex.value = index
  }

  function updateParagraphText(index, text) {
    if (index >= 0 && index < currentSubtitle.value.paragraphs.length) {
      currentSubtitle.value.saveHistory('修改字幕文本')
      currentSubtitle.value.paragraphs[index].text = text
      isModified.value = true
    }
  }

  function updateParagraphTranslation(index, translation) {
    if (index >= 0 && index < currentSubtitle.value.paragraphs.length) {
      currentSubtitle.value.paragraphs[index].translation = translation
      isModified.value = true
    }
  }

  // 更新时间码(波形拖拽/行内编辑/键盘微调共用)。
  // skipHistory: 拖拽过程中持续调用时不重复入历史栈,由调用方在拖拽开始时入栈一次。
  function updateParagraphTime(index, startMs, endMs, skipHistory = false) {
    const ps = currentSubtitle.value.paragraphs
    if (index < 0 || index >= ps.length) return false
    startMs = Math.max(0, Math.round(startMs))
    endMs = Math.max(0, Math.round(endMs))
    // 最短时长 0.1s,且不允许倒置
    if (endMs - startMs < 100) return false
    if (!skipHistory) {
      currentSubtitle.value.saveHistory('调整时间码')
    }
    ps[index].startTime.totalMilliseconds = startMs
    ps[index].endTime.totalMilliseconds = endMs
    isModified.value = true
    return true
  }

  // 拖拽开始时保存一次历史(配合 updateParagraphTime 的 skipHistory)
  function saveTimeEditHistory() {
    currentSubtitle.value.saveHistory('调整时间码')
  }

  function addParagraph(paragraph) {
    currentSubtitle.value.addParagraph(paragraph)
    isModified.value = true
  }

  function removeParagraph(index) {
    currentSubtitle.value.removeParagraph(index)
    isModified.value = true
  }

  function undo() {
    const result = currentSubtitle.value.undo()
    if (result) {
      isModified.value = true
    }
    return result
  }

  function redo() {
    const result = currentSubtitle.value.redo()
    if (result) {
      isModified.value = true
    }
    return result
  }

  const canUndo = computed(() => currentSubtitle.value.historyItems.length > 0)
  const canRedo = computed(() => currentSubtitle.value.redoItems.length > 0)

  // 撤销到指定步数(保留前 keepCount 条历史),用于历史面板点击回退。
  // 逐步撤销使每一中间状态都进入重做栈,可连续重做回来。
  function undoToStep(keepCount) {
    const items = currentSubtitle.value.historyItems
    if (keepCount < 0 || keepCount >= items.length) return false
    while (currentSubtitle.value.historyItems.length > keepCount) {
      currentSubtitle.value.undo()
    }
    currentSubtitle.value.renumber()
    isModified.value = true
    return true
  }

  // 批量删除(索引数组,自动按倒序删除避免索引位移)
  function removeParagraphs(indexes) {
    if (!indexes?.length) return
    currentSubtitle.value.saveHistory('批量删除字幕')
    const sorted = [...indexes].sort((a, b) => b - a)
    const ps = currentSubtitle.value.paragraphs
    for (const i of sorted) {
      if (i >= 0 && i < ps.length) ps.splice(i, 1)
    }
    currentSubtitle.value.renumber()
    isModified.value = true
  }

  // 时间码整体平移:indexes 为 null 时应用到全部行
  function shiftParagraphTime(indexes, deltaMs) {
    deltaMs = Math.round(deltaMs)
    if (!deltaMs) return false
    const ps = currentSubtitle.value.paragraphs
    if (!ps.length) return false
    currentSubtitle.value.saveHistory(deltaMs > 0 ? '时间码后移' : '时间码前移')
    const targets = indexes ? new Set(indexes) : null
    for (let i = 0; i < ps.length; i++) {
      if (targets && !targets.has(i)) continue
      const s = Math.max(0, ps[i].startTime.totalMilliseconds + deltaMs)
      const en = Math.max(0, ps[i].endTime.totalMilliseconds + deltaMs)
      ps[i].startTime.totalMilliseconds = s
      ps[i].endTime.totalMilliseconds = en
    }
    isModified.value = true
    return true
  }

  function loadSubtitle(content, fileName) {
    const format = SubtitleFormats.detectFormat(content)
    if (format) {
      currentSubtitle.value = SubtitleFormats.parse(content, format)
      currentSubtitle.value.fileName = fileName
      selectedParagraphIndex.value = -1
      isModified.value = false
      showTranslation.value = false
      return true
    }
    return false
  }

  function loadFromTranscription(segments, fileName) {
    currentSubtitle.value = new Subtitle()
    currentSubtitle.value.fileName = fileName
    
    segments.forEach((item, index) => {
      const startTime = new TimeCode(item.start * 1000)
      const endTime = new TimeCode(item.end * 1000)
      const paragraph = new Paragraph(startTime, endTime, item.text, index + 1)
      currentSubtitle.value.paragraphs.push(paragraph)
    })
    
    currentSubtitle.value.renumber()
    selectedParagraphIndex.value = -1
    isModified.value = false
    showTranslation.value = false
  }

  function clearSubtitle() {
    currentSubtitle.value = new Subtitle()
    selectedParagraphIndex.value = -1
    isModified.value = false
    showTranslation.value = false
  }

  function setVideoFile(file) {
    videoFile.value = file
  }

  function setVideoElement(element) {
    videoElement.value = element
  }

  function setDubbingAudioFile(file) {
    dubbingAudioFile.value = file
  }

  function exportToSRT() {
    return SubtitleFormats.toSRT(currentSubtitle.value)
  }

  function exportToSRTTranslation() {
    return SubtitleFormats.toSRTTranslation(currentSubtitle.value)
  }

  function exportToVTT() {
    return SubtitleFormats.toVTT(currentSubtitle.value)
  }

  function exportToASS() {
    return SubtitleFormats.toASS(currentSubtitle.value)
  }

  // 通用格式导出:useTranslation 时以翻译文本作为正文
  function exportAsFormat(format, useTranslation = false) {
    let target = currentSubtitle.value
    if (useTranslation && hasTranslation.value) {
      target = new Subtitle()
      target.fileName = currentSubtitle.value.fileName
      target.paragraphs = currentSubtitle.value.paragraphs.map(p => {
        const c = p.clone()
        if (c.translation && c.translation.trim()) c.text = c.translation
        return c
      })
    }
    switch (format) {
      case 'vtt': return SubtitleFormats.toVTT(target)
      case 'ass': return SubtitleFormats.toASS(target)
      case 'txt': return SubtitleFormats.toTXT(target)
      default: return SubtitleFormats.toSRT(target)
    }
  }

  // ============================================================
  // 项目文件(.stproj):完整工作区序列化,仅本软件可打开
  // ============================================================
  const PROJECT_FORMAT = 'stproj'
  const SESSION_KEY = 'subtitle-tool-last-session'

  /**
   * 序列化完整工作区(.stproj 项目文件 / 会话快照 / 草稿共用)
   * @param {{includeHistory?:boolean, maxHistoryItems?:number}} [opts] - 是否携带撤销栈及条数上限
   * @returns {SubtitleProject}
   */
  function serializeProject(opts = {}) {
    const { includeHistory = true, maxHistoryItems = 30 } = opts
    const payload = {
      app: 'subtitle-tool',
      format: PROJECT_FORMAT,
      version: 1,
      savedAt: new Date().toISOString(),
      subtitle: {
        fileName: currentSubtitle.value.fileName,
        header: currentSubtitle.value.header,
        footer: currentSubtitle.value.footer,
        paragraphs: currentSubtitle.value.paragraphs.map(p => ({
          start: p.startTime.totalMilliseconds,
          end: p.endTime.totalMilliseconds,
          text: p.text,
          translation: p.translation,
          style: p.style,
          actor: p.actor,
          marginL: p.marginL,
          marginR: p.marginR,
          marginV: p.marginV,
          effect: p.effect
        }))
      },
      media: {
        // 媒体文件本体不打包,仅记录路径(桌面版可自动重连,浏览器版提示手动加载)
        videoPath: typeof videoFile.value === 'string' ? videoFile.value : null,
        dubbingAudioPath: typeof dubbingAudioFile.value === 'string' ? dubbingAudioFile.value : null
      },
      view: {
        showTranslation: showTranslation.value,
        selectedParagraphIndex: selectedParagraphIndex.value
      }
    }
    if (includeHistory) {
      payload.history = currentSubtitle.value.serializeHistory(maxHistoryItems)
    }
    return payload
  }

  /**
   * 加载 .stproj 项目
   * @param {SubtitleProject} data - 项目负载
   * @returns {{media:ProjectMedia}|null} 成功返回媒体重连信息,失败返回 null
   */
  function loadProject(data) {
    if (!data || data.format !== PROJECT_FORMAT || !data.subtitle || !Array.isArray(data.subtitle.paragraphs)) {
      return null
    }
    const sub = new Subtitle()
    sub.fileName = data.subtitle.fileName || '未命名项目'
    sub.header = data.subtitle.header || ''
    sub.footer = data.subtitle.footer || ''
    for (const p of data.subtitle.paragraphs) {
      const para = new Paragraph(new TimeCode(p.start || 0), new TimeCode(p.end || 0), p.text || '')
      para.translation = p.translation || ''
      para.style = p.style || ''
      para.actor = p.actor || ''
      para.marginL = p.marginL || '0000'
      para.marginR = p.marginR || '0000'
      para.marginV = p.marginV || '0000'
      para.effect = p.effect || ''
      sub.paragraphs.push(para)
    }
    sub.renumber()
    // #7 恢复 undo/redo 栈(来自历史版本无 history 字段时静默跳过)
    if (data.history) sub.restoreHistory(data.history)
    currentSubtitle.value = sub
    selectedParagraphIndex.value = data.view?.selectedParagraphIndex ?? -1
    isModified.value = false
    if (data.view) showTranslation.value = !!data.view.showTranslation
    return { media: data.media || {} }
  }

  // ============================================================
  // #5 会话快照(自动恢复上次会话):不含撤销历史以节省体积
  // ============================================================
  const lastSessionError = ref(null)

  /**
   * 保存会话快照到 localStorage(不含撤销历史,节省体积)
   * @returns {boolean} 是否成功(失败时 lastSessionError 可查原因)
   */
  function saveSessionSnapshot() {
    if (paragraphCount.value === 0) {
      try { localStorage.removeItem(SESSION_KEY) } catch (_) { /* ignore */ }
      return true
    }
    lastSessionError.value = null
    try {
      const snap = serializeProject({ includeHistory: false })
      snap.snapshot = true
      localStorage.setItem(SESSION_KEY, JSON.stringify(snap))
      return true
    } catch (e) {
      lastSessionError.value = e
      console.warn('[Session] 保存会话快照失败:', e)
      return false
    }
  }

  function peekSessionSnapshot() {
    try {
      const raw = localStorage.getItem(SESSION_KEY)
      if (!raw) return null
      const data = JSON.parse(raw)
      if (data?.subtitle?.paragraphs?.length > 0) return data
    } catch { /* ignore */ }
    return null
  }

  function clearSessionSnapshot() {
    try { localStorage.removeItem(SESSION_KEY) } catch (e) { console.warn(e) }
  }

  // ============================================================
  // 崩溃保护:草稿持久化(localStorage)
  // ============================================================
  const DRAFT_KEY = 'subtitle-tool-draft'
  const draftSavedAt = ref(null)
  const lastDraftError = ref(null)

  function saveDraft() {
    if (currentSubtitle.value.paragraphs.length === 0) return false
    lastDraftError.value = null
    try {
      const data = serializeProject()
      data.draft = true
      const payload = JSON.stringify(data)
      // 预留 4.5MB 安全阈值(与 storage.js 一致),避免写入超过浏览器配额
      if (typeof Blob !== 'undefined') {
        const size = new Blob([payload]).size
        const used = Object.keys(localStorage).reduce((s, k) => {
          try { return s + (localStorage.getItem(k)?.length || 0) * 2 } catch { return s }
        }, 0)
        if (used + size > 4.5 * 1024 * 1024) {
          const err = new Error('本地存储容量不足(>4.5MB),请导出项目或清理缓存')
          err.name = 'QuotaExceededError'
          throw err
        }
      }
      localStorage.setItem(DRAFT_KEY, payload)
      draftSavedAt.value = Date.now()
      return true
    } catch (e) {
      lastDraftError.value = e
      console.error('[Subtitle] 草稿保存失败:', e)
      return false
    }
  }

  // 读取草稿(不删除),无草稿返回 null
  function peekDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (!raw) return null
      const data = JSON.parse(raw)
      if (data?.subtitle?.paragraphs?.length > 0) return data
    } catch { /* 损坏的草稿视同无草稿 */ }
    return null
  }

  function clearDraft() {
    try {
      localStorage.removeItem(DRAFT_KEY)
    } catch (e) {
      console.warn('[Subtitle] 清理草稿失败:', e)
    }
    draftSavedAt.value = null
  }

  // 已显式保存到文件后调用:清除草稿并复位修改标记
  function markSaved() {
    isModified.value = false
    clearDraft()
  }

  function mergeParagraphs(startIndex, endIndex) {
    if (startIndex < 0 || endIndex >= currentSubtitle.value.paragraphs.length || startIndex >= endIndex) {
      return false
    }

    currentSubtitle.value.saveHistory('合并字幕')

    const paragraphs = currentSubtitle.value.paragraphs
    const firstParagraph = paragraphs[startIndex]
    const lastParagraph = paragraphs[endIndex]

    const mergedText = paragraphs.slice(startIndex, endIndex + 1).map(p => p.text).join(' ')
    const mergedTranslation = paragraphs.slice(startIndex, endIndex + 1).map(p => p.translation || '').filter(t => t).join(' ')

    const mergedParagraph = new Paragraph(
      firstParagraph.startTime,
      lastParagraph.endTime,
      mergedText,
      firstParagraph.number
    )
    mergedParagraph.translation = mergedTranslation

    paragraphs.splice(startIndex, endIndex - startIndex + 1, mergedParagraph)
    currentSubtitle.value.renumber()
    isModified.value = true

    return true
  }

  function applyMergedSubtitles(mergedData) {
    currentSubtitle.value.saveHistory('合并字幕')

    const newSubtitle = new Subtitle()
    newSubtitle.fileName = currentSubtitle.value.fileName
    newSubtitle.header = currentSubtitle.value.header
    newSubtitle.footer = currentSubtitle.value.footer
    newSubtitle.originalFormat = currentSubtitle.value.originalFormat
    newSubtitle.historyItems = currentSubtitle.value.historyItems

    mergedData.forEach(item => {
      const p = new Paragraph(
        item.startTime,
        item.endTime,
        item.text,
        item.number
      )
      p.id = item.id
      p.translation = item.translation || ''
      newSubtitle.paragraphs.push(p)
    })

    newSubtitle.renumber()
    currentSubtitle.value = newSubtitle
    isModified.value = true
  }

  function applySplitResults(splitResults) {
    currentSubtitle.value.saveHistory('分割长句')

    const newSubtitle = new Subtitle()
    newSubtitle.fileName = currentSubtitle.value.fileName
    newSubtitle.header = currentSubtitle.value.header
    newSubtitle.footer = currentSubtitle.value.footer
    newSubtitle.originalFormat = currentSubtitle.value.originalFormat
    newSubtitle.historyItems = currentSubtitle.value.historyItems

    splitResults.forEach(item => {
      const p = new Paragraph(
        item.startTime,
        item.endTime,
        item.text,
        item.number
      )
      newSubtitle.paragraphs.push(p)
    })

    newSubtitle.renumber()
    currentSubtitle.value = newSubtitle
    isModified.value = true
  }

  return {
    currentSubtitle,
    selectedParagraphIndex,
    selectedParagraph,
    isModified,
    videoFile,
    videoElement,
    dubbingAudioFile,
    paragraphCount,
    hasTranslation,
    showTranslation,
    selectParagraph,
    updateParagraphText,
    updateParagraphTranslation,
    updateParagraphTime,
    saveTimeEditHistory,
    addParagraph,
    removeParagraph,
    removeParagraphs,
    shiftParagraphTime,
    undo,
    redo,
    canUndo,
    canRedo,
    undoToStep,
    loadSubtitle,
    loadFromTranscription,
    clearSubtitle,
    setVideoFile,
    setVideoElement,
    setDubbingAudioFile,
    exportToSRT,
    exportToSRTTranslation,
    exportToVTT,
    exportToASS,
    exportAsFormat,
    serializeProject,
    loadProject,
    saveDraft,
    peekDraft,
    clearDraft,
    markSaved,
    draftSavedAt,
    lastDraftError,
    saveSessionSnapshot,
    peekSessionSnapshot,
    clearSessionSnapshot,
    lastSessionError,
    mergeParagraphs,
    applyMergedSubtitles,
    applySplitResults
  }
})
