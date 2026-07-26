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

## 内置后端（一键启动）

自 v1.1.0 起安装包捆绑 Python 后端（PyInstaller 冻结产物），用户双击即用、无需装 Python/MySQL：

- **打包**：`cd backend && pyinstaller studymate-backend.spec --noconfirm` 产出 `backend/dist/studymate-backend/`（约 99MB），由 `build.extraResources` 拷进安装包 `resources/backend/`。
- **启动链路**：`main.js` 在打包态 spawn `studymate-backend.exe --port <空闲端口> --data-dir <userData>/backend-data` → 轮询 `/api/health`（最长 30s）→ 就绪后写回 `settings.json` 的 `backendUrl` → 再开窗口；`before-quit` 时 `taskkill /T /F` 清理整个进程树。
- **数据**：SQLite（`userData/backend-data/studymate.db`，首启 `db.create_all()` 自动建表），RAG 索引同目录；后端日志在 `userData/backend.log`。
- **入口差异**（`backend/desktop_run.py` vs `run.py`）：waitress 替代 Flask dev server；DATABASE_URL 缺省为 SQLite；无 DeepSeek 密钥时 `PDF_AI_MOCK=true`、无微信 AppID 时 `WECHAT_MOCK=true`（保证单机可登录）。
- **体积取舍**：spec 排除了 torch / sentence-transformers / faiss（否则 +2GB）。RAG 自动回退**关键词检索**；需完整向量检索时删掉 excludes 重打后端。
- 若内置后端 exe 缺失（如开发者手工删了 extraResources），回退用 `settings.json` 里的外部 `backendUrl`。

## 后端地址

- 打包态由主进程自动写入（内置后端实际端口）；开发态默认 `http://127.0.0.1:5000`。
- `request.ts` 在 Electron 下读取 `electronAPI.getBackendUrl()`，拼成 `${url}/api`；非 Electron（vite dev）则走 `/api` 由 vite proxy 转发。
- 注意：内置后端就绪时会覆盖 `settings.json` 的 `backendUrl`；如要强制连远程后端，需删除内置后端目录或后续加设置 UI 开关。

## 已知限制 / 取舍

- **未做代码签名**：`build.win.signAndEditExecutable: false` 跳过 exe 资源编辑/签名，故安装包使用 Electron 默认图标与版本信息。
  - 若要正式签名（Authenticode）：移除该开关、用 `CSC_LINK` 指向 `.pfx` 证书（或 Windows 证书存储），并在**具备创建符号链接权限**的环境构建。
- **winCodeSign 解压需符号链接权限**：electron-builder 拉取的 `winCodeSign` 工具链 `.7z` 含 darwin 软链，在**无建链特权**的 Windows 上解压失败（已知问题）。
  - 规避：以管理员运行 / 开启 Windows「开发者模式」（授予软链权限）；或手动 `7z x -sni` 预解压缓存。
  - 本项目构建时通过 `signAndEditExecutable: false` 绕开了该工具链，故可在受限环境出包（代价如上）。
- **仅 NSIS 安装包**：已按需求选 NSIS；如需 squirrel/portable 改 `build.win.target` 即可。
