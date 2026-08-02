# StudyMate 前端（Vue 3 + TypeScript）

StudyMate 桌面端的前端 SPA，运行在 Electron 渲染进程内（同时支持纯 Web 构建）。

## 技术栈

Vue 3 · TypeScript · Vite · Pinia · Vue Router（hash 模式）· Element Plus · ECharts · Axios

## 目录

```
src/
├── api/          # 接口封装（request.ts 统一 axios 实例 + api/plan.ts / stat.ts / task.ts / ai.ts / reminder.ts）
├── views/        # 页面：Dashboard / UploadPlanView / TasksView / TimerView / stat/(今日·全部) / SettingsView / AuthView / Reminder*
├── views/stat/   # 学习统计：StudyStat(双 Tab) / TodayStat / AllStat + components/(StatCard·TaskTimeline·StudyChart·TimerModeChart)
├── layout/       # MainLayout / Sidebar / Header
├── router/       # 路由（hash 路由，兼容 Electron file:// 协议）
├── stores/       # Pinia（user 登录态）
├── composables/  # useAiKey / useScheduler（提醒轮询）
└── main.ts
```

## 常用命令

```bash
npm install        # 安装依赖
npm run dev        # Vite dev server（:5173，/api 代理到后端 :5088）
npm run build      # 构建 + vue-tsc 类型检查 → dist/
```

## 后端地址解析

`src/api/request.ts` 按环境取基地址：

- **Electron 打包态**：读 `window.electronAPI.getBackendUrl()`（主进程注入，内置后端实际端口）→ 拼接 `/api`
- **开发态（Vite）**：走相对 `/api`，由 `vite.config.ts` 代理到后端（默认 `http://127.0.0.1:5088`）
- **Web 构建**：可用 `VITE_API_BASE` 指定完整后端地址
