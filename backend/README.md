# StudyMate 后端服务

智能考研学习助手（StudyMate）的后端 API 服务。

- **技术栈**：Python 3.13 · Flask 3 · Flask-SQLAlchemy (ORM) · waitress · SQLite（桌面端默认）/ MySQL 8.0（Web 部署）
- **认证**：本地账号密码 + JWT（`utils/local_auth.py`，`auth_sessions` 表），Bearer Token 鉴权
- **接口规范**：RESTful JSON，统一响应结构 `{ code, message, data }`

---

## 1. 目录结构

```
backend/
├── app/
│   ├── __init__.py          # create_app(): 初始化扩展、注册蓝图、健康检查
│   ├── config.py            # Config / Development / Production + config_map
│   ├── extensions.py        # db / migrate / cors / limiter
│   └── schema_migrate.py    # SQLite 幂等补列（新增列自动迁移，MySQL 走 Alembic）
├── models/                  # ORM 模型
│   ├── user.py             # User（本地账号：username / password_hash / salt）
│   ├── auth_session.py     # AuthSession（登录会话令牌，30 天过期）
│   ├── task.py             # StudyTask（学习计划/任务）
│   ├── record.py           # StudyRecord（学习记录，record_type: pomodoro/task/countup/countdown/focus）
│   ├── timer_session.py    # TimerSession（计时会话，含 mode 字段）
│   ├── pomodoro_cycle.py   # PomodoroCycle（番茄轮次：专注/休息时长明细）
│   ├── reminder.py         # Reminder / ReminderSetting（提醒）
│   ├── ai_setting.py       # UserAISetting（用户自填 API Key，加密存储）
│   └── vision_setting.py   # UserVisionSetting
├── routes/                  # 蓝图（路由层，仅参数校验与响应封装）
│   ├── auth.py             # 本地账号：注册 / 登录 / 登出 / 当前用户
│   ├── user.py             # 用户：资料、改密码
│   ├── task.py             # 学习计划：CRUD / 批量 / 导入 / 当日统计
│   ├── plan.py             # 计划解析(AI) + 计时（/api/plans/timer/*）
│   ├── stat.py             # 学习统计（/api/stat/today | /api/stat/all）
│   ├── record.py / reminder.py / schedule.py / ai_route.py
├── services/                # 业务层（与路由解耦，便于单测）
│   ├── plan_service.py     # 计划 CRUD 与导入编排
│   ├── stat_service.py     # 今日 / 全部统计（按计时模式拆分）
│   ├── auth_service.py     # 注册 / 登录 / 账号初始化
│   ├── reminder_service.py # 提醒生成与到期扫描（APScheduler）
│   └── scheduler.py        # 日程生成
├── ai/                      # AI 能力（DeepSeek 兼容客户端，Key 由用户提供）
│   ├── deepseek_client.py  # 调用封装（指数退避重试、错误分类）
│   ├── prompt.py / prompt_manager.py  # 提示词（文件优先，内置兜底）
│   └── service.py          # 计划解析 / 学习报告等编排
├── parser/                  # 文件解析（PDF / Word，延迟导入）
├── utils/                   # local_auth(JWT+会话) / time_utils / subject_utils / crypto
├── tests/                   # pytest 单测（SQLite 内存库，不依赖 MySQL）
├── desktop_run.py          # 桌面端入口：waitress + SQLite 兜底，接受 --port / --data-dir
├── run.py                  # Web 入口：默认 127.0.0.1:5000
├── build_backend.py        # PyInstaller 打包脚本 → dist/studymate-backend/
└── requirements.txt        # Python 依赖
```

---

## 2. 启动

```bash
cd backend
python -m venv ../.venv && ../.venv/Scripts/pip install -r requirements.txt

# 桌面端（推荐）：waitress + SQLite
../.venv/Scripts/python desktop_run.py --port 5088 --data-dir D:/StudyMate/data

# Web 部署：按 .env.example 配置 MySQL 后
../.venv/Scripts/python run.py            # 127.0.0.1:5000
```

- 健康检查：`GET http://127.0.0.1:5088/api/health` → `{"status":"ok",...}`
- 桌面端首次启动自动建表，并对已有库幂等补齐新增列（`app/schema_migrate.py`）。

---

## 3. 数据库

- **桌面端（默认）**：SQLite，文件在 `--data-dir/studymate.db`；不需要 MySQL。
- **Web / 生产**：MySQL 8.0（`DATABASE_URL`），用 Flask-Migrate（Alembic）迁移：

```bash
export FLASK_APP=app:create_app
../.venv/Scripts/flask db migrate -m "描述"
../.venv/Scripts/flask db upgrade
```

