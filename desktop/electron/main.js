const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')
const http = require('http')
const net = require('net')
const { spawn } = require('child_process')

// ---------------------------------------------------------------------------
// 后端地址持久化（userData/settings.json）
// 打包后前端 SPA 通过 http 连后端；默认 127.0.0.1:5000，可在设置里改。
// ---------------------------------------------------------------------------
function settingsPath() {
  return path.join(app.getPath('userData'), 'settings.json')
}
function readSettings() {
  try {
    return JSON.parse(fs.readFileSync(settingsPath(), 'utf-8'))
  } catch {
    return {}
  }
}
function readBackendUrl() {
  return readSettings().backendUrl || 'http://127.0.0.1:5000'
}
function writeBackendUrl(url) {
  const s = readSettings()
  s.backendUrl = url
  fs.writeFileSync(settingsPath(), JSON.stringify(s, null, 2))
}

// ---------------------------------------------------------------------------
// 内置后端进程管理（打包态：spawn studymate-backend.exe → 探活 → 退出清理）
// 开发态跳过：开发者自行运行 python run.py。
// ---------------------------------------------------------------------------
let backendProc = null
let backendPort = 5000

function backendExePath() {
  // extraResources 布局：resources/backend/studymate-backend/studymate-backend.exe
  return path.join(
    process.resourcesPath,
    'backend',
    'studymate-backend',
    'studymate-backend.exe'
  )
}

// 找一个空闲端口（优先 5000，被占则由系统分配）
function findFreePort(preferred) {
  return new Promise((resolve) => {
    const srv = net.createServer()
    srv.once('error', () => {
      // preferred 被占用 → 端口 0 让系统分配
      const srv2 = net.createServer()
      srv2.listen(0, '127.0.0.1', () => {
        const port = srv2.address().port
        srv2.close(() => resolve(port))
      })
    })
    srv.listen(preferred, '127.0.0.1', () => {
      srv.close(() => resolve(preferred))
    })
  })
}

function healthCheck(port) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: '127.0.0.1', port, path: '/api/health', timeout: 2000 },
      (res) => resolve(res.statusCode === 200)
    )
    req.on('error', () => resolve(false))
    req.on('timeout', () => {
      req.destroy()
      resolve(false)
    })
  })
}

// 轮询探活：最多 waitMs 毫秒
async function waitForBackend(port, waitMs = 30000) {
  const deadline = Date.now() + waitMs
  while (Date.now() < deadline) {
    if (await healthCheck(port)) return true
    await new Promise((r) => setTimeout(r, 500))
  }
  return false
}

async function startBackend() {
  const exe = backendExePath()
  if (!fs.existsSync(exe)) {
    console.warn('[backend] 未找到内置后端：', exe, '（回退到 settings 中的外部后端地址）')
    return false
  }

  backendPort = await findFreePort(5000)
  const dataDir = path.join(app.getPath('userData'), 'backend-data')
  const logPath = path.join(app.getPath('userData'), 'backend.log')
  const logFd = fs.openSync(logPath, 'a')

  backendProc = spawn(exe, ['--port', String(backendPort), '--data-dir', dataDir], {
    cwd: path.dirname(exe),
    stdio: ['ignore', logFd, logFd],
    windowsHide: true,
  })
  backendProc.on('exit', (code) => {
    console.warn('[backend] 进程退出，code =', code)
    backendProc = null
  })

  const ok = await waitForBackend(backendPort)
  if (ok) {
    // 内置后端就绪 → 覆盖 backendUrl，前端 request.ts 走 IPC 拿到正确端口
    writeBackendUrl(`http://127.0.0.1:${backendPort}`)
    console.log(`[backend] 内置后端就绪：http://127.0.0.1:${backendPort}`)
  } else {
    console.error('[backend] 30 秒内未就绪，查看日志：', logPath)
  }
  return ok
}

function stopBackend() {
  if (!backendProc) return
  try {
    // Windows 下 kill 整个进程树，避免残留 waitress 子进程
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProc.pid), '/T', '/F'], { windowsHide: true })
    } else {
      backendProc.kill('SIGTERM')
    }
  } catch (e) {
    console.warn('[backend] 结束进程失败：', e.message)
  }
  backendProc = null
}

