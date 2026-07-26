# StudyMate

基于 AI 大模型的智能考研学习助手（Windows 桌面端）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 桌面端 | Electron + Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts |
| 后端 | Python Flask + Flask-SQLAlchemy + Flask-Migrate（RESTful API） |
| 数据库 | MySQL 8.0（ORM: SQLAlchemy） |
| AI 模块 | 预留接口，后续阶段接入 DeepSeek API（**禁止 Ollama**） |

## 目录结构

```
StudyMate
├── desktop/            # 前端桌面应用
│   ├── src/            # Vue 工程源码（api / assets / components / router / stores / views / utils）
│   ├── electron/       # Electron 主进程（main.js / preload.js / package.json）
│   ├── package.json    # 前端依赖与脚本（dev / build / 启动 Electron）
│   └── vite.config.ts
├── backend/            # Flask 后端
│   ├── app/            # 应用工厂、配置、扩展
│   ├── models/         # 数据库模型
│   ├── routes/         # RESTful 路由（蓝图）
│   ├── services/       # 业务逻辑
│   ├── ai/             # AI 模块（预留接口，DeepSeek 后续实现）
│   ├── parser/         # 文件解析（PDF / Excel / JSON）
│   ├── utils/          # 工具（JWT 等）
│   └── run.py          # 启动入口
├── database/sql/       # 数据库初始化 / 种子 SQL
├── requirements/       # Python 依赖（base.txt 核心 / dev.txt 开发）
├── uploads/            # 用户上传文件（运行时生成，不入库）
├── logs/               # 运行日志（不入库）
├── docs/               # 项目文档
├── .env                # 环境变量（不入库，参考 backend/.env.example）
└── README.md
```

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv ../.venv        # 若尚未创建虚拟环境
../.venv/Scripts/pip install -r ../requirements/base.txt
cp ../backend/.env.example ../.env   # 按需修改数据库连接与密钥
python run.py                   # 访问 http://127.0.0.1:5000
```

> 业务功能（用户系统、学习计划、计时、AI 等）依赖 `backend/requirements.txt` 中的完整依赖，
> 将在对应阶段安装。

### 2. 前端（Vue）

```bash
cd desktop
npm install
npm run dev            # Vite 开发服务器 http://localhost:5173
```

### 3. 桌面端（Electron）

```bash
cd desktop
npm run dev            # 同时启动 Vite + Electron（开发模式）
# 或仅启动 Electron 主进程：
cd desktop/electron && npm start
```

### 4. 数据库

使用 MySQL 8.0，初始化脚本位于 `database/sql/init.sql`：

```bash
mysql -uroot -p studymate < database/sql/init.sql
```

## 当前阶段

- **Phase 0：项目初始化（基础架构）** —— 已完成。
- **Phase 1–7：用户系统、学习计划、计时系统、资料库、提醒系统、数据分析与学习报告** —— 已实现。
  - Phase 7 新增「数据分析」分页：ECharts 可视化（时长/完成率/科目/连续打卡/时段）+ DeepSeek/模板双轨 AI 学习报告。
  - 详细后端接口与测试说明见 `backend/README.md` 第 7 节。

## 开发规范

- 模块化组织，避免重复代码。
- 配置通过环境变量读取（python-dotenv），禁止在代码中写死密码 / 密钥。
- 提交前使用 `black` 格式化、`flake8` 检查、`pytest` 跑测试（开发依赖见 `requirements/dev.txt`）。
