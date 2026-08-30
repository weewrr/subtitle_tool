<template>
  <header class="menu-bar">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="16" height="16">
          <rect x="1" y="11" width="14" height="3" rx="1" fill="currentColor" opacity="0.9" />
          <rect x="3" y="6.5" width="10" height="3" rx="1" fill="currentColor" opacity="0.65" />
          <rect x="5" y="2" width="6" height="3" rx="1" fill="currentColor" opacity="0.4" />
        </svg>
      </div>
      <span class="brand-name">字幕工作台</span>
    </div>

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
        <el-menu-item index="saveProject" @click="saveProject" :disabled="!hasSubtitle" title="Ctrl+Shift+S">
          <el-icon><FolderChecked /></el-icon>保存项目
        </el-menu-item>
        <el-menu-item index="openProject" @click="openProjectFile">
          <el-icon><Folder /></el-icon>打开项目
        </el-menu-item>
        <el-menu-item index="closeSubtitle" @click="closeSubtitle" :disabled="!hasSubtitle">
          <el-icon><DocumentRemove /></el-icon>关闭字幕
        </el-menu-item>
        <el-menu-item index="settings" @click="showSettings">
          <el-icon><Setting /></el-icon>设置
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
        <el-menu-item index="embedHardSubtitles" @click="embedHardSubtitles" :disabled="!subtitleStore.videoFile || subtitleStore.paragraphCount === 0">
          <el-icon><Film /></el-icon>生成带硬字幕的视频
        </el-menu-item>
        <el-menu-item index="speechRecognition" @click="showSpeechRecognition">
          <el-icon><Microphone /></el-icon>语言识别
        </el-menu-item>
        <el-menu-item index="addTts" @click="addTtsToVideo" :disabled="!subtitleStore.videoFile || !subtitleStore.dubbingAudioFile">
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

    <div class="header-actions">
      <button
        class="palette-btn"
        type="button"
        aria-label="打开命令面板"
        title="命令面板 (Ctrl+K)"
        @click="commandStore.togglePalette(true)"
      >
        <el-icon :size="13"><Search /></el-icon>
        <span class="palette-key">Ctrl K</span>
      </button>
      <button
        class="icon-btn"
        type="button"
        :aria-label="isDark ? '切换到浅色主题' : '切换到深色主题'"
        :title="isDark ? '切换到浅色主题' : '切换到深色主题'"
        @click="toggleTheme"
      >
        <el-icon :size="15"><Sunny v-if="isDark" /><Moon v-else /></el-icon>
      </button>
      <button
        class="export-btn"
        type="button"
        :class="{ 'is-disabled': !hasSubtitle }"
        :disabled="!hasSubtitle"
        @click="showExportDialog"
      >
        <el-icon :size="14"><Upload /></el-icon>导出
      </button>
    </div>
  </header>
</template>

<script setup>
import { useAppActions } from '@/composables/useAppActions'
import { useCommandStore } from '@/stores/commandStore'
import { useSubtitleStore } from '@/stores/subtitleStore'
import { useRecentFilesStore } from '@/stores/recentFilesStore'

const commandStore = useCommandStore()
const subtitleStore = useSubtitleStore()
const recentFilesStore = useRecentFilesStore()

const {
  isDark,
  toggleTheme,
  hasSubtitle,
  hasTranslation,
  openSubtitleFile,
  openVideoFile,
  openProjectFile,
  saveProject,
  openRecentFile,
  clearRecentFiles,
  saveOriginalSubtitle,
  saveTranslatedSubtitle,
  closeSubtitle,
  showExportDialog,
  exitApp,
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
  showSettings
} = useAppActions()
</script>

<style lang="scss" scoped>
.menu-bar {
  flex-shrink: 0;
  height: 44px;
  padding: 0 12px;
  background: var(--app-surface);
  border-bottom: 1px solid var(--app-border);
  display: flex;
  align-items: center;
  gap: 8px;

  .brand {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-right: 8px;
    margin-right: 4px;
    border-right: 1px solid var(--app-border);
    user-select: none;

    .brand-mark {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 7px;
      background: var(--app-primary);
      color: #fff;
      box-shadow: var(--app-shadow-sm);
    }

    .brand-name {
      font-size: $font-size-lg;
      font-weight: 700;
      letter-spacing: 0.01em;
      color: var(--app-text-primary);
    }
  }

  :deep(.el-menu) {
    background: transparent;
    border-bottom: none;
    height: 32px;
    flex: 1;
    min-width: 0;
  }

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 32px;
    line-height: 32px;
    font-size: $font-size-base;
    font-weight: 500;
    padding: 0 10px;
    border-radius: $border-radius-sm;
    color: var(--app-text-secondary);
    transition: $transition-colors;
  }

  :deep(.el-menu-item:hover),
  :deep(.el-sub-menu__title:hover) {
    background: var(--app-hover-bg);
    color: var(--app-text-primary);
  }

  :deep(.el-sub-menu .el-menu-item) {
    height: 30px;
    line-height: 30px;
  }

  :deep(.hide-arrow) {
    .el-sub-menu__icon-arrow {
      display: none;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
    flex-shrink: 0;
  }

  .palette-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 10px;
    border: 1px solid var(--app-border);
    border-radius: $border-radius-sm;
    background: var(--app-surface-muted);
    color: var(--app-text-muted);
    cursor: pointer;
    transition: $transition-colors;

    .palette-key {
      font-family: $font-family-mono;
      font-size: 11px;
      line-height: 1;
    }

    &:hover {
      background: var(--app-hover-bg);
      border-color: var(--app-border-strong);
      color: var(--app-text-primary);
    }
  }

  .icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border: 1px solid var(--app-border);
    border-radius: $border-radius-sm;
    background: var(--app-surface);
    color: var(--app-text-secondary);
    cursor: pointer;
    transition: $transition-colors;

    &:hover {
      background: var(--app-hover-bg);
      border-color: var(--app-border-strong);
      color: var(--app-text-primary);
    }
  }

  .export-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 14px;
    font-size: $font-size-base;
    font-weight: 600;
    border: none;
    border-radius: $border-radius-sm;
    background: var(--app-accent);
    color: #fff;
    cursor: pointer;
    transition: $transition-colors;

    &:hover:not(:disabled) {
      background: var(--app-accent-hover);
      box-shadow: var(--app-shadow-md);
    }

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
  }
}
</style>
