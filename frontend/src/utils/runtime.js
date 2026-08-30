export function getBackendBaseUrl() {
  const electronUrl = window?.subtitleToolConfig?.backendUrl
  const envUrl = import.meta.env.VITE_BACKEND_URL

  return electronUrl || envUrl || 'http://127.0.0.1:5000'
}

/**
 * 将本地文件路径转成可供 <video>/<audio> 使用的 URL。
 * - Electron 桌面版:使用自定义 media:// 协议直读,绕过后端 HTTP 转发,
 *   同时消除了跨域 → Web Audio 被强制静音的 CORS 问题。
 * - 浏览器版:回退到 /api/video/serve HTTP 接口。
 *
 * 对 File 对象(来自 <input type=file>)直接用 URL.createObjectURL,不走这里。
 */
export async function resolveMediaUrl(filePath) {
  if (!filePath || typeof filePath !== 'string') return ''
  if (window.electronAPI?.pathToMediaUrl) {
    const result = await window.electronAPI.pathToMediaUrl(filePath)
    if (result?.success && result.url) return result.url
  }
  const encodedPath = encodeURIComponent(filePath)
  return `${getBackendBaseUrl()}/api/video/serve?path=${encodedPath}`
}
