# StudyMate 后端服务

智能考研学习助手（11408）的后端 API 服务。

- **技术栈**：Python 3.13 · Flask 3 · Flask-SQLAlchemy (ORM) · Flask-Migrate (Alembic) · MySQL 8.0 · PyJWT · PyMySQL
- **当前阶段**：Phase 8 DeepSeek + RAG 知识库（API 调用加固 / 文件化 Prompt 管理 / 向量 RAG 问答）
- **接口规范**：RESTful JSON API，统一响应结构 `{ code, message, data }`

---

## 1. 目录结构

```
backend/
├── app/                      # 应用工厂
│   ├── __init__.py          # create_app(): 初始化扩展、注册蓝图、健康检查路由
│   ├── config.py            # Config / Development / Production + config_map
│   └── extensions.py        # db / migrate / cors 等全局扩展（避免循环导入）
├── models/                  # ORM 模型
│   ├── user.py             # User（微信用户：openid/unionid/资料/登录时间）
│   ├── login_ticket.py     # LoginTicket（扫码登录票据：pending→confirmed/expired）
│   ├── task.py             # StudyTask（学习计划/任务实体，含状态/来源枚举）
│   └── record.py / analysis.py   # 计时记录 / AI 分析（后续阶段）
├── routes/                  # 蓝图（路由层，仅做参数校验与响应封装）
│   ├── auth.py             # 鉴权：扫码登录、code 登录、刷新、当前用户
│   ├── user.py             # 用户：资料查询与更新
│   └── task.py             # 学习计划：CRUD / 批量 / Excel·JSON·PDF 导入 / 统计
├── services/                # 业务层（与路由解耦，便于单测）
│   ├── auth_service.py     # 令牌签发/刷新、扫码流程编排
│   ├── wechat_service.py   # 微信 code2session / 二维码（支持 MOCK 模式）
│   └── plan_service.py     # 学习计划 CRUD 与导入编排（Phase 3）
├── parser/                  # 文件解析（延迟导入重依赖，启动不强制安装）
│   ├── excel_parser.py     # Excel 学习计划（表头感知）
│   ├── json_parser.py      # JSON 学习计划
│   └── pdf_parser.py       # PDF 学习计划（需 pdfminer.six）
├── utils/
│   ├── jwt_utils.py        # 双令牌生成/校验、login_required 装饰器
│   ├── time_utils.py       # 时区安全的 utcnow()
│   └── subject_utils.py    # 科目归一化（高数→数学 等）
├── tests/                  # pytest 单元测试（SQLite 内存库，不依赖 MySQL）
│   ├── conftest.py
│   ├── test_auth.py        # Phase 2 用户系统
│   └── test_plan.py        # Phase 3 学习计划系统
├── migrations/              # Flask-Migrate 迁移脚本（Alembic）
├── requirements.txt        # 运行依赖
├── requirements-dev.txt    # 开发/测试依赖
├── run.py                  # 入口：监听 127.0.0.1:5000
└── .env.example            # 环境变量模板（复制为 .env 后填写）
```

---

## 2. 环境准备

### 2.1 Python 虚拟环境

```bash
cd backend
python -m venv ../.venv          # 或自建 venv
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/pip install -r requirements-dev.txt
```

### 2.2 MySQL

- 已注册为 Windows 服务 `StudyMateMySQL`（开机自启），数据目录 `D:\StudyMate\mysql_data`。
- 手动管理：`net start StudyMateMySQL` / `net stop StudyMateMySQL`
- 确保存在数据库 `studymate`（utf8mb4）：

```sql
CREATE DATABASE IF NOT EXISTS studymate CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2.3 环境变量

复制模板并填写：

```bash
cp .env.example .env
```

关键配置（详见 `.env.example`）：

| 变量 | 说明 | 默认 |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy 连接串，优先于 MYSQL_* 片段 | `mysql+pymysql://root@localhost:3306/studymate?charset=utf8mb4` |
| `JWT_SECRET_KEY` / `JWT_SECRET` | JWT 签名密钥（**生产务必修改**） | `dev-jwt-secret` |
| `JWT_ACCESS_EXPIRATION_HOURS` | access token 有效期 | `2` |
| `JWT_REFRESH_EXPIRATION_DAYS` | refresh token 有效期 | `30` |
| `WECHAT_APP_ID` / `WECHAT_APP_SECRET` | 微信小程序凭证（真实登录用） | 空 |
| `WECHAT_MOCK` | `true` 时微信接口返回确定性 mock openid（无真实 AppID 也能跑通登录/测试） | `false` |
| `LOGIN_QR_EXPIRE_SECONDS` | 扫码票据有效期 | `300` |
| `QR_LOGIN_BASE_URL` | 二维码内容前缀 | `studymate://login` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（AI 阶段用） | 空 |
| `LEARNING_REPORT_MOCK` | `true` 时学习报告强制走离线模板（不调用 DeepSeek，便于测试/离线） | `false` |

