const { contextBridge, ipcRenderer } = require('electron')

// 渲染进程通过 window.electronAPI 安全访问主进程能力（contextIsolation 开启）
contextBridge.exposeInMainWorld('electronAPI', {
  // 后端地址：同步读取（request.ts 模块初始化时需要）
  getBackendUrl: () => ipcRenderer.sendSync('get-backend-url'),
  setBackendUrl: (url) => ipcRenderer.invoke('set-backend-url', url),

  // 自动更新
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  restartAndInstall: () => ipcRenderer.invoke('restart-and-install'),
  onUpdateStatus: (callback) => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('update-status', listener)
    // 返回取消订阅函数
    return () => ipcRenderer.removeListener('update-status', listener)
  },
})
