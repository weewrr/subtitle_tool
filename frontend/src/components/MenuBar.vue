<template>
  <div class="menu-bar">
    <el-menu mode="horizontal" :ellipsis="false">
      <el-sub-menu index="file" class="hide-arrow">
        <template #title>文件</template>
        <el-menu-item index="openSubtitle" @click="openSubtitleFile">
          <el-icon><FolderOpened /></el-icon>打开字幕
        </el-menu-item>
        <el-sub-menu index="reopen" :disabled="recentFilesStore.recentFiles.length === 0">
          <template #title>
            <el-icon><Clock /></el-icon>重新打开
          </template>
          <el-menu-item 
            v-for="file in recentFilesStore.recentFiles" 
            :key="file.path" 
            :index="file.path"
            @click="openRecentFile(file)"
          >
            <el-icon>
              <VideoPlay v-if="file.type === 'video'" />
              <Headset v-else-if="file.type === 'audio'" />
              <Document v-else />
            </el-icon>{{ file.name }}
          </el-menu-item>
          <el-menu-item index="clearRecent" @click="clearRecentFiles">
            <el-icon><Delete /></el-icon>清除历史记录
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="saveTranslated" @click="saveTranslatedSubtitle" :disabled="!hasTranslation">
          <el-icon><Download /></el-icon>保存翻译字幕
        </el-menu-item>
        <el-menu-item index="saveOriginal" @click="saveOriginalSubtitle">
          <el-icon><Document /></el-icon>保存原始字幕
        </el-menu-item>
        <el-menu-item index="closeSubtitle" @click="closeSubtitle" :disabled="!hasSubtitle">
          <el-icon><DocumentRemove /></el-icon>关闭字幕
        </el-menu-item>
        <el-menu-item index="exit" @click="exitApp">
          <el-icon><Close /></el-icon>退出
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="edit" class="hide-arrow">
        <template #title>编辑</template>
        <el-menu-item index="find" @click="showFindDialog">
          <el-icon><Search /></el-icon>查找
        </el-menu-item>
        <el-menu-item index="findNext" @click="findNext">
          <el-icon><Bottom /></el-icon>查找下一个
        </el-menu-item>
        <el-menu-item index="replace" @click="showReplaceDialog">
          <el-icon><Edit /></el-icon>替换
        </el-menu-item>
        <el-menu-item index="multiReplace" @click="showMultiReplaceDialog">
          <el-icon><DocumentCopy /></el-icon>多重替换
        </el-menu-item>
        <el-menu-item index="goTo" @click="showGoToDialog">
          <el-icon><Position /></el-icon>转到字幕编号
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="spellCheck" class="hide-arrow">
        <template #title>拼写检查</template>
        <el-menu-item index="checkSpelling" @click="checkSpelling">
          <el-icon><EditPen /></el-icon>拼写检查
        </el-menu-item>
        <el-menu-item index="findDuplicateWords" @click="findDuplicateWords">
          <el-icon><CopyDocument /></el-icon>查找重复词
        </el-menu-item>
        <el-menu-item index="findDuplicateLines" @click="findDuplicateLines">
          <el-icon><Tickets /></el-icon>查找重复行
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="video" class="hide-arrow">
        <template #title>视频</template>
        <el-menu-item index="openVideo" @click="openVideoFile">
          <el-icon><VideoPlay /></el-icon>打开视频文件
        </el-menu-item>
        <el-menu-item index="closeVideo" @click="closeVideo">
          <el-icon><VideoPause /></el-icon>关闭视频文件
        </el-menu-item>
        <el-menu-item index="generateWaveform" @click="generateWaveform">
          <el-icon><DataLine /></el-icon>批量生成波形
        </el-menu-item>
        <el-menu-item index="embedHardSubtitles" @click="embedHardSubtitles">
          <el-icon><Film /></el-icon>生成带硬字幕的视频
        </el-menu-item>
        <el-menu-item index="speechRecognition" @click="showSpeechRecognition">
          <el-icon><Microphone /></el-icon>语言识别
        </el-menu-item>
        <el-menu-item index="addTts" @click="addTtsToVideo">
          <el-icon><ChatDotRound /></el-icon>文本转语音添加到视频
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="translate" class="hide-arrow">
        <template #title>字幕处理</template>
        <el-menu-item index="translate" @click="showTranslate">
          <el-icon><Connection /></el-icon>自动翻译
        </el-menu-item>
        <el-menu-item index="mergeSentences" @click="mergeSentences">
          <el-icon><Plus /></el-icon>合并句子
        </el-menu-item>
        <el-menu-item index="splitLongLines" @click="splitLongLines">
          <el-icon><Minus /></el-icon>分割长行
        </el-menu-item>
      </el-sub-menu>
    </el-menu>

    <div class="export-btn" :class="{ 'is-disabled': !hasSubtitle }" @click="showExportDialog">
      <el-icon><Upload /></el-icon>导出
    </div>

    <input
      type="file"
      ref="subtitleFileInput"
      accept=".srt,.vtt,.sub,.ass,.ssa"
      style="display: none"
      @change="handleSubtitleFile"
    />
    <input
      type="file"
      ref="videoFileInput"
      accept="video/*"
      style="display: none"
      @change="handleVideoFile"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useUIStore } from '@/stores/uiStore'