---

## 3. 启动

```bash
# 开发模式
export FLASK_APP=app:create_app
../.venv/Scripts/python run.py
# 或
../.venv/Scripts/flask run
```

启动后：

- 健康检查：`GET http://127.0.0.1:5000/api/health` → `{"status":"ok",...}`
- 根路径：`GET http://127.0.0.1:5000/` → `StudyMate Backend Running`

---

## 4. 数据库迁移（Flask-Migrate）

```bash
export FLASK_APP=app:create_app
../.venv/Scripts/flask db migrate -m "描述本次变更"
../.venv/Scripts/flask db upgrade     # 应用到数据库
../.venv/Scripts/flask db downgrade    # 回滚一个版本
```

> 注意：`migrations/` 已纳入版本控制；`backend/.env` 被 `.gitignore` 忽略，请勿入库。

---

## 5. Phase 2 用户系统

### 5.1 登录方案

桌面端为 Electron 应用，采用**自生成二维码票据 + 配套微信小程序扫码确认**的登录方式，无需公众号公网回调：

1. 桌面端请求 `POST /api/auth/wechat/qr` 生成 `ticket`，并渲染二维码（内容为 `studymate://login?ticket=xxx`）。
2. 用户在**配套微信小程序**中扫码，小程序用 `wx.login` 取得 `code`，调用 `POST /api/auth/wechat/scan` 上报 `ticket + code`。
3. 桌面端轮询 `GET /api/auth/wechat/qr/status?ticket=xxx`：状态 `pending` → 继续轮询；`confirmed` → 返回 JWT；`expired` → 二维码失效。
4. 也可以走 `POST /api/auth/wechat/login`（小程序内直接 `code` 登录，无需扫码），用于纯小程序场景。

`WeChatService` 在 `WECHAT_MOCK=true` 时返回确定性 mock openid，保证无真实 AppID 也能开发、测试。

### 5.2 扫码登录时序图

```
桌面端(Electron)        Backend           微信小程序
     |                     |                   |
     |-- POST /wechat/qr ->|                   |
     |<- ticket + qr_content|                   |
     | 渲染二维码          |                   |
     |                     |                   | 用户扫码
     |                     |<- POST /wechat/scan(ticket,code)
     |                     |   (code2session 取 openid, 标记 confirmed)
     |                     |                   |
     |-- GET /wechat/qr/status?ticket ->|       |
     |<- {status:pending} -|                   |
     |       (轮询中...)    |                   |
     |-- GET /wechat/qr/status?ticket ->|       |
     |<- {status:confirmed, token, user} ------|
     |  本地保存 JWT，登录完成                 |
```

### 5.3 JWT 双令牌

- **access token**：有效期短（默认 2h），用于业务接口鉴权，请求头 `Authorization: Bearer <access_token>`。
- **refresh token**：有效期长（默认 30d），仅用于 `POST /api/auth/refresh` 无感换发新双令牌。
- 令牌载荷：`{ sub: <user_id 字符串>, type: access|refresh, iat, exp }`。
- `utils.jwt_utils.login_required` 装饰器：仅接受 access token，将当前用户注入视图首参；失败返回 401。

### 5.4 用户表（users）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 自增主键 |
| `openid` | string(64) UNIQUE | 微信 openid（唯一身份） |
| `unionid` | string(64) | 跨应用关联（公众号/小程序） |
| `nickname` / `avatar` | string | 昵称 / 头像 |
| `phone` | string(20) | 手机号（可空） |
| `gender` | smallint | 0 未知 / 1 男 / 2 女 |
| `country` / `province` / `city` | string | 地区 |
| `last_login_at` | datetime | 最后登录时间 |
| `create_time` / `update_time` | datetime | 创建 / 更新时间 |

### 5.5 API 参考

统一响应：`{ "code": 200, "message": "...", "data": {...} }`

#### 小程序 code 登录
```
POST /api/auth/wechat/login
Body:   { "code": "<wx.login 返回的 code>" }
→ 200 { data: { token: { access_token, refresh_token }, user: {...} } }
```

