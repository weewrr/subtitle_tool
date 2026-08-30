<template>
  <el-config-provider :locale="zhCn">
    <div
      class="app-container"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent
      @dragleave="onDragLeave"
      @drop.prevent="onDrop"
    >
      <MenuBar />

      <div class="workbench">
        <SplitPane
          :vertical="false"
          :initial-split="58"
          :min-first-size="400"
          :min-second-size="250"
          class="main-split"
        >
          <template #first>
            <SplitPane
              :vertical="true"
              :initial-split="55"
              :min-first-size="400"
              :min-second-size="400"
              class="top-split"
            >
              <template #first>
                <div class="left-panel">
                  <VideoPlayer />
                  <VideoControls />
                </div>
              </template>
              <template #second>
                <div class="right-panel">
                  <SubtitleList />
                  <EditPanel />
                </div>
              </template>
            </SplitPane>
          </template>
          <template #second>
            <SplitPane
              :vertical="true"
              :initial-split="50"
              :min-first-size="300"
              :min-second-size="300"
              class="bottom-split"
            >
              <template #first>
                <div class="bottom-left">
                  <TtsPanel />
                </div>
              </template>
              <template #second>
                <div class="bottom-right">
                  <WaveformPanel />
                </div>
              </template>
            </SplitPane>
          </template>
        </SplitPane>
      </div>

      <StatusBar />

      <!-- 拖放投放覆盖层 -->
      <Transition name="drop-fade">
        <div v-if="dragDepth > 0" class="drop-overlay" aria-hidden="true">
          <div class="drop-card">
            <el-icon :size="40"><Download /></el-icon>
            <div class="drop-title">释放以加载文件</div>
            <div class="drop-hints">
              <span class="drop-chip">视频 → 播放器</span>
              <span class="drop-chip">音频 → 配音轨</span>
              <span class="drop-chip">字幕 → 编辑器</span>
            </div>
          </div>
        </div>
      </Transition>

      <SpeechRecognitionModal />
      <BatchProcessingModal />
      <ModelDownloadModal />
      <TranslateModal />
      <TranslateAdvancedModal />
      <ConfirmDialog />
      <FindDialog />
      <ReplaceDialog />
      <MultiReplaceDialog />
      <GoToLineDialog />
      <SpellCheckDialog />
      <FindDuplicateWordsDialog />
      <FindDuplicateLinesDialog />
      <MergeSentencesModal />
      <SplitLongLinesModal />
      <SplitLongLinesAdvancedModal />
      <HardSubtitleModal ref="hardSubtitleModalRef" />
      <AddTtsToVideoModal />
      <SettingsDialog :visible="uiStore.settingsDialogVisible" @update:visible="uiStore.hideSettingsDialog" />
      <ModelConfigModal />
      <ExportDialog />

      <!-- 交互层:命令面板 / 快捷键速查 / 任务坞 -->
      <CommandPalette />
      <ShortcutsOverlay />
      <TaskDock />
    </div>
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { ref, watch } from 'vue'
import MenuBar from '@/components/MenuBar.vue'
import VideoPlayer from '@/components/VideoPlayer.vue'
import VideoControls from '@/components/VideoControls.vue'
import SubtitleList from '@/components/SubtitleList.vue'
import EditPanel from '@/components/EditPanel.vue'
import TtsPanel from '@/components/TtsPanel.vue'
import WaveformPanel from '@/components/WaveformPanel.vue'
import StatusBar from '@/components/StatusBar.vue'
import SplitPane from '@/components/SplitPane.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import ShortcutsOverlay from '@/components/ShortcutsOverlay.vue'
import TaskDock from '@/components/TaskDock.vue'
import SpeechRecognitionModal from '@/components/modals/SpeechRecognitionModal.vue'
import BatchProcessingModal from '@/components/modals/BatchProcessingModal.vue'
import ModelDownloadModal from '@/components/modals/ModelDownloadModal.vue'
import TranslateModal from '@/components/modals/TranslateModal.vue'
import TranslateAdvancedModal from '@/components/modals/TranslateAdvancedModal.vue'
import ConfirmDialog from '@/components/modals/ConfirmDialog.vue'
import FindDialog from '@/components/modals/FindDialog.vue'
import ReplaceDialog from '@/components/modals/ReplaceDialog.vue'
import MultiReplaceDialog from '@/components/modals/MultiReplaceDialog.vue'
import GoToLineDialog from '@/components/modals/GoToLineDialog.vue'
import SpellCheckDialog from '@/components/modals/SpellCheckDialog.vue'
import FindDuplicateWordsDialog from '@/components/modals/FindDuplicateWordsDialog.vue'
import FindDuplicateLinesDialog from '@/components/modals/FindDuplicateLinesDialog.vue'
import MergeSentencesModal from '@/components/modals/MergeSentencesModal.vue'
import SplitLongLinesModal from '@/components/modals/SplitLongLinesModal.vue'
import SplitLongLinesAdvancedModal from '@/components/modals/SplitLongLinesAdvancedModal.vue'
import HardSubtitleModal from '@/components/modals/HardSubtitleModal.vue'
import AddTtsToVideoModal from '@/components/modals/AddTtsToVideoModal.vue'
import SettingsDialog from '@/components/modals/SettingsDialog.vue'
import ModelConfigModal from '@/components/modals/ModelConfigModal.vue'
import ExportDialog from '@/components/modals/ExportDialog.vue'
import { useUIStore } from '@/stores/uiStore'
import { useCommandStore } from '@/stores/commandStore'
import { useAppActions } from '@/composables/useAppActions'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useCrashProtection } from '@/composables/useCrashProtection'
import { onMounted, onBeforeUnmount } from 'vue'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { ElMessage, ElMessageBox } from 'element-plus'