import { useRecentFilesStore, FILE_TYPES } from '@/stores/recentFilesStore'
import { SubtitleFormats } from '@/models/subtitle'

const subtitleStore = useSubtitleStore()
const uiStore = useUIStore()
const recentFilesStore = useRecentFilesStore()

const subtitleFileInput = ref(null)
const videoFileInput = ref(null)

const hasSubtitle = computed(() => subtitleStore.paragraphCount > 0)
const hasTranslation = computed(() => subtitleStore.hasTranslation)

function openSubtitleFile() {
  if (window.electronAPI) {
    openSubtitleFileElectron()
  } else {
    subtitleFileInput.value?.click()
  }
}

async function openSubtitleFileElectron() {
  const result = await window.electronAPI.selectSubtitleFile()
  if (result.success) {
    const success = subtitleStore.loadSubtitle(result.content, result.fileName)
    if (success) {
      document.title = `${result.fileName} - 字幕编辑工具`
      ElMessage.success(`已加载字幕文件: ${result.fileName}`)
      recentFilesStore.addRecentFile(result.filePath, result.fileName, FILE_TYPES.SUBTITLE)
    } else {
      ElMessage.error('无法识别的字幕文件格式')
    }
  }
}

function openVideoFile() {
  if (window.electronAPI) {
    openVideoFileElectron()
  } else {
    videoFileInput.value?.click()
  }
}

async function openVideoFileElectron() {
  const result = await window.electronAPI.selectVideoFile()
  if (result.success) {
    subtitleStore.setVideoFile(result.filePath)
    ElMessage.success(`已加载视频文件: ${result.fileName}`)
    recentFilesStore.addRecentFile(result.filePath, result.fileName, FILE_TYPES.VIDEO)
  }
}

function handleSubtitleFile(e) {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    const content = event.target.result
    const success = subtitleStore.loadSubtitle(content, file.name)
    if (success) {
      document.title = `${file.name} - 字幕编辑工具`
      ElMessage.success(`已加载字幕文件: ${file.name}`)
      if (file.path) {
        recentFilesStore.addRecentFile(file.path, file.name, FILE_TYPES.SUBTITLE)
      }
    } else {
      ElMessage.error('无法识别的字幕文件格式')
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}

async function openRecentFile(file) {
  if (!window.electronAPI) {
    ElMessage.warning('此功能仅在Electron环境下可用')
    return
  }

  if (file.type === FILE_TYPES.SUBTITLE) {
    const result = await window.electronAPI.readFile(file.path)
    if (result.success) {
      const success = subtitleStore.loadSubtitle(result.content, result.fileName)
      if (success) {
        document.title = `${result.fileName} - 字幕编辑工具`
        ElMessage.success(`已加载字幕文件: ${result.fileName}`)
        recentFilesStore.addRecentFile(result.filePath, result.fileName, FILE_TYPES.SUBTITLE)
      } else {
        ElMessage.error('无法识别的字幕文件格式')
      }
    } else {
      ElMessage.error(`打开文件失败: ${result.error}`)
      recentFilesStore.removeRecentFile(file.path)
    }
  } else if (file.type === FILE_TYPES.VIDEO) {
    subtitleStore.setVideoFile(file.path)
    ElMessage.success(`已加载视频文件: ${file.name}`)
    recentFilesStore.addRecentFile(file.path, file.name, FILE_TYPES.VIDEO)
  } else if (file.type === FILE_TYPES.AUDIO) {
    subtitleStore.setDubbingAudioFile(file.path)
    ElMessage.success(`已加载音频文件: ${file.name}`)
    recentFilesStore.addRecentFile(file.path, file.name, FILE_TYPES.AUDIO)
  }
}

function clearRecentFiles() {
  recentFilesStore.clearRecentFiles()
  ElMessage.success('已清除历史记录')
}

function handleVideoFile(e) {
  const file = e.target.files[0]
  if (!file) return

  subtitleStore.setVideoFile(file)
  ElMessage.success(`已加载视频文件: ${file.name}`)
  if (file.path) {
    recentFilesStore.addRecentFile(file.path, file.name, FILE_TYPES.VIDEO)
  }
  e.target.value = ''
}

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

async function saveFileWithPicker(content, defaultName) {
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: defaultName,
        types: [{
          description: '字幕文件',
          accept: { 'text/plain': ['.srt', '.vtt', '.ass', '.sub'] }
        }]
      })
      const writable = await handle.createWritable()
      await writable.write(content)
      await writable.close()
      ElMessage.success('保存成功')
    } catch (err) {
      if (err.name !== 'AbortError') {
        ElMessage.error(`保存失败: ${err.message}`)
      }
    }
  } else {
    downloadFile(content, defaultName)
    ElMessage.success('保存成功')
  }
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
  document.title = '字幕编辑工具'
  ElMessage.success('已关闭字幕文件')
}

