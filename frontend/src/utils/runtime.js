export function getBackendBaseUrl() {
  const electronUrl = window?.subtitleToolConfig?.backendUrl
  const envUrl = import.meta.env.VITE_BACKEND_URL

  return electronUrl || envUrl || 'http://127.0.0.1:5000'
}