#### 生成扫码票据
```
POST /api/auth/wechat/qr
→ 200 { data: { ticket, qr_content: "studymate://login?ticket=...", expire_at } }
```

#### 小程序扫码确认
```
POST /api/auth/wechat/scan
Body:   { "ticket": "...", "code": "<wx.login 返回的 code>" }
→ 200 { message: "已确认扫码" }
```

#### 轮询扫码状态
```
GET /api/auth/wechat/qr/status?ticket=...
→ 200 { data: { status: "pending" | "confirmed", token?, user? } }
→ 410 { data: { status: "expired" } }   # 二维码过期
```

#### 刷新令牌
```
POST /api/auth/refresh
Body:   { "refresh_token": "..." }
→ 200 { data: { token: { access_token, refresh_token } } }
```

#### 当前用户（需鉴权）
```
GET /api/auth/me
Header: Authorization: Bearer <access_token>
→ 200 { data: { id, nickname, avatar, ... } }
```

#### 退出登录
```
POST /api/auth/logout
→ 200 { message: "已退出登录（客户端请清除本地 token）" }
```
> 当前为无状态 JWT，退出由客户端清除本地令牌完成；服务端令牌黑名单（Redis）留待后续阶段。

#### 用户信息 / 更新资料（需鉴权）
```
GET  /api/user/info       → 200 { data: { ... } }
PUT  /api/user/profile
Header: Authorization: Bearer <access_token>
Body:   { "nickname": "...", "avatar": "...", "phone": "...",
          "gender": 1, "country": "...", "province": "...", "city": "..." }
→ 200 { data: { ...更新后用户信息 } }
```
> 仅白名单字段可写（`nickname/avatar/phone/gender/country/province/city`），`openid` 等内部字段被忽略，防止越权写入。

---

## 6. Phase 3 学习计划系统

### 6.1 设计说明
- 本阶段以 `StudyTask`（`study_tasks` 表）作为**学习计划/任务实体**：每一行 = 一个「带日期的具体任务」。
- `plan_source` 标记来源：`manual`(手动) / `excel` / `json` / `pdf` / `auto`，便于统计与追溯。
- 业务逻辑下沉至 `services/plan_service.py`，路由层仅做参数校验与响应封装（与 Phase 2 `AuthService` 一致）。
- 科目归一化（`utils/subject_utils.normalize_subject`）：高数/线代/概率 → 数学；英语一/二 → 英语；马原/毛中特/史纲/思修 → 政治；数据结构/计组/OS/计网 → 408。
- 说明：本阶段未引入独立的「学习计划(plan)」聚合表；当 Phase「每日任务自动生成」需要时，再据实建模。

### 6.2 学习计划表（study_tasks）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int PK | 自增主键 |
| `user_id` | int FK→users.id | 归属用户（数据隔离） |
| `date` | date | 任务日期 |
| `subject` | string(32) | 科目（已归一化） |
| `content` | string(512) | 任务内容 |
| `start_time` / `end_time` | time NULL | 起止时间（可空） |
| `status` | string(16) | `pending` / `done` / `cancelled` |
| `plan_source` | string(16) | `manual` / `excel` / `json` / `pdf` / `auto` |
| `create_time` / `update_time` | datetime | 时间戳 |

### 6.3 API 参考（`/api/tasks`，均需 `Authorization: Bearer <access_token>`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tasks` | 列出任务。查询：`date` / `start_date` / `end_date` / `subject` / `status` / `keyword`；按 date、start_time 排序 |
| POST | `/api/tasks` | 创建单条 |
| POST | `/api/tasks/batch` | 批量创建（body 为任务数组） |
| GET | `/api/tasks/<id>` | 任务详情 |
| PUT | `/api/tasks/<id>` | 更新（date/subject/content/start_time/end_time/status 均可改） |
| DELETE | `/api/tasks/<id>` | 删除 |
| POST | `/api/tasks/import/excel` | Excel 导入（multipart 字段 `file`） |
| POST | `/api/tasks/import/json` | JSON 导入（multipart 字段 `file`） |
| GET | `/api/tasks/stats/daily?date=YYYY-MM-DD` | 当日统计（总数/完成数/完成率/涉及科目） |

