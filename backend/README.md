# StudyMate 后端服务

智能考研学习助手（11408）的后端 API 服务。

- **技术栈**：Python 3.13 · Flask 3 · Flask-SQLAlchemy (ORM) · Flask-Migrate (Alembic) · MySQL 8.0 · PyJWT · PyMySQL
- **当前阶段**：Phase 2 用户系统（微信扫码登录 / 小程序 code 登录 / JWT 双令牌 / 用户管理）
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
│   ├── task.py / record.py / analysis.py   # 学习计划/计时记录/AI 分析（后续阶段）
│   └── __init__.py
├── routes/                  # 蓝图（路由层，仅做参数校验与响应封装）
│   ├── auth.py             # 鉴权：扫码登录、code 登录、刷新、当前用户
│   ├── user.py             # 用户：资料查询与更新
│   └── ...                 # task / record / ai 等（后续阶段）
├── services/                # 业务层（与路由解耦，便于单测）
│   ├── auth_service.py     # 令牌签发/刷新、扫码流程编排
│   └── wechat_service.py   # 微信 code2session / 二维码（支持 MOCK 模式）
├── utils/
│   ├── jwt_utils.py        # 双令牌生成/校验、login_required 装饰器
│   └── time_utils.py       # 时区安全的 utcnow()
├── tests/                  # pytest 单元测试（SQLite 内存库，不依赖 MySQL）
│   ├── conftest.py
│   └── test_auth.py
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

## 6. 测试

使用 pytest，基于 **SQLite 内存库 + `WECHAT_MOCK=true`**，不依赖本地 MySQL：

```bash
export FLASK_APP=app:create_app
../.venv/Scripts/python -m pytest tests/ -v
```

覆盖场景：小程序 code 登录、扫码建票/确认/轮询拿令牌、票据过期、refresh 换发、`/me` 鉴权、资料更新与越权字段防护。

---

## 7. 后续阶段

- **Phase 3+**：学习计划管理、PDF/Excel/JSON 导入、每日任务自动生成、桌面提醒、番茄钟/计时、数据统计、AI 总结与计划优化（DeepSeek）。
- **Redis**：缓存与 JWT 黑名单（支持服务端主动失效令牌）。
- **生产部署**：修改 `JWT_SECRET`、配置真实 `WECHAT_APP_ID/SECRET`、关闭 `WECHAT_MOCK`、使用环境变量注入数据库凭证。

---

## 8. 常见问题

- **启动报 `ModuleNotFoundError: pdfminer / openpyxl / openai`**：这些是后续阶段的重依赖，已在导入处改为延迟导入，启动后端不依赖它们。需要对应功能时再 `pip install -r requirements.txt` 补齐。
- **迁移报 `Cannot drop index` / 表已存在**：早期残留表结构与当前模型不一致，清空 `studymate` 库重新 `flask db upgrade` 即可（开发环境无业务数据）。
- **`InvalidSubjectError`**：PyJWT 要求 `sub` 为字符串，令牌中已用 `str(user_id)`。
