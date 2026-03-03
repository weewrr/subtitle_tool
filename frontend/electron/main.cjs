const path = require('path')
const fs = require('fs')
const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const { spawn } = require('child_process')

const isDev = process.argv.includes('--dev')
const backendUrl = process.env.SUBTITLE_TOOL_BACKEND_URL || 'http://127.0.0.1:5000'
const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://127.0.0.1:3000'


let mainWindow = null
let backendProcess = null

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
      SUBTITLE_TOOL_BACKEND_PORT: backendPort
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
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

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


app.whenReady().then(() => {
  process.env.SUBTITLE_TOOL_BACKEND_URL = backendUrl
  startBackend()
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