任务对象（创建/响应字段一致）：
```json
{
  "date": "2026-08-01",      // 必填 YYYY-MM-DD
  "subject": "数学",         // 必填（支持别名，自动归一化）
  "content": "高数强化",      // 必填
  "start_time": "08:30",     // 可选 HH:MM
  "end_time": "11:30",       // 可选 HH:MM
  "status": "pending"        // 可选 pending|done|cancelled
}
```

请求/响应示例：
```
POST /api/tasks
Body:  { "date":"2026-08-01", "subject":"高数", "content":"极限", "start_time":"08:00", "end_time":"10:00" }
→ 201 { code:200, data:{ id, date:"2026-08-01", subject:"数学", content:"极限", start_time:"08:00", ... } }

GET /api/tasks?date=2026-08-01&subject=数学
→ 200 { code:200, data:[ ... ] }
```

### 6.4 Excel 导入格式
- 表头映射（中/英均可）：`日期`/`date`、`科目`/`subject`、`内容`/`content`、`开始时间`/`start_time`、`结束时间`/`end_time`、`状态`/`status`。
- 无表头时按位置兜底：列1 日期、列2 科目、列3 内容、列4 开始、列5 结束、列6 状态。
- 跳过缺日期或缺内容的行；状态非法自动回退 `pending`；科目自动归一化。
- 示例：

| 日期 | 科目 | 内容 | 开始时间 | 结束时间 | 状态 |
|---|---|---|---|---|---|
| 2026-08-01 | 数学 | 高数强化 | 08:30 | 11:30 | pending |
| 2026-08-02 | 英语 | 阅读 | 14:00 | 16:00 | |

### 6.5 JSON 导入格式
- 两种顶层结构：数组，或 `{ "tasks": [...] }`。
- 每项字段同 6.3 任务对象；`date` 必填且格式正确，否则该项被跳过。
- 示例：
```json
{
  "tasks": [
    {"date": "2026-08-01", "subject": "高数", "content": "极限", "start_time": "08:00", "end_time": "10:00"},
    {"date": "2026-08-02", "subject": "英语", "content": "单词", "status": "done"}
  ]
}
```
> 导入响应含 `data.count`（成功条数）与 `data.tasks`（落库后的任务列表）。

### 6.6 测试
- `tests/test_plan.py`：SQLite 内存库 + 真实 JWT，覆盖 CRUD、批量、过滤（date/subject/status）、鉴权 401、以及 Excel（openpyxl 内存生成）/JSON 上传导入。
- 运行：`python -m pytest tests/ -v`（Phase 2 + Phase 3 共 26 项全过）。

---

## 7. Phase 7 数据分析与学习报告

### 7.1 设计说明
- 从计时记录（`StudyRecord`）与学习计划（`StudyTask`）按时间范围聚合出「学习报告」所需的全部指标，**纯计算、不依赖 AI**，由 `services/analytics_service.build_report()` 完成。
- AI 文字总结独立可降级：有 `DEEPSEEK_API_KEY` 时走 DeepSeek，否则（或 `LEARNING_REPORT_MOCK=true`）走确定性模板，保证报告始终可用。
- 路由层（`routes/analytics.py`）仅做参数校验、权限（`login_required`）与响应封装；指标计算与 AI 调用解耦，便于单测。

### 7.2 指标维度（覆盖：时长 / 完成率 / 科目 / 连续打卡 / 时段）
`build_report(user_id, range_type='week', start=None, end=None)` 返回：

| 字段 | 说明 |
|---|---|
| `range` / `start` / `end` | 生效的时间范围（day/week/month/all 或自定义 start-end） |
| `total_seconds` / `total_hours` | 总学习时长（秒 / 小时） |
| `session_count` | 计时会话数 |
| `avg_session_minutes` / `daily_avg_minutes` | 平均单次时长 / 日均时长（分钟） |
| `by_mode` | 按计时模式（pomodoro/countup/countdown）的秒数分布 |
| `by_subject_actual` | 按科目的实际学习秒数 |
| `by_subject_planned` | 按科目的计划分钟数（`StudyTask.estimated_minutes`） |
| `daily` | 每日 `{date, seconds}` 序列 |
| `hour_distribution` | 24 小时时段 `{hour, seconds}` 分布 |
| `tasks` | `{total, done, pending, completion_rate, planned_minutes, actual_minutes}` |
| `streak` | 连续打卡天数（以今天或昨天为终点向前数） |
| `best_day` | 学习时长最高的一天 `{date, seconds}` |

### 7.3 API 参考（`/api/analytics`，均需 `Authorization: Bearer <access_token>`）

