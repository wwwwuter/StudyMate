# StudyMate

基于 AI 大模型的智能考研学习助手（Windows 桌面端）。

StudyMate 帮助你制定学习计划、按计划计时学习、自动统计学习数据，并结合 AI 解析上传的计划文件（Word / PDF / 截图），一键生成排期。桌面端采用 Electron 外壳，内置 Python 后端，**双击安装即用，无需安装 Python / MySQL**。

## 功能特性

- **学习计划**：上传计划文件（Word / PDF / 图片截图）→ AI 识别日期、科目与时间段 → 复核确认落库 → 到点提醒
- **计时系统（4 种模式）**：
  - 🍅 番茄钟（25 分钟专注 + 5 分钟休息，**休息不计入学习时长**）
  - 📋 任务计时（绑定 StudyTask，计入任务学习时间）
  - ⏱ 自由计时（临时学习）
  - ⏳ 倒计时（绑定任务剩余时间）
- **学习统计（今日 / 全部双 Tab）**：学习时长、任务完成率、连续打卡、30 天趋势折线、科目投入饼图、**计时模式分布环形图**（番茄 / 任务 / 自由 / 倒计时分别统计）
- **AI 接入**：在「设置」页填你自己的 API Key（DeepSeek / 通义千问 / 智谱兼容），密钥只存本机，不上传、无内置密钥
- **本地账号**：注册 / 登录 / 修改密码，JWT 鉴权
- **自动更新**：electron-updater 对接 GitHub Releases，启动静默检查、下载完成提示安装

## 技术栈

| 层 | 技术 |
| --- | --- |
| 桌面端 | Electron + Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts |
| 后端 | Python Flask + Flask-SQLAlchemy + waitress（RESTful API） |
| 数据库 | 桌面端默认 **SQLite**（开箱即用）；Web 多用户部署可切 MySQL 8.0 + Alembic 迁移 |
| 打包 | PyInstaller（后端 exe）+ electron-builder（NSIS 安装包）+ electron-updater |

## 目录结构

```
StudyMate
├── desktop/                    # 桌面端
│   ├── vue/                    # Vue3 + TS 前端（api / views / router / stores / composables）
│   │   └── src/views/stat/     # 学习统计页（今日 / 全部，含图表组件）
│   └── electron/               # Electron 主进程 + electron-builder 打包配置
│       ├── main.js             # 窗口 / 内置后端进程管理 / 自动更新 / 后端地址 IPC
│       ├── preload.js          # contextBridge 暴露 electronAPI
│       └── package.json        # build 配置（NSIS / extraResources / publish）
├── backend/                    # Flask 后端
│   ├── app/                    # 应用工厂 create_app、配置、扩展、schema_migrate
│   ├── models/                 # ORM：User / AuthSession / StudyTask / StudyRecord /
│   │                           #       TimerSession / PomodoroCycle / Reminder / AI 设置
│   ├── routes/                 # 蓝图：auth / user / task / record / plan(计时) / stat / reminder / schedule / ai
│   ├── services/               # 业务层：plan_service / stat_service / auth_service / reminder_service / scheduler
│   ├── ai/                     # AI：DeepSeek 兼容客户端 + Prompt 管理（Key 由用户提供）
│   ├── parser/                 # 文件解析（PDF / Word）
│   ├── utils/                  # 本地鉴权 / 时间 / 科目归一化 / 加密
│   ├── tests/                  # pytest 单测（SQLite 内存库）
│   ├── desktop_run.py          # 桌面端入口（waitress + SQLite 兜底，接受 --port / --data-dir）
│   ├── run.py                  # Web 部署入口（默认 127.0.0.1:5000）
│   ├── build_backend.py        # PyInstaller 打包脚本（产物 backend/dist/studymate-backend/）
│   └── requirements.txt        # Python 依赖
├── docs/                       # 项目文档
└── README.md
```

## 快速开始（开发模式）

### 1. 后端

```bash
cd backend
python -m venv ../.venv                 # 首次
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/python desktop_run.py --port 5088 --data-dir D:/StudyMate/data
# 健康检查：http://127.0.0.1:5088/api/health
```

> 桌面端入口 `desktop_run.py` 默认使用 SQLite（`--data-dir` 指定目录），无需 MySQL。
> Web 模式用 `run.py`，按 `.env.example` 配置 MySQL 连接。

### 2. 前端（Vue）

```bash
cd desktop/vue
npm install
npm run dev            # Vite dev server：http://localhost:5173（/api 代理到 5088）
```

### 3. 桌面端（Electron 开发态）

```bash
cd desktop/electron
npm install
npm run dev            # 并行启动 Vite + Electron，连 dev server，热更新
```

## 打包发布（桌面 app）

```bash
# 1) 打包后端为 exe（PyInstaller，产物 backend/dist/studymate-backend/）
cd backend && python build_backend.py

# 2) 打包前端（Vue 构建产物进 desktop/vue/dist）
cd desktop/vue && npm run build

# 3) 打包 Electron 安装包（NSIS，产物 desktop/electron/release/StudyMate-Setup-x.x.x.exe）
cd desktop/electron && npm run dist
# 发布到 GitHub Releases：npm run release（需 GH_TOKEN）
```

打包后的 app 内置后端 exe + SQLite，用户双击安装即用；数据与日志位于 `%APPDATA%/StudyMate/`。详见 `desktop/README.md`。

## 数据库

- **桌面端**：SQLite（`<data-dir>/studymate.db`，默认 `%APPDATA%/StudyMate/backend-data`）。首次启动自动建表，已有库自动补齐新增列（`app/schema_migrate.py`）。
- **Web / 生产**：MySQL 8.0 + Flask-Migrate（Alembic）迁移，见 `backend/README.md`。

## 测试

```bash
cd backend
../.venv/Scripts/python -m pytest -q        # 全量（当前 72 项全过）
```

前端类型检查：`cd desktop/vue && npm run build`（含 `vue-tsc`）。

## 开发规范

- Route / Service / Model 分层，路由层只做参数校验与响应封装（统一 `{ code, message, data }` 信封）。
- Vue 组件化，业务逻辑拆分到 `composables/` 与 `api/`。
- 配置通过环境变量读取（python-dotenv），禁止在代码中写死密码 / 密钥；AI Key 只存本机数据库。
- 提交前跑 `pytest` + 前端 `npm run build` 保证不破坏现有功能。
