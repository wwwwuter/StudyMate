# StudyMate · UI 风格规范（Design Spec）

> 风格方向：**森林青绿 (Forest Teal) · 浅色模式**
> 适用：桌面端 Electron + Vue3 应用（Phase 1+ 统一遵循）
> 组件库：Element Plus 2.x（通过 CSS 变量覆盖主题，不改写源码）

---

## 1. 设计理念

- **平静专注**：青绿色调模拟自然/森林，降低长时间学习的视觉疲劳，强调「沉浸」而非「刺激」。
- **清晰可信**：以卡片化布局 + 充足留白建立秩序感，贴合「智能学习助手」的专业定位。
- **AI 可辨识**：AI 相关元素统一使用天蓝（Cyan）作为次强调色，与主青绿区分，但同属冷色系，不冲突。

---

## 2. 色板（Design Tokens）

### 品牌主色 · 青绿 Teal
| Token | 值 | 用途 |
|---|---|---|
| `--brand-900` | `#0B3B36` | 最深，渐变收尾 |
| `--brand-700` | `#0F766E` | **主色 Primary**（按钮、激活、链接） |
| `--brand-600` | `#0D9488` | 主色 hover / 强调 |
| `--brand-500` | `#14B8A6` | 装饰、图标 |
| `--brand-50`  | `#ECFDF5` | 选中/浅底背景 |

### AI 强调色 · 天蓝 Cyan
| Token | 值 | 用途 |
|---|---|---|
| `--ai-600` | `#0284C7` | AI 按钮 hover |
| `--ai-500` | `#0EA5E9` | **AI 元素主色**（气泡、CTA） |
| `--ai-50`  | `#E0F2FE` | AI 浅底 |

### 中性 / 背景
| Token | 值 | 用途 |
|---|---|---|
| `--bg-page` | `#F4F8F6` | 页面背景（极淡绿调） |
| `--bg-card` | `#FFFFFF` | 卡片背景 |
| `--bg-soft` | `#F1F6F4` | 次级浅底 / 分隔线底 |
| `--border`   | `#E3EBE8` | 描边 |

### 文字
| Token | 值 | 用途 |
|---|---|---|
| `--text-strong` | `#16302B` | 标题（深森林墨） |
| `--text` | `#1F2A28` | 正文 |
| `--text-secondary` | `#5B6B66` | 次要 |
| `--text-muted` | `#93A39D` | 占位 / 辅助 |

### 状态色
`--success #10B981` · `--warning #F59E0B` · `--danger #EF4444` · `--info #64748B`

---

## 3. 半径 / 阴影 / 字体

- **圆角**：`--radius-sm 6px` / `--radius 10px`（卡片、按钮）/ `--radius-lg 16px`（横幅、大卡）/ `--radius-pill 999px`
- **阴影**：`--shadow-sm`（卡片静止）/ `--shadow`（悬浮）/ `--shadow-lg`（弹层）
- **字体**：`"Microsoft YaHei", "PingFang SC", "Inter", system-ui, sans-serif`
- **基准字号**：14px，行高 1.6

---

## 4. Element Plus 主题映射

在 `src/theme/index.css` 中覆盖以下变量（已落地）：

```css
--el-color-primary: #0F766E;
--el-color-primary-light-3: #57A099;
--el-color-primary-light-5: #87BAB6;
--el-color-primary-light-7: #B8D6D3;
--el-color-primary-light-8: #CFE3E2;
--el-color-primary-light-9: #E7F1F0;
--el-color-primary-dark-2:  #0C5E58;
--el-border-radius-base: 10px;
--el-border-radius-small: 6px;
--el-font-family: var(--font-sans);
```

> 新增组件一律使用 Element Plus 原生组件 + 上述 token，**不要**写死颜色值；自定义区域使用第 2 节 token。

---

## 5. 布局骨架

```
┌─────────────┬──────────────────────────────┐
│  侧边栏       │  顶栏（标题 / 搜索 / 通知 / 头像） │
│ (青绿渐变)    ├──────────────────────────────┤
│  Logo + 菜单  │                              │
│             │   内容区（router-view）         │
│  AI 状态条    │   · 横幅 / 统计卡 / 图表 / 列表   │
│             │                              │
└─────────────┴──────────────────────────────┘
```

- 侧边栏：青绿渐变背景，白字；菜单激活态为半透明白底（见 `MainLayout.vue`）。
- 顶栏：白底 + 1px 描边；搜索框限宽 420px。
- 内容区：页面背景 `--bg-page`，内边距 24px，纵向可滚动。

---

## 6. 明暗策略

当前仅实现 **浅色**（Phase 0 边界，用户确认）。后续若需深色模式：
- 新增 `[data-theme="dark"]` 作用域，重映射上述 token（背景转深、文字转浅），主色保持青绿不变。
- Element Plus 暗色变量通过 `--el-color-primary` 同级覆盖，无需换包。

---

## 7. 组件用法约定

- 主操作按钮：`type="primary"`（青绿）；破坏性：`type="danger"`。
- AI 专用按钮：使用 `color="#0EA5E9"` 自定义色，不混用 primary。
- 卡片：统一 `shadow="never"` + `border-radius: var(--radius)`，靠 1px 描边而非阴影区分层次。
- 图标：统一 `@element-plus/icons-vue`，避免混用 emoji 作功能图标（装饰性 emoji 除外）。