function showExportDialog() {
  ElMessage.info('导出功能尚未实现')
}

function exitApp() {
  if (confirm('确定要退出吗？')) {
    window.close()
  }
}

function showFindDialog() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showFindDialog()
}

function findNext() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showFindDialog()
}

function showReplaceDialog() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showReplaceDialog()
}

function showMultiReplaceDialog() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showMultiReplaceDialog()
}

function showGoToDialog() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showGoToLineDialog({ maxLine: subtitleStore.paragraphCount })
}

function checkSpelling() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showSpellCheckDialog()
}

function findDuplicateWords() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showFindDuplicateWordsDialog()
}

function findDuplicateLines() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showFindDuplicateLinesDialog()
}

function closeVideo() {
  subtitleStore.setVideoFile(null)
  subtitleStore.setVideoElement(null)
  ElMessage.info('已关闭视频')
}

function generateWaveform() {
  if (!subtitleStore.videoFile) {
    ElMessage.warning('请先打开视频文件')
    return
  }
  ElMessage.info('请在波形区域点击生成波形')
}

function embedHardSubtitles() {
  uiStore.showHardSubtitleModal()
}

function showSpeechRecognition() {
  uiStore.showSpeechRecognitionModal()
}

function addTtsToVideo() {
  ElMessage.info('文本转语音添加到视频功能尚未实现')
}

function showTranslate() {
  uiStore.showTranslateModal()
}

function mergeSentences() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showMergeSentencesModal()
}

function splitLongLines() {
  if (subtitleStore.paragraphCount === 0) {
    ElMessage.warning('请先打开字幕文件')
    return
  }
  uiStore.showSplitLongLinesModal()
}
</script>

<style lang="scss" scoped>
.menu-bar {
  background-color: $menu-bg;
  padding: 2px 4px;
  border-bottom: 1px solid $border-color;
  display: flex;
  align-items: center;

  :deep(.el-menu) {
    background-color: transparent;
    border-bottom: none;
    height: 24px;
  }

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 24px;
    line-height: 24px;
    font-size: $font-size-base;
    padding: 0 10px;
  }

  :deep(.el-menu-item:hover),
  :deep(.el-sub-menu__title:hover) {
    background-color: $menu-hover;
  }

  :deep(.el-sub-menu .el-menu-item) {
    height: 28px;
    line-height: 28px;
  }

  :deep(.hide-arrow) {
    .el-sub-menu__icon-arrow {
      display: none;
    }
  }

  .export-btn {
    height: 24px;
    line-height: 24px;
    font-size: $font-size-base;
    padding: 0 10px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    margin-left: auto;

    &:hover {
      background-color: $menu-hover;
    }

    &.is-disabled {
      cursor: not-allowed;
      opacity: 0.5;
      pointer-events: none;
    }
  }
}
</style>