// ---------------------------------------------------------------------------
// 窗口
// ---------------------------------------------------------------------------
const isDev = !app.isPackaged

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // 本地应用加载 app.asar 内 file:// 协议的 ESM 模块，关闭 webSecurity 避免 CORS 拦截
      webSecurity: false,
    },
  })

  // 把渲染进程的 console 日志回写到 userData/renderer.log，便于排查白屏
  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const levels = { 0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR' }
    const label = levels[level] || 'LOG'
    const line2 = `[renderer] [${label}] ${message}${sourceId ? ' @ ' + sourceId + ':' + line : ''}`
    console.log(line2)
    try {
      const logPath = path.join(app.getPath('userData'), 'renderer.log')
      fs.appendFileSync(logPath, line2 + '\n')
    } catch (e) {}
  })

  win.webContents.on('did-finish-load', () => {
    const u = win.webContents.getURL()
    console.log('[main] did-finish-load:', u)
    try {
      fs.appendFileSync(path.join(app.getPath('userData'), 'renderer.log'), `[main] did-finish-load: ${u}\n`)
    } catch (e) {}
  })
  win.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.log('[main] did-fail-load:', errorCode, errorDescription, validatedURL)
    try {
      fs.appendFileSync(path.join(app.getPath('userData'), 'renderer.log'), `[main] did-fail-load: ${errorCode} ${errorDescription} ${validatedURL}\n`)
    } catch (e) {}
  })

  if (isDev) {
    // 开发态：连 Vite dev server（vite.config 已把 /api 代理到 Flask:5000）
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools()
  } else {
    // 生产态：加载打包进来的 Vue 构建产物
    // asar 已禁用（package.json build.asar:false），避免 ESM 在 asar 内动态导入失败
    win.loadFile(path.join(__dirname, 'vue', 'dist', 'index.html'))
  }
}

// ---------------------------------------------------------------------------
// 设置相关 IPC（前端读取/保存后端地址）
// ---------------------------------------------------------------------------
ipcMain.on('get-backend-url', (event) => {
  event.returnValue = readBackendUrl()
})
ipcMain.handle('set-backend-url', (event, url) => {
  writeBackendUrl(url)
  return readBackendUrl()
})

// ---------------------------------------------------------------------------
// 自动更新（electron-updater，仅生产打包态启用；开发态跳过以免误报）
// ---------------------------------------------------------------------------
function initAutoUpdater() {
  if (isDev) return
  let autoUpdater
  try {
    autoUpdater = require('electron-updater').autoUpdater
  } catch (e) {
    console.warn('[updater] electron-updater 未安装，跳过自动更新', e.message)
    return
  }

  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true

  const send = (state, extra = {}) =>
    BrowserWindow.getAllWindows().forEach((w) =>
      w.webContents.send('update-status', { state, ...extra })
    )

  autoUpdater.on('checking-for-update', () => send('checking'))
  autoUpdater.on('update-available', (info) =>
    send('available', { version: info && info.version })
  )
  autoUpdater.on('update-not-available', () => send('not-available'))
  autoUpdater.on('download-progress', (p) =>
    send('downloading', { percent: Math.floor(p.percent || 0) })
  )
  autoUpdater.on('update-downloaded', (info) =>
    send('downloaded', { version: info && info.version })
  )
  autoUpdater.on('error', (err) => send('error', { message: err.message }))

  ipcMain.handle('check-for-updates', async () => {
    try {
      await autoUpdater.checkForUpdates()
      return { ok: true }
    } catch (e) {
      return { ok: false, message: e.message }
    }
  })
  ipcMain.handle('restart-and-install', () => {
    autoUpdater.quitAndInstall()
  })

  // 启动后静默检查一次
  autoUpdater.checkForUpdates().catch(() => {})
}

// ---------------------------------------------------------------------------
// 生命周期
// ---------------------------------------------------------------------------
app.whenReady().then(async () => {
  // 打包态：先拉起内置后端（探活通过或超时后再开窗，避免首屏全是请求报错）
  if (!isDev) {
    await startBackend()
  }
  createWindow()
  initAutoUpdater()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
