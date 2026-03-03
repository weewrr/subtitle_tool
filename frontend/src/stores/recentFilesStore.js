import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const MAX_RECENT_FILES = 10
const STORAGE_KEY = 'subtitle-tool-recent-files'

export const FILE_TYPES = {
  SUBTITLE: 'subtitle',
  VIDEO: 'video',
  AUDIO: 'audio'
}

export const useRecentFilesStore = defineStore('recentFiles', () => {
  const recentFiles = ref([])

  const subtitleFiles = computed(() => 
    recentFiles.value.filter(f => f.type === FILE_TYPES.SUBTITLE)
  )

  const videoFiles = computed(() => 
    recentFiles.value.filter(f => f.type === FILE_TYPES.VIDEO)
  )

  const audioFiles = computed(() => 
    recentFiles.value.filter(f => f.type === FILE_TYPES.AUDIO)
  )

  function loadFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        recentFiles.value = JSON.parse(stored)
      }
    } catch (err) {
      console.error('Failed to load recent files from storage:', err)
      recentFiles.value = []
    }
  }

  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(recentFiles.value))
    } catch (err) {
      console.error('Failed to save recent files to storage:', err)
    }
  }

  function addRecentFile(filePath, fileName, type = FILE_TYPES.SUBTITLE) {
    const existingIndex = recentFiles.value.findIndex(f => f.path === filePath)
    if (existingIndex !== -1) {
      recentFiles.value.splice(existingIndex, 1)
    }

    recentFiles.value.unshift({
      path: filePath,
      name: fileName,
      type: type,
      lastOpened: new Date().toISOString()
    })

    if (recentFiles.value.length > MAX_RECENT_FILES) {
      recentFiles.value = recentFiles.value.slice(0, MAX_RECENT_FILES)
    }

    saveToStorage()
  }

  function removeRecentFile(filePath) {
    const index = recentFiles.value.findIndex(f => f.path === filePath)
    if (index !== -1) {
      recentFiles.value.splice(index, 1)
      saveToStorage()
    }
  }

  function clearRecentFiles() {
    recentFiles.value = []
    saveToStorage()
  }

  function clearRecentFilesByType(type) {
    recentFiles.value = recentFiles.value.filter(f => f.type !== type)
    saveToStorage()
  }

  loadFromStorage()

  return {
    recentFiles,
    subtitleFiles,
    videoFiles,
    audioFiles,
    addRecentFile,
    removeRecentFile,
    clearRecentFiles,
    clearRecentFilesByType
  }
})
