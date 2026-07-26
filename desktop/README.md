# StudyMate 桌面端（Electron）

Vue 前端 SPA 被打包进 Electron 外壳，产出 Windows 安装包，并集成自动更新。
后端（Flask）**单独运行/部署**，桌面端通过 HTTP 连接（默认 `http://127.0.0.1:5000`）。

## 目录结构

```
desktop/
├── electron/            # Electron 主进程（打包配置在此）
│   ├── main.js          # 窗口 / 加载 / 自动更新 / 后端地址 IPC
│   ├── preload.js       # contextBridge 暴露 electronAPI 给渲染进程
│   ├── package.json     # electron-builder 构建与发布配置（build 字段）
│   └── release/         # 构建产物（gitignored：StudyMate-Setup-*.exe / latest.yml / win-unpacked）
└── vue/                # Vue3 + TS + Element Plus 前端
```

## 脚本（在 desktop/electron 下执行）

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 开发态：并行起 Vite dev server + Electron，热更新 |
| `npm run dist` | 构建 Vue + 打包 Windows NSIS 安装包到 `release/` |
| `npm run release` | 构建并**发布**到 GitHub Releases（`--publish=always`，需 `GH_TOKEN`） |

> `dist` / `release` 产物已在根 `.gitignore` 忽略，不入库。

## 自动更新（electron-updater）

- **源**：GitHub Releases（`electron/package.json` 的 `build.publish`）。
- **流程**：打包时生成 `release/latest.yml`（含版本、sha512、大小）；桌面端启动后静默 `checkForUpdates()`，下载完成后弹通知，点击即 `quitAndInstall()`。
- **UI**：`vue/src/App.vue` 消费 `electronAPI.onUpdateStatus`，用 `ElNotification` 提示「正在检查 / 发现新版本 / 更新就绪（点击重启安装）/ 失败」。
- **配置**：把 `package.json` 里的 `repository.url` 与 `build.publish[].owner/repo` 改成你的仓库（`OWNER/REPO` 是占位符）。`latest.yml` 与安装包须由 `npm run release` 上传到同一 Release。

## 后端地址

- 生产态默认 `http://127.0.0.1:5000`，持久化在 `userData/settings.json`（`backendUrl` 字段）。
- `request.ts` 在 Electron 下读取 `electronAPI.getBackendUrl()`，拼成 `${url}/api`；非 Electron（vite dev）则走 `/api` 由 vite proxy 转发。
- 当前改地址需编辑 `settings.json`；后续可加设置 UI。

## 已知限制 / 取舍

- **未做代码签名**：`build.win.signAndEditExecutable: false` 跳过 exe 资源编辑/签名，故安装包使用 Electron 默认图标与版本信息。
  - 若要正式签名（Authenticode）：移除该开关、用 `CSC_LINK` 指向 `.pfx` 证书（或 Windows 证书存储），并在**具备创建符号链接权限**的环境构建。
- **winCodeSign 解压需符号链接权限**：electron-builder 拉取的 `winCodeSign` 工具链 `.7z` 含 darwin 软链，在**无建链特权**的 Windows 上解压失败（已知问题）。
  - 规避：以管理员运行 / 开启 Windows「开发者模式」（授予软链权限）；或手动 `7z x -sni` 预解压缓存。
  - 本项目构建时通过 `signAndEditExecutable: false` 绕开了该工具链，故可在受限环境出包（代价如上）。
- **仅 NSIS 安装包**：已按需求选 NSIS；如需 squirrel/portable 改 `build.win.target` 即可。
