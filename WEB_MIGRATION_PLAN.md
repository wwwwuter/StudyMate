# StudyMate Web 化最小可用（MVP）改造计划

> 目标：把现有 Electron 桌面应用改造成「开网页即用、数据跨设备」的网站版。  
> 核心结论：**业务代码 90%+ 可复用**，真正要改的是「壳（Electron 去除）+ 部署形态 + 多账户/安全」，外加一个产品模型变化（单机单账户 → 多租户）。  
> 估算工时：**约 1.5–2 周 / 1 人**（最小可用）；生产级 SaaS 再加 2–4 周。

---

## 0. 改造后架构

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  浏览器（任意设备）       │         │  服务器                        │
│  Vue 静态站 (dist/)      │  HTTPS  │  nginx                        │
│  - 读 VITE_API_BASE      │ ──────▶ │   ├─ /api  → Flask(gunicorn)  │
│  - Bearer 令牌鉴权       │         │   └─ /     → 静态站根          │
│  - Notification 提醒     │         │  Flask + MySQL + FAISS 索引    │
└─────────────────────────┘         └──────────────────────────────┘
```

**不变的部分（零改动）**：艾宾浩斯排程、解析/统计/RAG 问答、提醒轮询（`useReminders` 用浏览器 `Notification` API，Web 直接可用）、所有按 `current_user.id` 隔离的业务逻辑、RAG 磁盘索引（已按 user_id 分目录）。

---

## 1. 前端去桌面化（约 0.5–1 天）

### 1.1 `desktop/vue/vite.config.ts`

- **删除** `removeCrossorigin()` 插件及其函数定义（第 5–15 行）。该插件仅为 Electron `file://` 协议去除 `crossorigin`，Web（http/https）下不需要，留着反而可能误伤。
- **改** `base: './'`（第 20 行）→ `base: '/'`（站点挂根域名；若挂子路径如 `/studymate/` 则改成对应路径）。
- dev `proxy` 保留（本地联调转发到后端）；生产环境不再依赖它，由 `VITE_API_BASE` 决定。

### 1.2 `desktop/vue/src/api/request.ts`

- **删** 第 7–13 行 `electronAPI.getBackendUrl` 取值逻辑。
- **改** 为：
  ```ts
  const API_BASE = import.meta.env.VITE_API_BASE || '/api'
  ```
  生产站配 `VITE_API_BASE=https://api.yourdomain.com`（跨域时），或留空 `/api`（nginx 同源反代时）。
- `timeout: 15000` 保留全局；AI 预览接口已在 `task.ts` 单点设 90s，无需动。

### 1.3 `desktop/vue/src/App.vue`

- 第 17–52 行「自动更新提示」逻辑已用 `if (api?.onUpdateStatus)` 守卫，Web 下 `window.electronAPI` 为 `undefined`，不会触发——**可保留不崩**。
- 为干净起见，建议**删除** electron-updater 相关代码（`showUpdate`、`onMounted` 里的 `unsubscribe` 订阅、`onBeforeUnmount`），保留 `useReminders()` 与 `useAiKey()` 的 `loadAiKey()`。
- `useReminders` 依赖浏览器 `Notification` + 轮询 `/api/reminders/poll`，**Web 下完全可用**；唯一注意：Notification 权限请求需用户手势触发，在首次进入时引导授权即可。

### 1.4 其余前端文件

- 95% UI 与组件**无需改动**。无需新增文件。
- （可选）`src/main.ts` 已挂全局 errorHandler，保留。

---

## 2. 后端网站化（约 2–3 天）

### 2.1 `backend/app/__init__.py`（CORS 收紧）— 必修

- 第 14 行：
  ```python
  cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
  ```
  **改** 为读取环境变量、限定前端域名：
  ```python
  cors.init_app(app, resources={r"/api/*": {
      "origins": config.CORS_ORIGINS.split(',') if config.CORS_ORIGINS != '*' else '*',
      "supports_credentials": False,  # 用 Bearer 令牌，不需要 cookie
  }})
  ```
  > 若前端与后端同源（nginx 反代 `/api`），CORS 甚至可不配；跨域时填前端域名即可。

