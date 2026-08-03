# StudyMate —— AI 大模型驱动的智能学习助手

> 基于 AI 大模型的个人学习管理系统 · 计划解析 / 任务管理 / 专注计时 / 数据闭环

StudyMate 是一款面向学生的 **Windows 桌面端学习管理系统**：上传学习计划（Word / PDF / Excel / JSON / 图片），AI 语义解析后自动排入每日任务，配合计划时间段倒计时、番茄钟等专注计时，记录学习行为，最后由 AI 给出学习分析与调整建议，形成「计划 → 执行 → 记录 → 分析 → 优化」的完整学习闭环。

---

## 1. 项目背景

考研复习周期长（通常 6~12 个月）、科目多、任务交叉，学生普遍面临：

- **计划难坚持**：人工排期容易虎头蛇尾，缺计划后很难回轨
- **任务依赖人工**：Excel / Word 里的学习计划无法直接变成可执行、可提醒的任务
- **数据缺分析**：学了多久、完成率多少、哪个科目长期低效，全靠感觉，没有量化
- **执行缺陪伴**：缺少开始/结束提醒，专注过程没有反馈

因此设计并实现 StudyMate：**利用 AI 大模型理解学习计划并自动安排，用数据驱动执行与优化**，而不是一个普通 Todo 或计时工具。

## 2. 项目简介

StudyMate 基于 **Electron + Vue3 + Flask** 架构开发，桌面端默认 **SQLite 内置数据库、完全离线可用**（同时支持本地 Web 运行与 MySQL 多用户部署）。

系统结合大语言模型能力，实现：

- **学习计划智能解析**（多格式文档 → 结构化任务）
- **每日任务自动规划**（计划版本管理 + 时间冲突检测）
- **专注计时体系**（计划倒计时 / 番茄钟 / 自由计时 / 倒计时）
- **学习数据统计**（今日 / 累计 / 趋势 / 计划执行率）
- **AI 学习辅助**（每日总结、计划偏差检测、调整建议）

## 3. 核心功能

### 3.1 用户系统

- 首次启动初始化账号（setup），注册 / 登录 / 退出登录
- 本地会话令牌鉴权（AuthSession），登录状态全局恢复（刷新 / 重启不掉线）

### 3.2 智能学习计划（AI 解析）

- 支持 **Word(.docx) / PDF / Excel(.xlsx/.xls) / JSON / 图片(OCR) / 文本** 计划上传
- DeepSeek 语义分析（非正则），统一输出结构化 JSON（`plan_name` + 任务：日期/科目/内容/起止时间/优先级）
- 解析结果进入 **草稿预览**：可修改、删除、重新解析，确认后才落库
- **计划版本管理**：同名计划自动递增 v1/v2，旧版本标记 superseded 保留历史
- **时间冲突检测**：新任务与已有任务时间重叠时自动跳过并提示，不覆盖已有数据
- **已执行任务保护**：存在学习记录的任务禁止删除，保留历史（completed/adjusted/cancelled）

### 3.3 AI 学习助手（DeepSeek）

- 基于每日学习情况生成**今日总结、问题发现、可执行建议**
- **计划偏差检测**：近 7 天科目完成率 < 50% 自动预警（如「408 连续三天完成率低 → 建议调整时间」）
- 双轨降级：无 Key / 调用失败时自动回退规则模板，保证可用

### 3.4 学习任务管理

- 每日计划时间轴展示（按开始时间排序）
- 任务状态：pending / running / done / cancelled / expired
- 手动完成 / 取消；计时结束弹窗三选一（完成任务 / 继续学习 / 稍后处理）
- 历史任务查询

### 3.5 专注计时体系（桌面端核心）

四种模式：

| 模式 | 说明 |
|---|---|
| **计划计时** | 绑定 StudyTask，按计划时间段**倒计时**；支持提前开始提示、超时弹窗「继续学习」（额外时长单独统计） |
| **番茄钟** | 25 分钟专注 + 5 分钟休息，只统计专注时长 |
| **自由计时** | 不绑定任务，记录个人学习时间 |
| **倒计时** | 设定目标时长，可绑定任务，归零自动保存 |

**计划驱动时长模型**（AI 分析与统计的基石）：

```
planned_duration   = plan_end − plan_start      # 计划安排时长（目标）
effective_duration = min(end, plan_end) − start # 计划内有效学习（统计口径）
duration           = end − start                # 真实投入（行为分析）
extra_duration     = end − plan_end             # 计划外额外学习（正向行为）
```

### 3.6 学习提醒

- 任务开始前提醒（提前 N 分钟）、任务结束提醒（结束前 5 分钟窗口）
- APScheduler 周期扫描 + Electron 系统通知 / 前端弹窗；时区已按中国时区修正

### 3.7 学习数据分析

- **今日统计**：有效学习时长 / 额外学习 / 任务完成率 / **当前任务（按时间动态选取）** / 模式分布
- **全部统计**：累计学习（有效/实际/额外三口径）/ 学习趋势 / 科目占比 / 连续天数 / **计划执行率（按计划版本）**
- AI 学习建议卡片（含计划偏差区块）