> 新增表 / 列（如 `timer_sessions.mode`、`pomodoro_cycles` 表）在 MySQL 环境需生成 Alembic 迁移；SQLite 由 `ensure_schema` 兜底。

---

## 4. 核心业务

### 4.1 计时模式体系（pomodoro / task / countup / countdown）

四种计时模式由 `TimerSession.mode` 记录，计时结束自动同步写入 `StudyRecord`（`record_type` 与 mode 一致），作为统计唯一数据源：

| 模式 | TimerSession.mode | StudyRecord.record_type | 说明 |
|---|---|---|---|
| 番茄钟 | `pomodoro` | `pomodoro` | 只统计**专注段**；休息 5 分钟不计入时长 |
| 任务计时 | `task` | `task` | 必须绑定 `task_id` |
| 自由计时 | `countup` | `countup` | 手动开始/结束 |
| 倒计时 | `countdown` | `countdown` | 绑定任务剩余时间 |

接口：
```
POST /api/plans/timer/start    body: { mode, task_id?, duration?, note? }  → 返回 session
POST /api/plans/timer/cycle    body: { session_id, focus_duration, break_duration }   # 番茄轮次上报
POST /api/plans/timer/stop     body: { session_id? }
GET  /api/plans/timer/current
```

番茄钟休息段严格不计入学习时长：`StudyRecord.duration` 只累加各轮 `PomodoroCycle.focus_duration`。

### 4.2 学习统计（/api/stat）

```
GET /api/stat/today    → { date, study_time, task_total, task_completed, completion_rate,
                            subjects, tasks, pomodoro_time, task_time, free_time,
                            sessions: { pomodoro, task, countup, countdown } }
GET /api/stat/all      → { total_time, total_sessions, completed_tasks, completion_rate,
                            continuous_days, trend(30天), subjects,
                            pomodoro_total, task_total, countup_total, countdown_total,
                            mode_distribution: [{ name, mode, value, count }] }
```

时长一律以秒为单位，前端负责格式化。实现见 `services/stat_service.py`。

### 4.3 计划解析（AI）

```
POST /api/plans/parse    文本 / PDF / Word / 图片(截图) → 时间槽计划列表（不落库）
POST /api/plans/confirm  复核后的计划列表落库为 study_tasks（自动生成提醒）
```

AI 调用使用用户在「设置」页配置的 API Key（`user_ai_settings` 加密存储），系统无内置密钥；未配置时返回明确错误提示。

### 4.4 提醒

- `reminder_service.sweep_due_reminders`：按任务开始时间提前量生成提醒；日期型任务当天整点触发。
- 启动时由 `start_scheduler(app)` 拉起 APScheduler 后台线程（desktop_run.py / run.py 一致）。

---

## 5. 接口一览

| 蓝图 | 前缀 | 说明 |
|---|---|---|
| auth | `/api/auth` | 注册 / 登录 / 登出 / me / 改密码 |
| user | `/api/user` | 用户资料 |
| task | `/api/tasks` | 计划 CRUD / 批量 / 导入 / 当日统计 |
| record | `/api/records` | 学习记录 |
| plan | `/api/plans` | 计划解析 + 计时 |
| stat | `/api/stat` | 今日 / 全部统计 |
| reminder | `/api/reminders` | pending / ack / settings / sweep |
| schedule | `/api/schedule` | 日程生成 |
| ai | `/api/ai` | AI 设置读写 / 解析 |
| - | `/api/health` | 健康检查（Electron 探活） |

除 `auth` 注册登录与 `health` 外，均需请求头 `Authorization: Bearer <access_token>`。

---

## 6. 测试

```bash
../.venv/Scripts/python -m pytest -q        # 全量（当前 72 项全过）
```

覆盖：本地账号注册/登录/JWT、计划 CRUD 与导入解析、计时模式（番茄只算专注段、任务绑定 task_id、自由/倒计时）、统计按模式拆分、提醒扫描、DeepSeek 客户端重试与错误分类、Prompt 渲染。

---

## 7. 打包（桌面端内置后端）

```bash
python build_backend.py      # PyInstaller one-folder → dist/studymate-backend/studymate-backend.exe
```

- 入口 `desktop_run.py`；Electron 主进程以 `--port <空闲端口> --data-dir <userData>/backend-data` 拉起。
- 已排除 torch / sentence-transformers / faiss / numpy（体积 +2GB 的向量依赖，当前 RAG 能力不打包）；`--windowed` 无控制台黑窗。
- 新增源码文件放入 `app / models / routes / services / utils / ai / parser` 任一目录即会被收集，无需改 spec。
