const path = require('path')
const fs = require('fs')
const { app, BrowserWindow, ipcMain, dialog, protocol, net } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const { pathToFileURL } = require('url')

const isDev = process.argv.includes('--dev')
const backendUrl = process.env.SUBTITLE_TOOL_BACKEND_URL || 'http://127.0.0.1:5000'
const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://127.0.0.1:3000'

// 注册 app 为标准协议（必须在 app ready 之前调用），
// 否则 app://./index.html 会被错误规范化为 app:////./index.html，导致加载失败
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      stream: true
    }
  }
])


let mainWindow = null
let backendProcess = null

function isBackendHealthy(timeoutMs = 1000) {
  return new Promise((resolve) => {
    const request = http.get(`${backendUrl}/api/health`, (response) => {
      response.resume()
      resolve(response.statusCode === 200)
    })
    request.setTimeout(timeoutMs, () => { request.destroy(); resolve(false) })
    request.on('error', () => resolve(false))
  })
}

async function waitForBackend(maxWaitMs = 30000) {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    if (await isBackendHealthy()) return true
    await new Promise(resolve => setTimeout(resolve, 300))
  }
  return false
}

function parseBackendPort(url) {
  try {
    const parsed = new URL(url)
    return parsed.port ? Number(parsed.port) : (parsed.protocol === 'https:' ? 443 : 80)
  } catch {
    return 5000
  }
}

function startBackend() {
  if (backendProcess) {
    return
  }

  const projectRoot = path.resolve(__dirname, '..', '..')
  const pythonCommand = process.env.PYTHON_PATH || (process.platform === 'win32' ? 'python' : 'python3')
  const backendPort = String(parseBackendPort(backendUrl))

  backendProcess = spawn(pythonCommand, ['app.py'], {
    cwd: projectRoot,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      SUBTITLE_TOOL_BACKEND_PORT: backendPort,
      SUBTITLE_TOOL_BACKEND_DEBUG: isDev ? '1' : '0'
    },
    stdio: 'pipe',
    windowsHide: true
  })

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.on('exit', (code, signal) => {
    console.log(`[backend] exited with code=${code}, signal=${signal}`)
    backendProcess = null
  })
}

function stopBackend() {
  if (!backendProcess) {
    return
  }

  try {
    if (process.platform === 'win32') {
      backendProcess.kill('SIGTERM')
    } else {
      backendProcess.kill('SIGTERM')
    }
  } catch (err) {
    console.error('[backend] stop failed:', err)
  }
}

function loadDevUrlWithRetry(maxRetries = 20, delayMs = 500) {
  let retries = 0

  const tryLoad = () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      return
    }

    mainWindow.loadURL(devServerUrl).catch((err) => {
      retries += 1
      if (retries <= maxRetries) {
        console.warn(`[electron] dev server not ready, retry ${retries}/${maxRetries}: ${err.message}`)
        setTimeout(tryLoad, delayMs)
      } else {
        console.error('[electron] failed to load dev server:', err)
      }
    })
  }

  tryLoad()
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 760,
    autoHideMenuBar: true,
    backgroundColor: '#111111',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  if (isDev) {
    loadDevUrlWithRetry()
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadURL('app://./index.html').catch((err) => {
      console.error('[electron] failed to load app://./index.html:', err.message)
    })
  }

  mainWindow.webContents.on('did-finish-load', () => {
    console.log(`[electron] page loaded: ${mainWindow.webContents.getURL()}`)
  })

  mainWindow.webContents.on('did-fail-load', (_event, code, description) => {
    if (isDev && code !== -3) {
      console.warn(`[electron] did-fail-load: ${code} ${description}`)
      loadDevUrlWithRetry()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const content = fs.readFileSync(filePath, 'utf-8')
    const fileName = path.basename(filePath)
    return { success: true, content, fileName, filePath }
  } catch (err) {
    return { success: false, error: err.message }
  }
})

ipcMain.handle('select-subtitle-file', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      filters: [
        { name: '字幕文件', extensions: ['srt', 'vtt', 'sub', 'ass', 'ssa'] }
      ],
      properties: ['openFile']
    })
    
    if (result.canceled || result.filePaths.length === 0) {
      return { success: false, canceled: true }
    }
    
    const filePath = result.filePaths[0]
    const content = fs.readFileSync(filePath, 'utf-8')
    const fileName = path.basename(filePath)
    return { success: true, content, fileName, filePath }
  } catch (err) {
    return { success: false, error: err.message }
  }
})

ipcMain.handle('select-video-file', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      filters: [
        { name: '视频文件', extensions: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'] }
      ],
      properties: ['openFile']
    })
    
    if (result.canceled || result.filePaths.length === 0) {
      return { success: false, canceled: true }
    }
    
    const filePath = result.filePaths[0]
    const fileName = path.basename(filePath)
    return { success: true, filePath, fileName }
  } catch (err) {
    return { success: false, error: err.message }
  }
})

ipcMain.handle('select-audio-file', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      filters: [
        { name: '音频文件', extensions: ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'] }
      ],
      properties: ['openFile']
    })
    
    if (result.canceled || result.filePaths.length === 0) {
      return { success: false, canceled: true }
    }
    
    const filePath = result.filePaths[0]
    const fileName = path.basename(filePath)
    return { success: true, filePath, fileName }
  } catch (err) {
    return { success: false, error: err.message }
  }
})

// 统一存储桥接：Electron 主进程持久化，浏览器回退到 localStorage
function getStoragePath() {
  return path.join(app.getPath('userData'), 'shared-storage.json')
}

function readStorage() {
  try {
    const p = getStoragePath()
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, 'utf-8'))
    }
  } catch (e) {
    console.error('[storage] read error:', e.message)
  }
  return {}
}

function writeStorage(data) {
  try {
    const p = getStoragePath()
    fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8')
    return true
  } catch (e) {
    console.error('[storage] write error:', e.message)
    return false
  }
}

ipcMain.handle('storage-get', async (_event, key) => {
  const data = readStorage()
  return key ? (data[key] ?? null) : data
})

ipcMain.handle('storage-set', async (_event, key, value) => {
  const data = readStorage()
  data[key] = value
  return writeStorage(data)
})

ipcMain.handle('storage-remove', async (_event, key) => {
  const data = readStorage()
  delete data[key]
  return writeStorage(data)
})


app.whenReady().then(async () => {
  process.env.SUBTITLE_TOOL_BACKEND_URL = backendUrl

  // 注册自定义 app:// 协议，确保 Electron 有稳定的 localStorage 源
  protocol.handle('app', (request) => {
    // 标准协议下 URL 形如 app://./index.html 或 app://./assets/xx.js，
    // 用 URL 解析取 pathname，避免字符串 replace 对形态误判
    const pathname = decodeURIComponent(new URL(request.url).pathname)
    const relative = pathname.replace(/^\/+/, '') || 'index.html'
    const filePath = path.join(__dirname, '..', 'dist', relative)
    // Windows 路径必须用 pathToFileURL 转成合法 file:/// URL，不能直接拼接
    return net.fetch(pathToFileURL(filePath).toString())
  })

  if (!await isBackendHealthy()) {
    startBackend()
  }
  const backendReady = await waitForBackend()
  if (!backendReady) {
    console.error(`[backend] did not become ready within 30 seconds: ${backendUrl}`)
  }
  createMainWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow()
    }
  })
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
