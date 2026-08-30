import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { useRecentFilesStore, FILE_TYPES } from '@/stores/recentFilesStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useCommandStore } from '@/stores/commandStore'

// 应用动作中心:把 MenuBar 中的全部操作抽为可复用函数,
// 供菜单栏、命令面板(Ctrl+K)、全局拖放共用,保证行为一致。

const SUBTITLE_EXTS = ['.srt', '.vtt', '.sub', '.ass', '.ssa']
const VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.ts', '.m4v']
const AUDIO_EXTS = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']

export function useAppActions() {
  const subtitleStore = useSubtitleStore()
  const uiStore = useUIStore()
  const recentFilesStore = useRecentFilesStore()
  const settingsStore = useSettingsStore()

  const hasSubtitle = computed(() => subtitleStore.paragraphCount > 0)
  const hasTranslation = computed(() => subtitleStore.hasTranslation)

  const isDark = computed(() => {
    const theme = settingsStore.settings.workspace.theme
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return theme === 'dark'
  })

  // ---------- 主题 ----------
  function toggleTheme() {
    const next = isDark.value ? 'light' : 'dark'
    settingsStore.settings.workspace.theme = next
    settingsStore.applyTheme()
    settingsStore.saveToStorage()
  }

  // ---------- 文件选择 ----------
  function pickFile(accept, onPick) {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = accept
    input.style.display = 'none'
    input.onchange = (e) => {
      const file = e.target.files[0]
      if (file) onPick(file)
      input.remove()
    }
    document.body.appendChild(input)
    input.click()
  }

  function openSubtitleFile() {
    if (window.electronAPI) {
      openSubtitleFileElectron()
    } else {
      pickFile('.srt,.vtt,.sub,.ass,.ssa', loadSubtitleFile)
    }
  }

  async function openSubtitleFileElectron() {
    const result = await window.electronAPI.selectSubtitleFile()
    if (result.success) {
      loadSubtitleContent(result.content, result.fileName, result.filePath)
    }
  }

  function loadSubtitleFile(file) {
    const reader = new FileReader()
    reader.onload = (event) => {
      loadSubtitleContent(event.target.result, file.name, file.path)
    }
    reader.readAsText(file)
  }

  function loadSubtitleContent(content, fileName, filePath) {
    const success = subtitleStore.loadSubtitle(content, fileName)
    if (success) {
      document.title = `${fileName} - 字幕编辑工具`
      subtitleStore.clearDraft()
      ElMessage.success(`已加载字幕文件: ${fileName}`)
      if (filePath) {
        recentFilesStore.addRecentFile(filePath, fileName, FILE_TYPES.SUBTITLE)
      }
    } else {
      ElMessage.error('无法识别的字幕文件格式')
    }
  }

  function openVideoFile() {
    if (window.electronAPI) {
      openVideoFileElectron()
    } else {
      pickFile('video/*', (file) => loadVideoFile(file))
    }
  }

  async function openVideoFileElectron() {
    const result = await window.electronAPI.selectVideoFile()
    if (result.success) {
      loadVideoFile(result.filePath, result.fileName)
    }
  }

  function loadVideoFile(fileOrPath, nameOverride) {
    const name = nameOverride || (typeof fileOrPath === 'string'
      ? fileOrPath.split(/[/\\]/).pop()
      : fileOrPath.name)
    subtitleStore.setVideoFile(fileOrPath)
    ElMessage.success(`已加载视频文件: ${name}`)
    const path = typeof fileOrPath === 'string' ? fileOrPath : fileOrPath.path
    if (path) {
      recentFilesStore.addRecentFile(path, name, FILE_TYPES.VIDEO)
    }
  }

  function loadAudioFile(fileOrPath) {
    const name = typeof fileOrPath === 'string'
      ? fileOrPath.split(/[/\\]/).pop()
      : fileOrPath.name
    subtitleStore.setDubbingAudioFile(fileOrPath)
    ElMessage.success(`已加载音频文件: ${name}`)
    const path = typeof fileOrPath === 'string' ? fileOrPath : fileOrPath.path
    if (path) {
      recentFilesStore.addRecentFile(path, name, FILE_TYPES.AUDIO)
    }
  }

  // ---------- 拖放路由 ----------
  function handleDroppedFiles(fileList) {
    const files = Array.from(fileList || [])
    if (!files.length) return
    for (const file of files) {
      const name = (typeof file === 'string' ? file : file.name) || ''
      const ext = name.toLowerCase().match(/\.[^.]+$/)?.[0] || ''
      const isVideo = VIDEO_EXTS.includes(ext) || (!ext && file.type?.startsWith('video/'))
      const isAudio = AUDIO_EXTS.includes(ext) || (!ext && file.type?.startsWith('audio/'))

      if (ext === '.stproj') {
        loadProjectFile(file)
      } else if (SUBTITLE_EXTS.includes(ext)) {
        loadSubtitleFile(file)
      } else if (isVideo) {
        loadVideoFile(file)
      } else if (isAudio) {
        loadAudioFile(file)
      } else {
        ElMessage.warning(`不支持的文件类型: ${name}`)
      }
    }
  }

  // ---------- 最近文件 ----------
  async function openRecentFile(file) {
    if (!window.electronAPI) {
      ElMessage.warning('此功能仅在Electron环境下可用')
      return
    }

    if (file.type === FILE_TYPES.SUBTITLE) {
      const result = await window.electronAPI.readFile(file.path)
      if (result.success) {
        loadSubtitleContent(result.content, result.fileName, result.filePath)
      } else {
        ElMessage.error(`打开文件失败: ${result.error}`)
        recentFilesStore.removeRecentFile(file.path)
      }
    } else if (file.type === FILE_TYPES.VIDEO) {
      loadVideoFile(file.path, file.name)
    } else if (file.type === FILE_TYPES.AUDIO) {
      loadAudioFile(file.path)
    }
  }

  function clearRecentFiles() {
    recentFilesStore.clearRecentFiles()
    ElMessage.success('已清除历史记录')
  }

  // ---------- 保存 ----------
  async function saveTranslatedSubtitle() {
    if (subtitleStore.paragraphCount === 0) {
      ElMessage.warning('没有可保存的字幕')
      return
    }
    const content = subtitleStore.exportToSRTTranslation()
    const defaultName = `${subtitleStore.currentSubtitle.fileName.replace(/\.[^/.]+$/, '')}_translated.srt`
    await saveFileWithPicker(content, defaultName)
  }

  async function saveOriginalSubtitle() {
    if (subtitleStore.paragraphCount === 0) {
      ElMessage.warning('没有可保存的字幕')
      return
    }
    const content = subtitleStore.exportToSRT()
    await saveFileWithPicker(content, subtitleStore.currentSubtitle.fileName)
  }

  async function saveFileWithPicker(content, defaultName, extensions = ['srt', 'vtt', 'ass', 'sub']) {
    // 1) Electron:原生保存对话框
    if (window.electronAPI?.saveTextFile) {
      try {
        const result = await window.electronAPI.saveTextFile({ content, defaultName, extensions })
        if (result.success) {
          subtitleStore.markSaved()
          ElMessage.success('保存成功')
        } else if (result.error) {
          ElMessage.error(`保存失败: ${result.error}`)
        }
      } catch (err) {
        ElMessage.error(`保存失败: ${err.message}`)
      }
      return
    }
    // 2) 浏览器:文件系统访问 API
    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: defaultName,
          types: [{
            description: '字幕文件',
            accept: { 'text/plain': extensions.map(e => '.' + e) }
          }]
        })
        const writable = await handle.createWritable()
        await writable.write(content)
        await writable.close()
        subtitleStore.markSaved()
        ElMessage.success('保存成功')
      } catch (err) {
        if (err.name !== 'AbortError') {
          ElMessage.error(`保存失败: ${err.message}`)
        }
      }
      return
    }
    // 3) 兜底:下载
    downloadFile(content, defaultName)
    subtitleStore.markSaved()
    ElMessage.success('保存成功')
  }

  function downloadFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function closeSubtitle() {
    if (subtitleStore.paragraphCount === 0) {
      ElMessage.info('当前没有打开的字幕文件')
      return
    }
    subtitleStore.clearSubtitle()
    subtitleStore.clearDraft()
    document.title = '字幕编辑工具'
    ElMessage.success('已关闭字幕文件')
  }

  function showExportDialog() {
    if (!requireSubtitle()) return
    uiStore.showExportDialog()
  }

  // ---------- 通用格式导出(srt/vtt/ass/txt,可选译文) ----------
  async function exportAs(format, useTranslation = false) {
    if (!requireSubtitle()) return
    if (useTranslation && !subtitleStore.hasTranslation) {
      ElMessage.warning('当前字幕没有翻译文本')
      return
    }
    const content = subtitleStore.exportAsFormat(format, useTranslation)
    const base = (subtitleStore.currentSubtitle.fileName || 'Untitled').replace(/\.[^/.]+$/, '')
    const suffix = useTranslation ? '_translated' : ''
    await saveFileWithPicker(content, `${base}${suffix}.${format}`, [format])
  }

  // ---------- 项目文件(.stproj):完整工作区 ----------
  async function saveProject() {
    if (!requireSubtitle()) return
    const data = subtitleStore.serializeProject()
    const base = (subtitleStore.currentSubtitle.fileName || '未命名项目').replace(/\.[^/.]+$/, '')
    await saveFileWithPicker(JSON.stringify(data, null, 2), `${base}.stproj`, ['stproj'])
  }

  function openProjectFile() {
    if (window.electronAPI?.selectProjectFile) {
      openProjectFileElectron()
    } else {
      pickFile('.stproj', loadProjectFile)
    }
  }

  async function openProjectFileElectron() {
    const result = await window.electronAPI.selectProjectFile()
    if (result.success) {
      try {
        applyProject(JSON.parse(result.content), result.fileName)
      } catch {
        ElMessage.error('项目文件已损坏或格式不正确')
      }
    } else if (result.error) {
      ElMessage.error(`打开项目失败: ${result.error}`)
    }
  }

  function loadProjectFile(file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        applyProject(JSON.parse(e.target.result), file.name)
      } catch {
        ElMessage.error('项目文件已损坏或格式不正确')
      }
    }
    reader.readAsText(file)
  }

  function applyProject(data, fileName) {
    const result = subtitleStore.loadProject(data)
    if (!result) {
      ElMessage.error('无法识别的项目文件(仅支持本软件生成的 .stproj 项目)')
      return
    }
    document.title = `${fileName} - 字幕编辑工具`
    subtitleStore.clearDraft()
    const n = subtitleStore.paragraphCount
    ElMessage.success(`已打开项目: ${fileName}(${n} 行字幕)`)

    // 重连媒体:桌面版按路径自动恢复;浏览器版提示手动加载
    const media = result.media || {}
    if (media.videoPath && window.electronAPI) {
      subtitleStore.setVideoFile(media.videoPath)
    } else if (media.videoPath) {
      ElMessage.info('项目引用了视频文件,网页版请手动重新加载')
    }
    if (media.dubbingAudioPath && window.electronAPI) {
      subtitleStore.setDubbingAudioFile(media.dubbingAudioPath)
    }
  }

  function exitApp() {
    if (confirm('确定要退出吗？')) {
      window.close()
    }
  }

  // ---------- 工具弹窗(带前置校验) ----------
  function requireSubtitle() {
    if (subtitleStore.paragraphCount === 0) {
      ElMessage.warning('请先打开字幕文件')
      return false
    }
    return true
  }

  function showFindDialog() { if (requireSubtitle()) uiStore.showFindDialog() }
  function findNext() { if (requireSubtitle()) uiStore.showFindDialog() }
  function showReplaceDialog() { if (requireSubtitle()) uiStore.showReplaceDialog() }
  function showMultiReplaceDialog() { if (requireSubtitle()) uiStore.showMultiReplaceDialog() }
  function showGoToDialog() { if (requireSubtitle()) uiStore.showGoToLineDialog({ maxLine: subtitleStore.paragraphCount }) }
  function checkSpelling() { if (requireSubtitle()) uiStore.showSpellCheckDialog() }
  function findDuplicateWords() { if (requireSubtitle()) uiStore.showFindDuplicateWordsDialog() }
  function findDuplicateLines() { if (requireSubtitle()) uiStore.showFindDuplicateLinesDialog() }
  function mergeSentences() { if (requireSubtitle()) uiStore.showMergeSentencesModal() }
  function splitLongLines() { if (requireSubtitle()) uiStore.showSplitLongLinesModal() }

  // ---------- 视频/语音 ----------
  function closeVideo() {
    subtitleStore.setVideoFile(null)
    subtitleStore.setVideoElement(null)
    ElMessage.info('已关闭视频')
  }

  function embedHardSubtitles() {
    if (!subtitleStore.videoFile || subtitleStore.paragraphCount === 0) {
      ElMessage.warning('请先打开视频和字幕文件')
      return
    }
    uiStore.showHardSubtitleModal()
  }

  function showSpeechRecognition() {
    uiStore.showSpeechRecognitionModal()
  }

  function addTtsToVideo() {
    if (!subtitleStore.videoFile) {
      ElMessage.warning('请先在视频区域打开视频文件')
      return
    }
    if (!subtitleStore.dubbingAudioFile) {
      ElMessage.warning('请先在文本转语音区域加载配音音频')
      return
    }
    uiStore.showAddTtsToVideoModal()
  }

  function showTranslate() {
    uiStore.showTranslateModal()
  }

  function showSettings() {
    uiStore.showSettingsDialog()
  }

  function toggleTranslationColumn() {
    subtitleStore.showTranslation = !subtitleStore.showTranslation
  }

  // ---------- 时间码整体平移(全部行) ----------
  async function shiftAllTimes() {
    if (!requireSubtitle()) return
    try {
      const { value } = await ElMessageBox.prompt(
        '输入偏移秒数(负数提前,正数延后),将应用到全部字幕行',
        '时间码整体平移',
        {
          confirmButtonText: '应用',
          cancelButtonText: '取消',
          inputPattern: /^-?\d+(\.\d+)?$/,
          inputErrorMessage: '请输入数字,如 -0.5 或 1.2'
        }
      )
      const seconds = parseFloat(value)
      if (seconds && subtitleStore.shiftParagraphTime(null, seconds * 1000)) {
        ElMessage.success(`全部字幕已${seconds > 0 ? '延后' : '提前'} ${Math.abs(seconds)}s`)
      }
    } catch {
      // 用户取消
    }
  }

  // ---------- 撤销 ----------
  function undoLastEdit() {
    if (subtitleStore.currentSubtitle?.historyItems?.length === 0) {
      ElMessage.info('没有可撤销的操作')
      return
    }
    if (subtitleStore.undo()) {
      ElMessage.success('已撤销')
    } else {
      ElMessage.info('没有可撤销的操作')
    }
  }

  // ---------- 重做 ----------
  function redoLastEdit() {
    if (subtitleStore.redo()) {
      ElMessage.success('已重做')
    } else {
      ElMessage.info('没有可重做的操作')
    }
  }

  // ---------- 命令注册表(供 Ctrl+K 命令面板消费) ----------
  const commands = [
    // 文件
    { id: 'openSubtitle', group: '文件', label: '打开字幕文件', keywords: ['open', 'subtitle', 'srt'], action: openSubtitleFile },
    { id: 'openVideo', group: '文件', label: '打开视频文件', keywords: ['open', 'video', 'mp4'], action: openVideoFile },
    { id: 'openProject', group: '文件', label: '打开项目文件', keywords: ['open', 'project', 'stproj', '项目'], action: openProjectFile },
    { id: 'saveProject', group: '文件', label: '保存项目', shortcut: 'Ctrl+Shift+S', keywords: ['save', 'project', 'stproj', '项目'], action: saveProject },
    { id: 'saveOriginal', group: '文件', label: '保存原始字幕', shortcut: 'Ctrl+S', keywords: ['save', 'srt'], action: saveOriginalSubtitle },
    { id: 'saveTranslated', group: '文件', label: '保存翻译字幕', keywords: ['save', 'translated'], action: saveTranslatedSubtitle },
    { id: 'exportDialog', group: '文件', label: '导出字幕(格式转换)', keywords: ['export', 'vtt', 'ass', 'txt', '导出'], action: showExportDialog },
    { id: 'closeSubtitle', group: '文件', label: '关闭字幕', keywords: ['close'], action: closeSubtitle },
    { id: 'closeVideo', group: '文件', label: '关闭视频', keywords: ['close', 'video'], action: closeVideo },
    { id: 'settings', group: '文件', label: '打开设置', shortcut: 'Ctrl+,', keywords: ['settings', 'preference'], action: showSettings },
    // 编辑
    { id: 'undo', group: '编辑', label: '撤销', shortcut: 'Ctrl+Z', keywords: ['undo', 'history'], action: undoLastEdit },
    { id: 'redo', group: '编辑', label: '重做', shortcut: 'Ctrl+Y', keywords: ['redo', 'history'], action: redoLastEdit },
    { id: 'shiftAllTimes', group: '编辑', label: '时间码整体平移(全部行)', keywords: ['shift', 'offset', 'sync', '平移'], action: shiftAllTimes },
    { id: 'find', group: '编辑', label: '查找', shortcut: 'Ctrl+F', keywords: ['find', 'search'], action: showFindDialog },
    { id: 'replace', group: '编辑', label: '替换', shortcut: 'Ctrl+H', keywords: ['replace'], action: showReplaceDialog },
    { id: 'multiReplace', group: '编辑', label: '多重替换', keywords: ['replace', 'batch'], action: showMultiReplaceDialog },
    { id: 'goTo', group: '编辑', label: '转到字幕编号', shortcut: 'Ctrl+G', keywords: ['goto', 'line'], action: showGoToDialog },
    // 拼写检查
    { id: 'spellCheck', group: '检查', label: '拼写检查', keywords: ['spell'], action: checkSpelling },
    { id: 'findDuplicateWords', group: '检查', label: '查找重复词', keywords: ['duplicate', 'words'], action: findDuplicateWords },
    { id: 'findDuplicateLines', group: '检查', label: '查找重复行', keywords: ['duplicate', 'lines'], action: findDuplicateLines },
    // 视频 / 语音
    { id: 'speechRecognition', group: '视频 / 语音', label: '语音识别(生成字幕)', keywords: ['transcribe', 'whisper', 'asr'], action: showSpeechRecognition },
    { id: 'embedHardSubtitles', group: '视频 / 语音', label: '生成带硬字幕的视频', keywords: ['hard', 'burn', 'ffmpeg'], action: embedHardSubtitles },
    { id: 'addTtsToVideo', group: '视频 / 语音', label: '文本转语音添加到视频', keywords: ['tts', 'dub'], action: addTtsToVideo },
    // 字幕处理
    { id: 'translate', group: '字幕处理', label: '自动翻译', keywords: ['translate'], action: showTranslate },
    { id: 'mergeSentences', group: '字幕处理', label: '合并句子', keywords: ['merge'], action: mergeSentences },
    { id: 'splitLongLines', group: '字幕处理', label: '分割长行', keywords: ['split'], action: splitLongLines },
    // 视图
    { id: 'toggleTheme', group: '视图', label: '切换深色 / 浅色主题', keywords: ['theme', 'dark', 'light'], action: toggleTheme },
    { id: 'toggleTranslationColumn', group: '视图', label: '切换翻译列显示', keywords: ['translation', 'column'], action: toggleTranslationColumn },
    { id: 'shortcuts', group: '视图', label: '查看键盘快捷键', shortcut: '?', keywords: ['shortcuts', 'help'], action: () => useCommandStore().toggleShortcuts(true) }
  ]

  return {
    // 状态
    hasSubtitle,
    hasTranslation,
    isDark,
    commands,
    // 文件
    openSubtitleFile,
    openVideoFile,
    loadSubtitleFile,
    loadSubtitleContent,
    loadVideoFile,
    loadAudioFile,
    handleDroppedFiles,
    openRecentFile,
    clearRecentFiles,
    saveOriginalSubtitle,
    saveTranslatedSubtitle,
    closeSubtitle,
    showExportDialog,
    exportAs,
    saveProject,
    openProjectFile,
    exitApp,
    // 弹窗与操作
    showFindDialog,
    findNext,
    showReplaceDialog,
    showMultiReplaceDialog,
    showGoToDialog,
    checkSpelling,
    findDuplicateWords,
    findDuplicateLines,
    closeVideo,
    embedHardSubtitles,
    showSpeechRecognition,
    addTtsToVideo,
    showTranslate,
    mergeSentences,
    splitLongLines,
    showSettings,
    toggleTheme,
    toggleTranslationColumn,
    shiftAllTimes,
    undoLastEdit,
    redoLastEdit
  }
}
