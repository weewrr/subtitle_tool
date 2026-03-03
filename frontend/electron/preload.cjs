const { contextBridge, ipcRenderer } = require('electron')

console.log('[preload] Loading preload script...')

contextBridge.exposeInMainWorld('subtitleToolConfig', {
  backendUrl: process.env.SUBTITLE_TOOL_BACKEND_URL || 'http://127.0.0.1:5000'
})

contextBridge.exposeInMainWorld('electronAPI', {
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  selectSubtitleFile: () => ipcRenderer.invoke('select-subtitle-file'),
  selectVideoFile: () => ipcRenderer.invoke('select-video-file'),
  selectAudioFile: () => ipcRenderer.invoke('select-audio-file')
})

console.log('[preload] electronAPI exposed successfully')
