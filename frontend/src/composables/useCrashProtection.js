import { onMounted, onUnmounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useSettingsStore } from '@/stores/settingsStore'

// 崩溃保护:
// 1. 定时将未保存修改写入 localStorage 草稿(间隔来自设置 fileTask.autoSaveInterval)
// 2. 关闭/刷新窗口前:同步保存草稿,并触发浏览器原生"未保存"确认
// 3. 启动时检测到草稿 → 询问是否恢复
export function useCrashProtection() {
  const subtitleStore = useSubtitleStore()
  const settingsStore = useSettingsStore()

  let timer = null
  let lastDraftErrorNotifyAt = 0

  function notifyDraftErrorOnce() {
    const now = Date.now()
    if (now - lastDraftErrorNotifyAt < 30_000) return // 30s 内不重复提示
    lastDraftErrorNotifyAt = now
    const err = subtitleStore.lastDraftError
    const msg = err?.message || '本地存储不足或写入失败'
    ElMessage.warning(`自动保存草稿失败:${msg}。请及时导出项目文件避免丢失。`)
  }

  function getIntervalMs() {
    const seconds = Number(settingsStore.settings.fileTask.autoSaveInterval) || 60
    return Math.max(10, seconds) * 1000
  }

  function startAutoSave() {
    stopAutoSave()
    const enabled = settingsStore.settings.fileTask.autoSave
    if (!enabled) return
    timer = setInterval(() => {
      if (subtitleStore.paragraphCount > 0) {
        // #5 会话快照:每次周期都刷(无论是否修改过,写入 selectedIndex / showTranslation 最新状态)
        subtitleStore.saveSessionSnapshot()
        if (subtitleStore.isModified) {
          const ok = subtitleStore.saveDraft()
          if (!ok) notifyDraftErrorOnce()
        }
      }
    }, getIntervalMs())
  }

  function stopAutoSave() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function onBeforeUnload(e) {
    // 最后防线:会话快照 + 草稿
    if (subtitleStore.paragraphCount > 0) {
      subtitleStore.saveSessionSnapshot()
    }
    if (subtitleStore.isModified && subtitleStore.paragraphCount > 0) {
      subtitleStore.saveDraft()
      e.preventDefault()
      e.returnValue = ''
    }
  }

  async function promptRestoreDraft() {
    // 优先级:草稿(draft) > 会话快照(last-session)
    let draft = subtitleStore.peekDraft()
    let fromSnapshot = false

    if (!draft && settingsStore.settings.workspace.autoRestoreSession) {
      const snap = subtitleStore.peekSessionSnapshot()
      if (snap) {
        draft = snap
        fromSnapshot = true
      }
    }
    if (!draft) return

    const time = draft.savedAt ? new Date(draft.savedAt).toLocaleString() : '未知时间'
    const count = draft.subtitle.paragraphs.length
    const label = fromSnapshot ? '上次打开的会话' : (draft.draft ? '未保存的编辑草稿' : '上次保存的项目')

    try {
      await ElMessageBox.confirm(
        `检测到${label}:${draft.subtitle.fileName || '未命名'}(${count} 行字幕),保存于 ${time}。是否恢复?`,
        '恢复工作区',
        {
          confirmButtonText: '恢复',
          cancelButtonText: '丢弃',
          type: 'info',
          distinguishCancelAndClose: false
        }
      )
      const result = subtitleStore.loadProject(draft)
      if (result) {
        const media = result.media || {}
        if (media.videoPath && window.electronAPI) {
          subtitleStore.setVideoFile(media.videoPath)
        }
        document.title = `${draft.subtitle.fileName || '恢复的工作区'} - 字幕编辑工具`
      }
      // 恢复后也把快照清掉,避免下次再问(草稿会在正常保存时被 markSaved 清理)
      if (fromSnapshot) subtitleStore.clearSessionSnapshot()
    } catch {
      // 用户选择丢弃
      subtitleStore.clearDraft()
      if (fromSnapshot) subtitleStore.clearSessionSnapshot()
    }
  }

  onMounted(() => {
    startAutoSave()
    promptRestoreDraft()
    window.addEventListener('beforeunload', onBeforeUnload)
  })

  onUnmounted(() => {
    stopAutoSave()
    window.removeEventListener('beforeunload', onBeforeUnload)
  })
}
