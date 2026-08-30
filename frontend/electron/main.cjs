const path = require('path')
const fs = require('fs')
const { app, BrowserWindow, ipcMain, dialog, protocol, net, shell } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const { pathToFileURL } = require('url')

const isDev = process.argv.includes('--dev')
const backendUrl = process.env.SUBTITLE_TOOL_BACKEND_URL || 'http://127.0.0.1:5000'
const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://127.0.0.1:3000'

// 待页面加载完成后再派发的「打开文件」队列
// (应用冷启动时 first-instance 先于 did-finish-load 触发,需要暂存)
let pendingOpenProjectPath = null

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
  },
  // media 协议用于直读本地音视频:
  // - 绕过后端 HTTP 转发,seek/加载速度直接走磁盘
  // - 同源即 app://./index.html → media:// → 无 CORS 问题,Web Audio 链路不再被强制静音
  {
    scheme: 'media',
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      stream: true,
      bypassCSP: true
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

// 把一个 .stproj 文件路径通过 IPC 交给渲染端加载
function dispatchOpenProject(projectPath) {
  if (!mainWindow || mainWindow.isDestroyed()) return false
  if (!fs.existsSync(projectPath)) {
    console.warn('[electron] open-project target not exists:', projectPath)
    return false
  }
  try {
    const content = fs.readFileSync(projectPath, 'utf-8')
    mainWindow.webContents.send('open-project', {
      content,
      fileName: path.basename(projectPath),
      filePath: projectPath
    })
    return true
  } catch (e) {
    console.error('[electron] dispatchOpenProject failed:', e.message)
    return false
  }
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 760,
    autoHideMenuBar: true,
    backgroundColor: '#111111',
    // NSIS 安装时会把 .stproj 图标绑定到这里的 productName,应用图标默认
    icon: path.join(__dirname, '..', 'public', 'favicon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  // 安全:禁止任何 window.open 弹出新窗口(渲染层被注入时防止 preload 暴露面被带出)
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  // 安全:拦截页面级导航,只允许应用自身与本地开发/后端地址;外部链接交给系统浏览器
  // 注:loadURL 编程式导航不触发 will-navigate,不影响启动加载
  mainWindow.webContents.on('will-navigate', (event, url) => {
    let parsed
    try {
      parsed = new URL(url)
    } catch {
      event.preventDefault()
      return
    }
    const isLocal =
      parsed.protocol === 'app:'
      || ((parsed.protocol === 'http:' || parsed.protocol === 'https:')
        && (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1'))
    if (!isLocal) {
      event.preventDefault()
      shell.openExternal(url)
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
    // 冷启动时 first-instance / open-file 可能先于 did-finish-load,这里统一补发
    if (pendingOpenProjectPath) {
      const p = pendingOpenProjectPath
      pendingOpenProjectPath = null
      dispatchOpenProject(p)
    }
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

// ============================================================
// 文件关联:双击 .stproj 打开
// ============================================================
function extractProjectPathFromArgv(argv) {
  // 过滤掉 Electron/应用自身的 switch 参数,剩下的第一个非 switch 参数就是被双击的文件路径
  const relevant = argv.filter(a => a && !a.startsWith('--'))
  const executable = process.execPath.toLowerCase()
  return relevant.find(a => {
    const candidate = a.toLowerCase()
    return candidate !== executable
      && !candidate.endsWith('electron.exe')
      && !candidate.endsWith('.asar')
      && candidate.endsWith('.stproj')
  })
}

// 非 darwin 平台:窗口尚未创建前,从 process.argv 末尾取被双击打开的文件
const bootProjectPath = extractProjectPathFromArgv(process.argv || [])

// darwin:用户点击 Finder 中的文件触发
app.on('open-file', (event, filePath) => {
  event.preventDefault()
  if (!filePath.toLowerCase().endsWith('.stproj')) return
  if (!dispatchOpenProject(filePath)) {
    pendingOpenProjectPath = filePath
  }
  if (mainWindow) {
    mainWindow.focus()
  } else if (app.isReady()) {
    createMainWindow()
  }
})

// 单实例:第二实例启动(双击 .stproj)时,通知第一实例并让它前台化
const gotInstanceLock = app.requestSingleInstanceLock()
if (!gotInstanceLock) {
  // 没抢到锁,直接退出(系统会把 argv 通过 second-instance 交给第一实例)
  app.quit()
} else {
  app.on('second-instance', (_event, commandLine) => {
    const p = extractProjectPathFromArgv(commandLine || [])
    if (p) {
      if (!dispatchOpenProject(p)) {
        pendingOpenProjectPath = p
      }
    }
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    } else {
      createMainWindow()
    }
  })
}

// ============================================================
// IPC handlers
// ============================================================
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

ipcMain.handle('select-project-file', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      filters: [
        { name: '字幕工作台项目', extensions: ['stproj'] }
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

ipcMain.handle('save-text-file', async (_event, { content, defaultName, extensions }) => {
  try {
    const exts = Array.isArray(extensions) && extensions.length > 0 ? extensions : ['txt']
    const result = await dialog.showSaveDialog(mainWindow, {
      defaultPath: defaultName,
      filters: [
        { name: exts[0].toUpperCase() + ' 文件', extensions: exts }
      ]
    })

    if (result.canceled) {
      return { success: false, canceled: true }
    }

    fs.writeFileSync(result.filePath, content, 'utf-8')
    return { success: true, filePath: result.filePath }
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

// ============================================================
// 统一存储桥接:Electron 主进程持久化,浏览器回退到 localStorage
// ============================================================
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
    // 为 Windows 兼容做独占式写入:先写到 .tmp 再 replace,避免中途 crash 破坏原文件
    const tmp = p + '.tmp'
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2), 'utf-8')
    fs.renameSync(tmp, p)
    return { success: true }
  } catch (e) {
    console.error('[storage] write error:', e.message)
    return { success: false, error: e.message }
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

// 原子性写全量存储(用于 Electron 下 flushCache,与 localStorage.setItem 等价)
ipcMain.handle('storage-flush', async (_event, fullData) => {
  if (!fullData || typeof fullData !== 'object') {
    return { success: false, error: 'invalid payload' }
  }
  return writeStorage(fullData)
})

// 渲染端拿到本地文件路径,需要一个 media:// URL 来直读
ipcMain.handle('path-to-media-url', async (_event, filePath) => {
  if (!filePath || typeof filePath !== 'string') {
    return { success: false, error: 'empty path' }
  }
  // media://local/<绝对路径编码>,渲染源同源,无需再处理 CORS
  try {
    const encoded = encodeURIComponent(filePath)
    return { success: true, url: `media://local/${encoded}` }
  } catch (e) {
    return { success: false, error: e.message }
  }
})

app.whenReady().then(async () => {
  process.env.SUBTITLE_TOOL_BACKEND_URL = backendUrl

  // app:// 协议:映射到 dist/ 下的前端静态资源
  // 安全:decodeURIComponent 后 '..' 生效(如 %2E%2E%2F),必须做前缀校验防止路径穿越
  protocol.handle('app', (request) => {
    const pathname = decodeURIComponent(new URL(request.url).pathname)
    const relative = pathname.replace(/^\/+/, '') || 'index.html'
    const distRoot = path.join(__dirname, '..', 'dist') + path.sep
    const filePath = path.join(distRoot, relative)
    if (!filePath.startsWith(distRoot)) {
      return new Response('Not Found', { status: 404 })
    }
    return net.fetch(pathToFileURL(filePath).toString())
  })

  // media:// 协议:从任意本地绝对路径直读音视频,绕过后端 HTTP 转发
  // URL 形态:media://local/<encodeURIComponent(绝对路径)>
  protocol.handle('media', (request) => {
    try {
      const url = new URL(request.url)
      // host === 'local' 时,pathname = '/' + encodeURIComponent(绝对路径)
      const encodedPath = url.pathname.slice(1)
      const targetPath = decodeURIComponent(encodedPath)
      if (!targetPath || !path.isAbsolute(targetPath) || !fs.existsSync(targetPath)) {
        return new Response('Not Found', { status: 404 })
      }
      return net.fetch(pathToFileURL(targetPath).toString(), {
        headers: request.headers
      })
    } catch (e) {
      console.error('[media-protocol] failed:', e.message)
      return new Response('Bad Request', { status: 400 })
    }
  })

  if (!await isBackendHealthy()) {
    startBackend()
  }
  const backendReady = await waitForBackend()
  if (!backendReady) {
    console.error(`[backend] did not become ready within 30 seconds: ${backendUrl}`)
  }
  createMainWindow()

  // 冷启动时若通过双击 .stproj 启动(非 darwin 平台 argv 末尾会带文件路径),等窗口 ready 后加载
  if (bootProjectPath) {
    pendingOpenProjectPath = bootProjectPath
  }

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
