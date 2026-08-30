/**
 * 统一存储工具
 * Electron 环境：通过 IPC 读写主进程 JSON 文件（app:// 协议 + shared-storage.json）
 * 浏览器环境：回退到 localStorage
 *
 * 所有写入方法返回 { success, error } 结构：
 *   - 写入失败时 success=false 并附带可读错误原因(配额满 / IPC 异常等),
 *     方便上层把失败变成用户可见提示,而不是静默吞掉。
 *
 * 数据安全保证:
 *   - 容量保护:浏览器 localStorage 单个存储 payload 不超过 4.5MB。
 *   - 主进程写入为临时文件再 replace,避免中途 crash 破坏原文件。
 */

const isElectron = () => typeof window !== 'undefined' && window.electronAPI && window.electronAPI.storageGet

// 单个 localStorage 值的安全上限(Chrome 的单域默认约 5MB,留 0.5MB 给其它 key)
const LS_SAFE_BYTES = 4_500_000

// 内存缓存，避免 Electron 下频繁 IPC
let cache = null
let cacheLoaded = false

async function loadCache() {
  if (cacheLoaded) return
  if (isElectron()) {
    try {
      cache = await window.electronAPI.storageGet() || {}
    } catch (e) {
      console.error('[storage] Electron cache load failed:', e)
      cache = {}
    }
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
  if (!cache) return { success: true }
  if (isElectron()) {
    try {
      const r = await window.electronAPI.storageFlush(cache) || { success: false }
      if (!r.success) {
        const msg = r.error || '写入失败'
        return { success: false, error: msg, quota: false }
      }
      return { success: true }
    } catch (e) {
      return { success: false, error: e.message || 'IPC 写入异常', quota: false }
    }
  } else {
    let serialized = ''
    try {
      serialized = JSON.stringify(cache)
    } catch (e) {
      return { success: false, error: `序列化失败: ${e.message}`, quota: false }
    }
    if (serialized.length > LS_SAFE_BYTES) {
      return {
        success: false,
        error: `存储数据过大(${Math.round(serialized.length / 1024)}KB),已超过浏览器安全配额,请清理历史文件或保存到 .stproj 项目文件`,
        quota: true
      }
    }
    try {
      localStorage.setItem('subtitle-tool-unified', serialized)
      return { success: true }
    } catch (e) {
      const quotaExceeded =
        e && (
          (typeof e === 'object' && 'QUOTA_EXCEEDED_ERR' in e) ||
          (e.name === 'QuotaExceededError') ||
          (e.code === 22) ||
          String(e.message || '').toLowerCase().includes('quota')
        )
      return {
        success: false,
        error: quotaExceeded ? `浏览器存储已满(${Math.round(serialized.length / 1024)}KB),请清理历史文件或保存为 .stproj 项目文件` : e.message || '写入失败',
        quota: !!quotaExceeded
      }
    }
  }
}

export async function storageGet(key) {
  await loadCache()
  return key ? (cache[key] ?? null) : cache
}

export async function storageSet(key, value) {
  await loadCache()
  cache[key] = value
  return flushCache()
}

export async function storageRemove(key) {
  await loadCache()
  delete cache[key]
  return flushCache()
}

// 同步环境(比如 beforeunload 时刻)读取 localStorage 草稿兜底用:
// 不走缓存,直接读原始 key(若 IPC 不可用);仅浏览器有效,Electron 返回 null
export function storageSyncGetRaw(key) {
  if (isElectron()) return null
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
