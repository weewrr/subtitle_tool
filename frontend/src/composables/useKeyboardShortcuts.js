import { onMounted, onUnmounted } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useCommandStore } from '@/stores/commandStore'
import { useAppActions } from '@/composables/useAppActions'

// 全局键盘流:
// ↑/↓ 选择上一/下一行 · Enter 播放当前行 · Space 播放暂停
// ←/→ 视频快退/快进 5 秒
// Shift+←/→ 当前字幕起点 -/+0.1s · Alt+←/→ 当前字幕终点 -/+0.1s
// Ctrl+Z 撤销 · Ctrl+Y/Ctrl+Shift+Z 重做 · Ctrl+S 导出 · Ctrl+Shift+S 保存项目
// Ctrl+K 命令面板 · ? 快捷键速查 · Esc 关闭浮层
const NUDGE_MS = 100
const SEEK_S = 5

export function useKeyboardShortcuts() {
  const subtitleStore = useSubtitleStore()
  const commandStore = useCommandStore()
  const { saveOriginalSubtitle, saveProject } = useAppActions()

  function isTyping() {
    const el = document.activeElement
    if (!el) return false
    const tag = el.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
  }

  function modalOpen() {
    // Element Plus 模态对话框(含确认框)打开时,暂停表格级快捷键
    return !!document.querySelector('.el-overlay:not([style*="display: none"])')
  }

  function uiLayerOpen() {
    return commandStore.paletteVisible || commandStore.shortcutsVisible
  }

  function selectRelative(delta) {
    const count = subtitleStore.paragraphCount
    if (count === 0) return
    const cur = subtitleStore.selectedParagraphIndex
    const next = Math.max(0, Math.min(count - 1, (cur < 0 ? (delta > 0 ? -1 : 0) : cur) + delta))
    subtitleStore.selectParagraph(next)
  }

  function playCurrentParagraph() {
    const p = subtitleStore.selectedParagraph
    const video = subtitleStore.videoElement
    if (!p || !video) return
    video.currentTime = p.startTime.totalMilliseconds / 1000
    video.play().catch(() => {})
  }

  function togglePlay() {
    const video = subtitleStore.videoElement
    if (!video) return
    if (video.paused) video.play().catch(() => {})
    else video.pause()
  }

  function seek(delta) {
    const video = subtitleStore.videoElement
    if (!video || !video.duration) return
    video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + delta))
  }

  function nudgeTime(dStart, dEnd) {
    const i = subtitleStore.selectedParagraphIndex
    const p = subtitleStore.currentSubtitle.paragraphs[i]
    if (!p) return
    const s = p.startTime.totalMilliseconds + dStart
    const e = p.endTime.totalMilliseconds + dEnd
    subtitleStore.updateParagraphTime(i, s, e)
  }

  function focusEditPanel() {
    const textarea = document.querySelector('.edit-panel textarea, .edit-panel input[type="text"]')
    if (textarea) {
      textarea.focus()
      textarea.select?.()
    }
  }

  function onKeyDown(e) {
    // 命令面板 / 速查浮层打开时,只处理 Esc
    if (uiLayerOpen()) {
      if (e.key === 'Escape') {
        commandStore.togglePalette(false)
        commandStore.toggleShortcuts(false)
        e.preventDefault()
      }
      return
    }

    // Ctrl+K / Cmd+K:命令面板(输入状态也允许)
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      commandStore.togglePalette(true)
      e.preventDefault()
      return
    }

    // 以下快捷键在输入框/模态框中不生效
    if (isTyping() || modalOpen()) return

    // Ctrl+Z/Ctrl+Y/Ctrl+Shift+Z/Ctrl+S:撤销/重做/保存
    if ((e.ctrlKey || e.metaKey) && !e.altKey) {
      const k = e.key.toLowerCase()
      if (k === 'z' && !e.shiftKey) {
        subtitleStore.undo()
        e.preventDefault()
        return
      }
      if ((k === 'z' && e.shiftKey) || k === 'y') {
        subtitleStore.redo()
        e.preventDefault()
        return
      }
      if (k === 's') {
        if (e.shiftKey) saveProject()
        else saveOriginalSubtitle()
        e.preventDefault()
        return
      }
    }

    // ?:快捷键速查
    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
      commandStore.toggleShortcuts(true)
      e.preventDefault()
      return
    }

    switch (e.key) {
      case 'ArrowUp':
        if (!e.altKey && !e.shiftKey) { selectRelative(-1); e.preventDefault() }
        break
      case 'ArrowDown':
        if (!e.altKey && !e.shiftKey) { selectRelative(1); e.preventDefault() }
        break
      case 'Enter':
        if (e.ctrlKey || e.metaKey) { focusEditPanel() } else { playCurrentParagraph() }
        e.preventDefault()
        break
      case ' ':
        togglePlay()
        e.preventDefault()
        break
      case 'ArrowLeft':
        if (e.shiftKey) nudgeTime(-NUDGE_MS, 0)
        else if (e.altKey) nudgeTime(0, -NUDGE_MS)
        else seek(-SEEK_S)
        e.preventDefault()
        break
      case 'ArrowRight':
        if (e.shiftKey) nudgeTime(NUDGE_MS, 0)
        else if (e.altKey) nudgeTime(0, NUDGE_MS)
        else seek(SEEK_S)
        e.preventDefault()
        break
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeyDown))
  onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
}