### 3.8 全局状态恢复（刷新 / 重启无缝续学）

- 启动单次 `/api/system/bootstrap` 聚合返回用户 + 计时 + 提醒状态
- 番茄钟阶段 / 倒计时目标由后端权威字段重建，**刷新页面、重启 App 计时不丢**
- 僵尸会话清理：running 超 12h 或超计划结束 24h 自动结束落库

## 4. 系统架构

```
                    ┌──────────────────────┐
                    │  用户（Windows 桌面） │
                    └──────────┬───────────┘
                    ┌──────────▼───────────┐
                    │  Electron 桌面客户端  │
                    │  （内置后端，离线可用）│
                    └──────────┬───────────┘
                    ┌──────────▼───────────┐
                    │  Vue3 + TypeScript    │
                    │  Pinia 全局状态       │
                    └──────────┬───────────┘
                    ┌──────────▼───────────┐
                    │  Flask REST API       │
                    │  (waitress / APScheduler)
                    └──────────┬───────────┘
        ┌──────────────────────┼──────────────────────┐
        │            │                  │              │
   ┌────▼───┐   ┌────▼────┐   ┌────────▼───────┐   ┌───▼──────┐
   │ 用户模块 │   │ 计划模块 │   │ AI 模块        │   │ 数据模块  │
   │ auth/me │   │ 解析/版本│   │ DeepSeek 客户端 │   │ 统计/趋势 │
   └────────┘   │ 冲突检测 │   │ 提示词管理      │   └──────────┘
                └─────────┘   └────────────────┘
        ┌──────────────────────┴──────────────────────┐
        │   SQLite（桌面默认） / MySQL（Web 多用户部署）  │
        └─────────────────────────────────────────────┘
```

**AI 服务**：DeepSeek API（OpenAI 兼容协议直调，轻量无重依赖）；RAG 向量检索（FAISS + 中文向量模型）为 Web 化知识库预留。

## 5. 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue3 · TypeScript · Vite · Pinia · Vue Router · Element Plus · ECharts |
| 桌面壳 | Electron（electron-builder 打包 NSIS 安装包） |
| 后端 | Python · Flask · Flask-SQLAlchemy · waitress · APScheduler |
| 数据库 | SQLite（桌面默认）· MySQL（Web 部署） |
| AI | DeepSeek API（OpenAI 兼容协议） |
| 文档解析 | python-docx · pypdf · pdfminer.six · openpyxl · 图片 Vision OCR |
| 打包 | PyInstaller（后端）· electron-builder（前端 + 安装包） |

## 6. 项目目录

```
StudyMate
├── backend/                     # Flask 后端
│   ├── ai/                      # DeepSeek 客户端、提示词管理（含内置兜底）
│   ├── app/                     # 应用工厂、配置、SQLite schema 迁移
│   ├── models/                  # SQLAlchemy 模型（用户/计划/任务/记录/计时/提醒…）
│   ├── parser/                  # docx / pdf / excel / json 解析
│   ├── prompts/                 # AI 提示词（随打包内嵌）
│   ├── routes/                  # REST 路由（auth/plan/task/stat/ai/reminder/system…）
│   ├── scheduler/               # 僵尸计时清理
│   ├── services/                # 业务服务（plan_manager/reminder/stat/scheduler）
│   ├── utils/                   # 鉴权、时区、科目归一化
│   ├── tests/                   # pytest 单元测试
│   ├── desktop_run.py           # 桌面端后端入口（waitress，动态数据目录）
│   ├── build_backend.py         # PyInstaller 打包脚本
│   └── requirements.txt         # Web 化部署依赖
├── desktop/
│   ├── electron/                # Electron 外壳（main/preload、electron-builder 配置）
│   └── vue/                     # Vue3 前端
│       ├── src/stores/          # Pinia（user / timer / reminder）
│       ├── src/views/           # 页面（上传/任务/计时/统计/设置…）
│       └── src/api/             # API 封装
├── nginx/                       # Web 部署反向代理模板
├── docs/                        # 产品文档
└── README.md
```

## 7. 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Windows 10 / 11（Electron 桌面端） |
| Python | >= 3.10 |
| Node.js | >= 18 |
| 数据库 | **无需安装**（桌面端内置 SQLite）；Web 多用户部署需 MySQL 8.0 |
| AI 服务 | DeepSeek API Key（在「设置」页配置，可选——无 Key 时 AI 解析不可用但其余功能正常） |

## 8. 安装部署

### 8.1 桌面 App（推荐，开箱即用）

直接安装打包产物：`StudyMate-Setup-<版本>.exe`（NSIS 安装包，双击安装）。

数据存储于 `%APPDATA%/StudyMate/backend-data`，完全本地、离线可用。

### 8.2 开发环境运行

```bash
# 1) 后端（venv 中安装依赖后）
cd backend
python desktop_run.py --port 5088 --data-dir "C:/Users/<你>/AppData/Roaming/StudyMate/backend-data"

# 2) 前端（开发态，Vite dev server，/api 自动代理到 5088）
cd desktop/vue
npm install
npm run dev        # http://localhost:5173
```

### 8.3 本地网页版（局域网分享）