### 2.2 `backend/app/config.py`（新增配置项）— 必修

- 新增：`CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')`
- 新增 AI Key 加密开关：`AI_KEY_ENCRYPT = os.getenv('AI_KEY_ENCRYPT', 'false').lower() in ('1','true','yes')`
- 新增生产强制项：`SECRET_KEY` 与 `JWT_SECRET_KEY` 在生产环境必须来自环境变量（已有读取，部署时务必设置强随机值）。
- DB：已有 `DATABASE_URL` / `MYSQL_*` 逻辑，**Web 化直接配 MySQL** 即可，无需改代码。

### 2.3 `backend/models/ai_setting.py`（AI Key 加密存储）— 安全必修

- 现状：`api_key = db.Column(db.String(512))` **明文存储**，仅 `to_dict(mask_key=True)` 输出时脱敏。多用户网站上 DB 一旦泄露会暴露所有用户的第三方 API Key。
- 改造：
  - 引入 `cryptography.Fernet`，密钥来自 `SECRET_KEY`（派生固定 32 字节）。
  - `save_for_user()` 写入前 `fernet.encrypt(api_key.encode())`；`get_for_user()` / 实际调用 DeepSeek 前解密。
  - `to_dict()` 保持脱敏逻辑不变。
  - 由 `AI_KEY_ENCRYPT` 开关控制：开则加密，关则兼容旧明文（便于灰度）。
  - 提供一次性迁移脚本：扫描存量明文记录并重加密。
- 涉及文件：`backend/utils/crypto.py`（新增，加解密工具）。

### 2.4 `backend/routes/auth.py` + `backend/services/auth_service.py`（开放注册）— 功能必修

- 现状：只有 `/api/auth/setup`（建首个本地账号）+ `/api/auth/login`，**无开放注册**，是单机单账户模型。
- 改造：
  - 新增 `POST /api/auth/register`：用户名唯一性校验（查重）+ 创建用户，返回令牌。
  - `/api/auth/setup` 保留为「无用户时初始化首个管理员」，已有用户时返回 409。
  - `auth_service.py` 新增 `register(username, password)`（复用 `setup_account` 的密码哈希逻辑，抽成公共函数）。
  - 注册接口加**基础限流**（如 Flask-Limiter，每 IP 每分钟 N 次），防垃圾注册。
- 前端配合：`desktop/vue/src/views/` 登录页增加「注册」入口（新增 `RegisterView.vue` 或登录页加模式切换），路由 `router/index.ts` 注册 `/register`。

### 2.5 数据库迁移（约 0.5 天）

- 已有 `backend/migrations/`（alembic）。Web 化切换到 MySQL 后：
  ```bash
  flask --app run.py db upgrade   # 针对 MySQL 执行迁移
  ```
- 需**核对** migrations/versions 是否覆盖全部表（用户、任务、记录、材料、AI 设置、提醒、RAG 元数据等）。若存在 sqlite 专属类型（如 `Boolean`/`JSON` 在 MySQL 下 SQLAlchemy 能自动映射，一般无碍），逐版本检查。
- 若迁移不全，退路：临时用 `db.create_all()` 一次性在 MySQL 建表，再补迁移。

---

## 3. 多租户安全审计（约 1 天，必修）

逐路由确认都按 `current_user.id` 过滤、无跨用户泄漏：

- `routes/task.py`、`routes/record.py`、`routes/material.py`、`routes/analytics.py`、`routes/rag.py`、`routes/reminder.py`、`routes/ai_route.py`、`routes/schedule.py` —— 均已用 `@login_required` + `current_user.id`。
- **已确认安全**：RAG 索引按 `user_id` 分目录（`ai/rag.py:_paths` → `data/rag/<user_id>`）；材料 content 存 DB 且带 `user_id`；文件不落盘。
- **需抽查**：提醒表 `reminder` 的归属过滤；analytics 统计是否严格 `user_id` 维度；AI 设置读写是否校验归属。
- 列出审计清单（文件:行号:结论）写入 `docs/tenant-audit.md`。

