import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUIStore = defineStore('ui', () => {
  const speechRecognitionModalVisible = ref(false)
  const batchProcessingModalVisible = ref(false)
  const modelDownloadModalVisible = ref(false)
  const currentEngine = ref('openai')
  const translateModalVisible = ref(false)
  const translateAdvancedModalVisible = ref(false)
  const confirmDialogVisible = ref(false)
  const confirmDialogConfig = ref({
    title: '确认',
    message: '',
    onConfirm: null,
    onCancel: null
  })

  const messageBoxVisible = ref(false)
  const messageBoxConfig = ref({
    type: 'info',
    message: ''
  })

  const findDialogVisible = ref(false)
  const findDialogConfig = ref({
    onFind: null
  })

  const replaceDialogVisible = ref(false)
  const replaceDialogConfig = ref({
    onReplace: null
  })

  const multiReplaceDialogVisible = ref(false)
  const multiReplaceDialogConfig = ref({
    onReplace: null
  })

  const goToLineDialogVisible = ref(false)
  const goToLineDialogConfig = ref({
    maxLine: 0,
    onGoTo: null
  })

  const spellCheckDialogVisible = ref(false)
  const spellCheckDialogConfig = ref({
    onAction: null
  })

  const spellCheckAdvancedModalVisible = ref(false)

  const findDuplicateWordsVisible = ref(false)
  const findDuplicateWordsConfig = ref({
    onFind: null
  })

  const findDuplicateLinesVisible = ref(false)
  const findDuplicateLinesConfig = ref({
    onFind: null
  })

  const mergeSentencesModalVisible = ref(false)

  const splitLongLinesModalVisible = ref(false)

  const splitLongLinesAdvancedModalVisible = ref(false)
  const hardSubtitleModalVisible = ref(false)

  function showSpeechRecognitionModal() {
    speechRecognitionModalVisible.value = true
  }

  function hideSpeechRecognitionModal() {
    speechRecognitionModalVisible.value = false
  }

  function showBatchProcessingModal() {
    batchProcessingModalVisible.value = true
  }

  function hideBatchProcessingModal() {
    batchProcessingModalVisible.value = false
  }

  function showModelDownloadModal(engine = 'openai') {
    currentEngine.value = engine
    modelDownloadModalVisible.value = true
  }

  function hideModelDownloadModal() {
    modelDownloadModalVisible.value = false
  }

  function showTranslateModal() {
    translateModalVisible.value = true
  }

  function hideTranslateModal() {
    translateModalVisible.value = false
  }

  function showTranslateAdvancedModal() {
    translateAdvancedModalVisible.value = true
  }

  function hideTranslateAdvancedModal() {
    translateAdvancedModalVisible.value = false
  }

  function showConfirmDialog(config) {
    confirmDialogConfig.value = {
      title: config.title || '确认',
      message: config.message || '',
      onConfirm: config.onConfirm || null,
      onCancel: config.onCancel || null
    }
    confirmDialogVisible.value = true
  }

  function hideConfirmDialog() {
    confirmDialogVisible.value = false
  }

  function showMessage(message, type = 'info') {
    messageBoxConfig.value = { type, message }
    messageBoxVisible.value = true
    setTimeout(() => {
      messageBoxVisible.value = false
    }, 3000)
  }

  function hideMessage() {
    messageBoxVisible.value = false
  }

  function showFindDialog(config = {}) {
    findDialogConfig.value = {
      onFind: config.onFind || null
    }
    findDialogVisible.value = true
  }

  function hideFindDialog() {
    findDialogVisible.value = false
  }

  function showReplaceDialog(config = {}) {
    replaceDialogConfig.value = {
      onReplace: config.onReplace || null
    }
    replaceDialogVisible.value = true
  }

  function hideReplaceDialog() {
    replaceDialogVisible.value = false
  }

  function showMultiReplaceDialog(config = {}) {
    multiReplaceDialogConfig.value = {
      onReplace: config.onReplace || null
    }
    multiReplaceDialogVisible.value = true
  }

  function hideMultiReplaceDialog() {
    multiReplaceDialogVisible.value = false
  }

  function showGoToLineDialog(config = {}) {
    goToLineDialogConfig.value = {
      maxLine: config.maxLine || 1,
      onGoTo: config.onGoTo || null
    }
    goToLineDialogVisible.value = true
  }

  function hideGoToLineDialog() {
    goToLineDialogVisible.value = false
  }

  function showSpellCheckDialog(config = {}) {
    spellCheckDialogConfig.value = {
      onAction: config.onAction || null
    }
    spellCheckDialogVisible.value = true
  }

  function hideSpellCheckDialog() {
    spellCheckDialogVisible.value = false
  }

  function showSpellCheckAdvancedModal() {
    spellCheckAdvancedModalVisible.value = true
  }

  function hideSpellCheckAdvancedModal() {
    spellCheckAdvancedModalVisible.value = false
  }

  function showFindDuplicateWordsDialog(config = {}) {
    findDuplicateWordsConfig.value = {
      onFind: config.onFind || null
    }
    findDuplicateWordsVisible.value = true
  }

  function hideFindDuplicateWordsDialog() {
    findDuplicateWordsVisible.value = false
  }

  function showFindDuplicateLinesDialog(config = {}) {
    findDuplicateLinesConfig.value = {
      onFind: config.onFind || null
    }
    findDuplicateLinesVisible.value = true
  }

  function hideFindDuplicateLinesDialog() {
    findDuplicateLinesVisible.value = false
  }

  function showMergeSentencesModal() {
    mergeSentencesModalVisible.value = true
  }

  function hideMergeSentencesModal() {
    mergeSentencesModalVisible.value = false
  }

  function showSplitLongLinesModal() {
    splitLongLinesModalVisible.value = true
  }

  function hideSplitLongLinesModal() {
    splitLongLinesModalVisible.value = false
  }

  function showSplitLongLinesAdvancedModal() {
    splitLongLinesAdvancedModalVisible.value = true
  }

  function hideSplitLongLinesAdvancedModal() {
    splitLongLinesAdvancedModalVisible.value = false
  }

  function showHardSubtitleModal() {
    hardSubtitleModalVisible.value = true
  }

  function hideHardSubtitleModal() {
    hardSubtitleModalVisible.value = false
  }

  return {
    speechRecognitionModalVisible,
    batchProcessingModalVisible,
    modelDownloadModalVisible,
    currentEngine,
    translateModalVisible,
    translateAdvancedModalVisible,
    confirmDialogVisible,
    confirmDialogConfig,
    messageBoxVisible,
    messageBoxConfig,
    findDialogVisible,
    findDialogConfig,
    replaceDialogVisible,
    replaceDialogConfig,
    multiReplaceDialogVisible,
    multiReplaceDialogConfig,
    goToLineDialogVisible,
    goToLineDialogConfig,
    spellCheckDialogVisible,
    spellCheckDialogConfig,
    spellCheckAdvancedModalVisible,
    findDuplicateWordsVisible,
    findDuplicateWordsConfig,
    findDuplicateLinesVisible,
    findDuplicateLinesConfig,
    mergeSentencesModalVisible,
    splitLongLinesModalVisible,
    splitLongLinesAdvancedModalVisible,
    hardSubtitleModalVisible,
    showSpeechRecognitionModal,
    hideSpeechRecognitionModal,
    showBatchProcessingModal,
    hideBatchProcessingModal,
    showModelDownloadModal,
    hideModelDownloadModal,
    showTranslateModal,
    hideTranslateModal,
    showTranslateAdvancedModal,
    hideTranslateAdvancedModal,
    showConfirmDialog,
    hideConfirmDialog,
    showMessage,
    hideMessage,
    showFindDialog,
    hideFindDialog,
    showReplaceDialog,
    hideReplaceDialog,
    showMultiReplaceDialog,
    hideMultiReplaceDialog,
    showGoToLineDialog,
    hideGoToLineDialog,
    showSpellCheckDialog,
    hideSpellCheckDialog,
    showSpellCheckAdvancedModal,
    hideSpellCheckAdvancedModal,
    showFindDuplicateWordsDialog,
    hideFindDuplicateWordsDialog,
    showFindDuplicateLinesDialog,
    hideFindDuplicateLinesDialog,
    showMergeSentencesModal,
    hideMergeSentencesModal,
    showSplitLongLinesModal,
    hideSplitLongLinesModal,
    showSplitLongLinesAdvancedModal,
    hideSplitLongLinesAdvancedModal,
    showHardSubtitleModal,
    hideHardSubtitleModal
  }
})
