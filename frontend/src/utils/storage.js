/**
 * 统一存储工具
 * Electron 环境：通过 IPC 读写主进程 JSON 文件（app:// 协议 + shared-storage.json）
 * 浏览器环境：回退到 localStorage
 */

const isElectron = () => typeof window !== 'undefined' && window.electronAPI && window.electronAPI.storageGet

// 内存缓存，避免 Electron 下频繁 IPC
let cache = null
let cacheLoaded = false

async function loadCache() {
  if (cacheLoaded) return
  if (isElectron()) {
    cache = await window.electronAPI.storageGet()
  } else {
    try {
      const raw = localStorage.getItem('subtitle-tool-unified')
      cache = raw ? JSON.parse(raw) : {}
    } catch {
      cache = {}
    }
  }
  cacheLoaded = true
}

async function flushCache() {
  if (!cache) return
  if (isElectron()) {
    await window.electronAPI.storageSet(null, cache)
  } else {
    try {
      localStorage.setItem('subtitle-tool-unified', JSON.stringify(cache))
    } catch { /* ignore */ }
  }
}

export async function storageGet(key) {
  await loadCache()
  return key ? (cache[key] ?? null) : cache
}

export async function storageSet(key, value) {
  await loadCache()
  cache[key] = value
  await flushCache()
}

export async function storageRemove(key) {
  await loadCache()
  delete cache[key]
  await flushCache()
}