---

## 4. 部署骨架（约 1–2 天）

### 4.1 `backend/Dockerfile`

- 基于 `python:3.11-slim`，装依赖，`gunicorn` 启动（或 waitress）。
- 入口：`gunicorn -w 4 -b 0.0.0.0:5000 "run:create_app()"`，config 用 `production`。

### 4.2 `docker-compose.yml`

- 服务：`web`(Flask) + `mysql`(8.0) + 可选 `nginx`。
- 挂载卷：MySQL 数据卷、RAG 索引卷（`RAG_INDEX_DIR`）、`.env`。

### 4.3 `nginx/studymate.conf`

- 静态站：`root /var/www/studymate; try_files $uri $uri/ /index.html;`（SPA 回退）。
- 反代：`location /api/ { proxy_pass http://web:5000; }`。
- HTTPS：Let's Encrypt 证书 + 80→443 跳转。
- `client_max_body_size 20m;`（资料上传）。

### 4.4 `.env.example`

- 集中列出：`DATABASE_URL`、`SECRET_KEY`、`JWT_SECRET_KEY`、`CORS_ORIGINS`、`AI_KEY_ENCRYPT`、`RAG_INDEX_DIR`、`RAG_EMBEDDING_MODEL`、`REMINDER_*`、`DEEPSEEK_*`。

### 4.5 静态站托管

- `desktop/vue/dist/` 由 nginx 直接托管（或上传 CDN）。

---

## 5. 可选增强（MVP 之后）

- **Service Worker + Web Push**：关掉标签页也能推送提醒（否则依赖页面在前台轮询，体验与桌面一致）。
- **配额/限流**：按用户限制 AI 调用次数（防滥用、控成本）。
- **管理后台**：用户管理、全局统计、内容审核。
- **对象存储**：资料量大时把 RAG 索引/潜在大文件迁到 S3/OSS。

---

## 6. 执行顺序（建议分 3 个 Phase）

| Phase          | 内容                                           | 交付                          |
| -------------- | -------------------------------------------- | --------------------------- |
| **P1 后端网站化**   | CORS 收紧、MySQL 配置、开放注册、AI Key 加密、迁移           | 后端能在服务器用 MySQL 跑起来、多账户可注册登录 |
| **P2 前端 + 部署** | 去桌面化（vite/request/App.vue）、nginx、Docker、.env | 浏览器打开网页可用、API 通             |
| **P3 审计 + 联调** | 多租户安全审计、端到端联调、限流                             | 安全验收 + 冒烟测试通过               |

---

## 7. 工作量汇总

| 模块                       | 估时                  |
| ------------------------ | ------------------- |
| 前端去桌面化                   | 0.5–1 天             |
| 后端网站化（CORS/MySQL/注册/加密）  | 2–3 天               |
| 多租户安全审计                  | 1 天                 |
| 部署骨架（Docker/nginx/.env）  | 1–2 天               |
| 联调测试                     | 1–2 天               |
| **合计（最小可用）**             | **约 1.5–2 周 / 1 人** |
| 生产级 SaaS（限流/配额/管理台/监控备份） | 再加 2–4 周            |



---

## 8. 风险与注意

1. **AI Key 明文**：上线前必须完成 2.3 加密，否则是合规/安全隐患。
2. **RAG 向量模型**：`shibing624/text2vec-base-chinese` 首次加载需联网下载权重，服务器需能访问 HuggingFace 或提前缓存。
3. **提醒体验**：纯 Web 无 Service Worker 时，提醒依赖页面在前台；如需后台推送需 P1 之后补 Web Push。
4. **注册滥用**：开放注册必须配限流 + 可选验证码/邮箱验证（MVP 可先限流）。
