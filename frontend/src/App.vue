<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <MenuBar />
      
      <SplitPane
        :vertical="false"
        :initial-split="55"
        :min-first-size="400"
        :min-second-size="250"
        class="main-split"
      >
        <template #first>
          <SplitPane
            :vertical="true"
            :initial-split="50"
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
            :min-first-size="400"
            :min-second-size="400"
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
    </div>
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import MenuBar from '@/components/MenuBar.vue'
import VideoPlayer from '@/components/VideoPlayer.vue'
import VideoControls from '@/components/VideoControls.vue'
import SubtitleList from '@/components/SubtitleList.vue'
import EditPanel from '@/components/EditPanel.vue'
import TtsPanel from '@/components/TtsPanel.vue'
import WaveformPanel from '@/components/WaveformPanel.vue'
import SplitPane from '@/components/SplitPane.vue'
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
import { useUIStore } from '@/stores/uiStore'
import { watch, ref } from 'vue'

const uiStore = useUIStore()
const hardSubtitleModalRef = ref(null)

watch(() => uiStore.hardSubtitleModalVisible, (newVal) => {
  if (newVal && hardSubtitleModalRef.value) {
    hardSubtitleModalRef.value.open()
  }
})
</script>

<style lang="scss">
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: $bg-color;
}

.main-split {
  flex: 1;
  min-height: 0;
}

.top-split {
  width: 100%;
  height: 100%;
}

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
  gap: 4px;
  min-width: 0;
  min-height: 0;
}

.bottom-left,
.bottom-right {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid $border-color;
  background-color: #fff;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
</style>
