const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')

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
    },
  })

  if (isDev) {
    // 开发态：连 Vite dev server（vite.config 已把 /api 代理到 Flask:5000）
    win.loadURL('http://localhost:5173')
  } else {
    // 生产态：加载打包进来的 Vue 构建产物
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
app.whenReady().then(() => {
  createWindow()
  initAutoUpdater()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
