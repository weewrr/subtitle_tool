const { contextBridge, ipcRenderer } = require('electron')

console.log('[preload] Loading preload script...')

contextBridge.exposeInMainWorld('subtitleToolConfig', {
  backendUrl: process.env.SUBTITLE_TOOL_BACKEND_URL || 'http://127.0.0.1:5000'
})

contextBridge.exposeInMainWorld('electronAPI', {
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  selectSubtitleFile: () => ipcRenderer.invoke('select-subtitle-file'),
  selectVideoFile: () => ipcRenderer.invoke('select-video-file'),
  selectAudioFile: () => ipcRenderer.invoke('select-audio-file'),
  selectProjectFile: () => ipcRenderer.invoke('select-project-file'),
  saveTextFile: (options) => ipcRenderer.invoke('save-text-file', options),
  // 统一存储桥接(修复调用签名传 value)
  storageGet: (key) => ipcRenderer.invoke('storage-get', key),
  storageSet: (key, value) => ipcRenderer.invoke('storage-set', key, value),
  storageRemove: (key) => ipcRenderer.invoke('storage-remove', key),
  storageFlush: (data) => ipcRenderer.invoke('storage-flush', data),
  // 本地文件路径 → media:// 自定义协议 URL(绕过后端 HTTP,根除 CORS 静音)
  pathToMediaUrl: (filePath) => ipcRenderer.invoke('path-to-media-url', filePath),
  // 主进程发出:双击 .stproj / 第二实例启动 → 渲染端加载项目
  onOpenProject: (callback) => {
    if (typeof callback !== 'function') return () => {}
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('open-project', listener)
    return () => ipcRenderer.removeListener('open-project', listener)
  }
})

console.log('[preload] electronAPI exposed successfully')