#### 聚合报告（无 AI）
```
GET /api/analytics/report?range=week            # 或 day / month / all
GET /api/analytics/report?start=2026-07-01&end=2026-07-31   # 自定义区间
→ 200 { code:200, data: { <见 7.2 指标> } }
→ 400 { code:400, message:"非法 range，应为 day/week/month/all" }   # range 非法
```

#### 生成 AI 学习报告（生成 + 落库）
```
POST /api/analytics/summary
Header: Authorization: Bearer <access_token>
Body:   { "range": "week" }          # 可选 start / end
→ 200 { code:200, data: {
        "text": "<报告正文>",
        "source": "ai" | "template",  # ai=DeepSeek 生成，template=离线模板降级
        "analysis_id": 12,            # ai_analysis 自增主键，便于回看
        "range": "week"
      } }
```
- 落库：每次生成都会写入 `ai_analysis`（`analysis_type='learning_report'`，`input_data` 存指标 JSON，`output_data` 存正文）。
- AI 降级开关：环境变量 `LEARNING_REPORT_MOCK=true` 强制走模板（测试 / 离线环境用）；配置了 `DEEPSEEK_API_KEY` 且开关关闭时走真实 DeepSeek，单次失败自动回退模板。

### 7.4 前端
- `desktop/vue/src/views/AnalyticsView.vue`：KPI 卡片（总时长 / 会话数 / 平均单次 / 日均 / 连续打卡 / 完成率）+ 6 张 ECharts（每日趋势、模式分布、科目实际时长、计划 vs 实际、24h 时段分布、任务完成情况）+ 「生成 AI 学习报告」区。
- 路由 `/stats` → `AnalyticsView`，侧边栏与顶栏标题已更新为「数据分析」。

### 7.5 测试
- `tests/test_analytics.py`：SQLite 内存库 + `WECHAT_MOCK=true`，覆盖指标聚合（时长/模式/科目/时段/完成率/连续打卡）、非法 range 返回 400、自定义区间、以及 `POST /summary` 模板降级生成并落库 `ai_analysis`。
- 运行：`python -m pytest tests/test_analytics.py -v`（4 项全过）。

---

## 8. Phase 8 DeepSeek + RAG 知识库

### 8.1 三大交付物

1. **API 调用（加固）** — `ai/deepseek_client.py`
   - 支持 env 配置：`DEEPSEEK_API_KEY` / `DEEPSEEK_API_BASE` / `DEEPSEEK_MODEL` / `DEEPSEEK_TIMEOUT` / `DEEPSEEK_MAX_RETRIES`。
   - 对瞬时错误（超时 / 429 限流 / 5xx）做指数退避重试（上限 30s），认证错误（401）立即抛出不重试。
   - 错误分类为 `DeepSeekAuthError` / `DeepSeekRateLimitError` / `DeepSeekTransientError` / `DeepSeekAPIError`，便于上层精确处理。
   - 延迟加载 openai、支持注入 client（测试用），`is_available()` 判断 Key 是否就绪。

2. **Prompt 管理（文件化）** — `ai/prompt_manager.py` + `prompts/*.txt`
   - 提示词外置到 `backend/prompts/*.txt`，首行 `# desc:` 为元信息描述；代码经 `PromptManager` 加载/渲染，**文件优先、缺文件回退 `ai/prompt.py` 内置常量**。
   - 渲染统一用 `<<<VAR>>>` 哨兵替换，避免 JSON 大括号触发 `.format` 的 `KeyError`（沿用 Phase 4 修复思路）。
   - `PromptManager.list_prompts()` 暴露全部可用提示词（key / 描述 / 预览），便于后续做管理界面。

3. **RAG 知识库（向量化）** — `ai/rag.py`
   - 向量化默认用本地 `sentence-transformers`（模型名 `RAG_EMBEDDING_MODEL`，默认中文向量模型 `shibing624/text2vec-base-chinese`），**首次使用自动下载、离线可用**；加载失败自动回退关键词检索。
   - 中文感知分块（按段落 + 滑动窗口 + 重叠），注入 embedder 可绕过 torch 做测试。
   - 每用户：内存缓存 + 磁盘持久化（`data/rag/{user_id}.index` + `.meta.json`，FAISS 优先、不可用时存 numpy `.npy`）。
   - `retrieve(user_id, query)` 返回 `[{material_id, title, score, snippet, content}]`；`rebuild` / `invalidate` 管理索引；资料上传/删除时路由自动 `invalidate`，下次查询懒重建。