const uiStore = useUIStore()
const commandStore = useCommandStore()
const subtitleStore = useSubtitleStore()
const { commands, handleDroppedFiles } = useAppActions()

// 注册命令面板指令集
commandStore.register(commands)

// 启用全局键盘流
useKeyboardShortcuts()

// 崩溃保护:草稿自动保存 + 未保存关闭拦截 + 启动恢复
useCrashProtection()

const hardSubtitleModalRef = ref(null)

watch(() => uiStore.hardSubtitleModalVisible, (newVal) => {
  if (newVal && hardSubtitleModalRef.value) {
    hardSubtitleModalRef.value.open()
  }
})

// ============================================================
// 全局拖放:任意位置拖入文件即加载
// ============================================================
const dragDepth = ref(0)

function onDragEnter(e) {
  if (e.dataTransfer?.types?.includes('Files')) {
    dragDepth.value++
  }
}

function onDragLeave() {
  if (dragDepth.value > 0) dragDepth.value--
}

function onDrop(e) {
  dragDepth.value = 0
  const files = e.dataTransfer?.files
  if (files?.length) {
    handleDroppedFiles(files)
  }
}

// ============================================================
// 应用生命周期:文件关联 + 未保存拦截(双击 .stproj 打开)
// ============================================================
let removeOpenProjectListener = null

async function confirmDiscardIfModified() {
  if (!subtitleStore.isModified || subtitleStore.paragraphCount === 0) return true
  try {
    await ElMessageBox.confirm(
      '当前工作区有未保存的修改,打开新项目将丢弃这些内容。确定继续?',
      '未保存修改',
      { type: 'warning', confirmButtonText: '丢弃并打开', cancelButtonText: '取消' }
    )
    return true
  } catch {
    return false
  }
}

function handleOpenProjectEvent(payload) {
  const { content, fileName, filePath } = payload || {}
  if (!content || !filePath) return
  // 打开前与草稿恢复互斥:若有未保存修改则需要用户确认
  confirmDiscardIfModified().then((ok) => {
    if (!ok) return
    try {
      const data = JSON.parse(content)
      const result = subtitleStore.loadProject(data)
      if (!result) {
        ElMessage.error('无法识别的项目文件(仅支持本软件生成的 .stproj)')
        return
      }
      document.title = `${fileName} - 字幕编辑工具`
      subtitleStore.clearDraft()
      const n = subtitleStore.paragraphCount
      ElMessage.success(`已打开项目: ${fileName}(${n} 行字幕)`)
      const media = result.media || {}
      if (media.videoPath && window.electronAPI) subtitleStore.setVideoFile(media.videoPath)
      if (media.dubbingAudioPath && window.electronAPI) subtitleStore.setDubbingAudioFile(media.dubbingAudioPath)
    } catch {
      ElMessage.error('项目文件已损坏或格式不正确')
    }
  })
}

onMounted(() => {
  if (window.electronAPI?.onOpenProject) {
    removeOpenProjectListener = window.electronAPI.onOpenProject(handleOpenProjectEvent)
  }
})

onBeforeUnmount(() => {
  if (typeof removeOpenProjectListener === 'function') {
    removeOpenProjectListener()
  }
})
</script>

<style lang="scss">
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// 工作台:以应用底色作为面板间沟槽(Swiss 网格感)
.workbench {
  flex: 1;
  min-height: 0;
  padding: 8px;
  background: var(--app-bg);
}

.main-split,
.top-split,
.bottom-split {
  width: 100%;
  height: 100%;
}

.left-panel,
.right-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  min-height: 0;
}

.bottom-left,
.bottom-right {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: $border-radius;
  box-shadow: var(--app-shadow-sm);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
</style>
