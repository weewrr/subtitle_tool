import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Subtitle, Paragraph, TimeCode, SubtitleFormats } from '@/models/subtitle'

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
    addParagraph,
    removeParagraph,
    undo,
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
    mergeParagraphs,
    applyMergedSubtitles,
    applySplitResults
  }
})