### 8.2 API 参考（`/api/rag`，均需 `Authorization: Bearer <access_token>`）

```
POST /api/rag/query            # 基于资料库的 RAG 问答
Body:   { "question": "特征值与特征向量？", "top_k": 4 }   # top_k 可选
→ 200 { code:200, data: {
      "answer": "<回答正文>",
      "sources": [ {material_id, title, score, snippet, content}, ... ],
      "source": "ai" | "retrieval" | "empty"
        # ai=DeepSeek 生成；retrieval=未连 AI 仅返回检索片段；empty=无相关资料
    } }

POST /api/rag/index            # 重建当前用户索引（通常无需手动，上传/删除资料自动失效）
→ 200 { code:200, data: { chunk_count, mode } }

GET  /api/rag/status           # 索引状态
→ 200 { code:200, data: { indexed, chunk_count, mode, model, vector_available } }
```

- RAG 问答编排在 `ai/service.py` 的 `AIService.rag_answer()`：先向量检索资料 → 渲染 `rag_chat` 提示词（检索上下文 + 问题）→ 调用 DeepSeek；无 Key 或 AI 失败时回退返回检索片段文本。
- `routes/material.py` 的上传/删除接口在提交后调用 `rag_service.invalidate(user_id)`，保证索引最终一致。
- `routes/material.py` 的 `/match`（轻量关键词匹配）保留原行为，不触发向量模型下载。

### 8.3 前端
- `desktop/vue/src/api/rag.ts`：`ragQuery` / `ragIndex` / `ragStatus`。
- `desktop/vue/src/views/RagView.vue`：类聊天界面（提问框 + 回答气泡 + 来源资料卡片 + 来源标签 DeepSeek/检索/无资料 + 「重建索引」按钮 + 索引状态），`/ai` 路由指向该视图，侧边栏与顶栏标题为「AI 知识库」。

### 8.4 测试
- `tests/test_prompt_manager.py`：哨兵渲染、缺失变量保留哨兵、`list_prompts` 覆盖全部 key。
- `tests/test_deepseek_client.py`：无 Key 报错、重试后成功、认证错误不重试、瞬时错误重试后失败、可用性判断。
- `tests/test_rag.py`：注入确定性 embedder 验证向量检索命中、磁盘持久化 + 重载、关键词兜底、失效清理。
- `tests/test_ai.py`：AIService 的 RAG 问答 ai/retrieval 双路径、`learning_report` 模板降级、以及 `/api/rag/query` 路由（含缺参 400）。
- 运行：`python -m pytest tests/test_prompt_manager.py tests/test_deepseek_client.py tests/test_rag.py tests/test_ai.py -v`（共 21 项全过）。

---

## 9. 测试

使用 pytest，基于 **SQLite 内存库 + `WECHAT_MOCK=true`**，不依赖本地 MySQL：

```bash
export FLASK_APP=app:create_app
../.venv/Scripts/python -m pytest tests/ -v
```

覆盖场景：小程序 code 登录、扫码建票/确认/轮询拿令牌、票据过期、refresh 换发、`/me` 鉴权、资料更新与越权字段防护、计时统计、资料库 CRUD、提醒设置，以及 Phase 7 学习报告聚合与 AI 总结落库。

---

## 10. 后续阶段

- **Phase 7 已完成**：学习数据指标聚合、ECharts 可视化、DeepSeek/模板双轨 AI 学习报告。
- **待做**：每日任务自动生成、每任务自定义提醒、桌面原生提醒推送、真实 OCR 与 RAG 向量检索、Redis 令牌黑名单、软删除回收站。
- **Redis**：缓存与 JWT 黑名单（支持服务端主动失效令牌）。
- **生产部署**：修改 `JWT_SECRET`、配置真实 `WECHAT_APP_ID/SECRET`、关闭 `WECHAT_MOCK`、使用环境变量注入数据库凭证。

---

## 11. 常见问题

- **启动报 `ModuleNotFoundError: pdfminer / openpyxl / openai`**：这些是后续阶段的重依赖，已在导入处改为延迟导入，启动后端不依赖它们。需要对应功能时再 `pip install -r requirements.txt` 补齐。
- **迁移报 `Cannot drop index` / 表已存在**：早期残留表结构与当前模型不一致，清空 `studymate` 库重新 `flask db upgrade` 即可（开发环境无业务数据）。
- **`InvalidSubjectError`**：PyJWT 要求 `sub` 为字符串，令牌中已用 `str(user_id)`。