```bash
cd desktop/vue
npm run build
npm run preview    # http://localhost:4173，/api 代理到 127.0.0.1:5088，监听局域网
```

同一 Wi-Fi 下手机/其他电脑访问 `http://<本机IP>:4173`（数据仍留在本机）。

### 8.4 打包分发

```bash
# ① 后端 exe（PyInstaller，含 prompts 提示词）
cd backend && python build_backend.py
# ② 前端构建
cd desktop/vue && npm run build
# ③ Electron 安装包（NSIS）
cd desktop/electron && npm run dist
```

### 8.5 Web 多用户部署（进阶）

`nginx/studymate.conf` + `backend/Dockerfile` + `requirements.txt`（MySQL + Alembic 迁移）已提供模板，用于服务器多用户场景。

## 9. 使用流程

```
初始化账号（首次启动）
        │
        ▼
     登录 / 注册
        │
        ▼
  上传学习计划（Word/PDF/Excel/JSON/图片）
        │
        ▼
  AI 语义解析 → 统一 JSON（草稿）
        │
        ▼
  预览确认（修改 / 删除 / 重新解析）
        │
        ▼
  生成计划版本（v1/v2，冲突自动跳过）
        │
        ▼
  今日任务 → 计划计时（倒计时）/ 番茄钟 / 自由 / 倒计时
        │
        ▼
  到点提醒（开始 + 结束）→ 计时结束判定（完成/继续/稍后）
        │
        ▼
  学习数据统计（今日/全部 + 计划执行率）
        │
        ▼
  AI 学习建议（总结 + 计划偏差 + 调整建议）
```

## 10. 系统展示

> 截图目录：`docs/images/`（`home.png`、`upload.png`、`timer.png`、`stats.png`、`ai.png`），
> 可运行网页版后自行截取补充。

## 11. 核心技术实现

- **多格式计划解析管道**：类型识别 → 文本提取（docx/pdf/excel/json/vision OCR）→ AI 语义结构化 → 统一 JSON → 草稿确认，全程非正则
- **提示词双轨保障**：提示词文件（`prompts/`）随后端打包内嵌，代码内同步内置兜底常量，避免打包环境提示词丢失导致解析退化
- **计划驱动计时**：Task 模式从 `StudyTask` 计算计划时间段（本地→UTC），前端按后端权威时间戳重建倒计时；超额学习（`extra_duration`）单独统计
- **全局状态水合**：`/api/system/bootstrap` 单次聚合 + Pinia store 启动水合；番茄段/倒计时目标持久化到 `TimerSession`，刷新/重启零丢失
- **僵尸会话清理**：APScheduler 周期 + 启动时清理超时 running 会话，统计口径与手动结束一致

## 12. 项目创新点

### 1. AI 驱动的学习计划语义解析
DeepSeek 大模型将任意格式的学习计划（Word/PDF/Excel/JSON/图片）解析为结构化任务 JSON，自动推断日期、匹配作息时间段，替代人工排期——**不是正则匹配，而是语义理解**。

### 2. 计划驱动型计时体系（三时长模型）
区分「计划安排（planned）」「计划内有效（effective，统计口径）」「真实投入（actual，行为分析）」「额外学习（extra，正向行为）」四类时长，为 AI 判断计划合理性、识别拖延/主动加练提供数据基础。

### 3. 计划版本管理与冲突保护
同名计划版本递增（v1/v2，旧版 superseded 保留）；新计划与已有任务时间重叠时自动跳过并提示；存在学习记录的任务禁止删除——**更新计划不丢历史**。

### 4. 全局状态无缝恢复
单接口启动水合 + 后端权威字段重建计时状态，刷新页面、重启桌面 App 后「昨天关掉时的学习状态」自动恢复，番茄钟进行到第几轮、倒计时还剩多久都不丢。

### 5. 学习数据闭环
「计划制定 → 任务执行 → 行为记录 → AI 分析（完成率/偏差/时长）→ 计划优化建议」完整闭环，AI 建议不仅看「学了多久」，更看「计划完成率 + 额外投入 + 执行习惯」。

### 6. 桌面端开箱即用
Electron + 内置后端 + SQLite 单文件交付，**完全离线**；同时保留 Web/MySQL 多用户部署路径，单机到云无缝扩展。

## 13. 后续规划（Roadmap）

- [ ] **RAG 知识库**：接入课本/笔记检索，让 AI 建议基于个人资料（FAISS + 中文向量模型已预留）
- [ ] **智能 Agent 任务规划**：基于计划偏差自动调整任务量与时间分配
- [ ] **个人学习知识图谱**：科目 → 知识点 → 掌握度的结构化建模
- [ ] **学习效果预测**：基于历史执行数据预测备考进度
- [ ] **Web 多用户正式部署**：MySQL + nginx/HTTPS + 开放注册
- [ ] **多平台客户端**（macOS / Linux）

## 14. Author

本项目为个人学习项目，用于将 **AI 大模型 + 桌面应用工程** 落地到真实学习场景。

研究方向（Research Direction）：

- Artificial Intelligence
- Intelligent Learning Systems
- Data-Driven Study Analytics
