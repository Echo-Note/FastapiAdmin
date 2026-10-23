# 医药市场管理服务平台 —— 两端统一设计系统（MASTER）

> **定位**：市场域（任务协作）两端共用的设计令牌与组件语义唯一真值源。
> **覆盖端**：`frontend/web`（运营平台，Vue3 + Element Plus + Tailwind v4）与 `frontend/app`（C 端小程序，uni-app + wot-design-uni + UnoCSS）。
> **使用规则**：构建某个页面前，先查 `design-system/default/pages/[page].md`，若存在则其规则覆盖本文；否则严格遵循本文。

---

## 0. 与 ui-ux-pro-max 生成结果的关系（override 说明）

`--design-system` 检索命中了「Flat Design / teal 主色」组合（`#0D9488`）。该结果为**通用「医疗」联想色**，与本项目现有品牌与权威设计文档冲突，故在此**显式覆盖**：

- 本项目已有品牌主色为**蓝**（`#4080FF`），运营端/小程序端均已大量落地，且《04-前端交互与视觉设计文档》§3.1 明确要求「保留现有蓝色主基调（专业、可信，符合医药服务气质）」。
- 采纳检索命中的 **Flat Design 风格方向**（去阴影化、克制动效、语义化图标、150–300ms 过渡），但不采纳其 teal 色板。

> 覆盖依据：`frontend-design` 原则——不为「医疗」套用模板化 teal 默认色；围绕「医药市场服务 / 任务协作」做有辨识度的选择，一次只在一处用重笔（此处「重笔」= 品牌蓝 + 状态语义色，而非装饰渐变）。

---

## 1. 语义色（两端唯一真值）

> **落地约束（上游不修改）**：两端主题底层由各自组件库驱动——Web 的 EP 语义变量（`--el-color-*`）、App 的 wot 语义令牌（`--wot-*`）。本项目的统一令牌通过「语义类型 + 文案」单一映射落地，不改上游主题文件。下方 hex 为**参考真值**，两端通过语义类型（`primary/success/warning/danger/info`）对齐；若上游默认色板与参考 hex 不一致（已知：EP 默认 success 为 teal `#13deb9`），以本表语义为准，待上游主题统一决策后同步（见 §7 已知偏差）。

| 令牌 | 语义 | 参考 Hex | 用途 |
|---|---|---|---|
| `primary` | 主色（品牌蓝） | `#4080FF` | 主按钮、进行中/已发布/已接收/已完成 |
| `success` | 成功 | `#22C55E` | 通过/已结算/已关闭/已审核/已发放 |
| `warning` | 警示 | `#F59E0B` | 待审核/待处理/待发放/归集中 |
| `danger` | 危险 | `#EF4444` | 驳回/删除/超限 |
| `info` | 中性 | `#64748B` | 草稿/归档/停用/待接收 |

### 1.1 状态色统一规则（覆盖「同义不同色」）

| 语义 | 对应状态（两端一致） |
|---|---|
| `info` 灰 | 草稿 / 已归档 / 已关闭 / 停用 / 待接收 |
| `warning` 橙 | 待审核 / 待处理 / 进行中 / 归集中 / 待发放 / 待结算 |
| `success` 绿 | 通过 / 已结算 / 已关闭 / 已审核 / 已入报告 / 已支付 / 已发放 |
| `danger` 红 | 驳回 / 删除 / 超限 |
| `primary` 蓝 | 已发布 / 已接收 / 已完成 / 已生成 / 已确认 |

> 两端 `constants`（Web：`api/module_market/constants.ts`；App：`constants/market.constant.ts`）共用同一份 `{ 状态值 → { text, type } }` 映射，type 取值严格限定为上述 5 类，**不再各自写一份**。

---

## 2. 状态徽标统一映射（唯一真值）

以下为五类状态机 + 发放/来源/分类的**统一文案与语义色**，两端完全一致：

| 状态机 | 值 | 文案 | 色型 |
|---|---|---|---|
| 任务 TaskStatus | DRAFT | 草稿 | info |
| | PUBLISHED | 已发布 | primary |
| | IN_PROGRESS | 进行中 | warning |
| | COMPLETED | 已完成 | primary |
| | SETTLING | 归集中 | warning |
| | SETTLED | 已结算 | success |
| | ARCHIVED | 已归档 | info |
| 项目 ProjectStatus | DRAFT / IN_PROGRESS / COMPLETED / CLOSED | 草稿 / 进行中 / 已完成 / 已关闭 | info / warning / success / info |
| 分派 AssignmentStatus | PENDING | 待接收 | info |
| | ACCEPTED | 已接收 | primary |
| | SUBMITTING | 进行中 | warning |
| | SUBMITTED | 已提交 | warning |
| | REVIEWED | 已审核 | success |
| | SETTLED | 已结算 | success |
| 成果 SubmissionStatus | DRAFT | 草稿 | info |
| | PENDING | 待审核 | warning |
| | APPROVED | 已通过 | success |
| | REJECTED | 已驳回 | danger |
| 结算 SettlementStatus | PENDING / CALCULATED / CONFIRMED / REPORTED / PAID | 待结算 / 已计算 / 已确认 / 已入报告 / 已支付 | info / warning / primary / success / success |
| 报告 ReportStatus | DRAFT / GENERATED / SUBMITTED | 草稿 / 已生成 / 已提交 | info / primary / success |
| 津贴 AllowanceStatus | PENDING / PAID | 待发放 / 已发放 | warning / success |
| 任务分类 TaskKind | periodic / quota | 周期性 / 定额 | info / warning |
| 分配方式 AssignMode | direct / open | 定向分派 / 公开大厅 | info / success |
| 实例来源 AssignmentSource | assigned / claimed | 运营分派 / 大厅接单 | info / primary |

---

## 3. 中性色阶、字体、间距、圆角、阴影

### 3.1 中性色阶（Web 沿用 `--fa-gray-*`，App 沿用 wot `text-main/auxiliary/muted`）

| 层级 | Web 令牌 | App 语义 | 用途 |
|---|---|---|---|
| 主文本 | `--fa-gray-900` | `wot-text-text-main` | 标题/关键数值 |
| 次文本 | `--fa-gray-600` | `wot-text-text-auxiliary` | 正文/说明 |
| 弱文本 | `--fa-gray-500` | `wot-text-text-secondary` | 辅助/时间/占位 |
| 分割线 | `--default-border` | `--wot-border` | 卡片描边/表头线 |
| 卡片底 | `--default-box-color` | `--wot-bg-card` | 卡片/弹层 |
| 页面底 | `--default-bg-color` | `--drop-bg` | 页面背景 |

### 3.2 字体（两套载体，同一品牌）

| 端 | 正文 | 数字/金额 |
|---|---|---|
| Web 桌面 | 系统栈（PingFang SC / Microsoft YaHei） | 金额用 `font-variant-numeric: tabular-nums`，右对齐、千分位 |
| App 移动 | 系统默认 | 金额统一 `¥` 前缀 + 两位小数 |

字号 5 档（两端语义对齐）：`xs 11px`（角标）→ `sm 12px`（表内/时间）→ `md 14px`（正文）→ `lg 16px`（卡片标题）→ `xl 18px`（页面标题/金额）。

### 3.3 间距 / 圆角 / 阴影

- **间距**：4px 刻度（4/8/12/16/24/32），禁写任意 px。
- **圆角**：卡片 `12px`、按钮/输入 `6px`、弹层 `8px`；跟随各端圆角令牌（Web `--custom-radius`，App wot 圆角变量）。
- **阴影**：克制动效下阴影仅用于「分层」（卡片 1 层、弹层 2 层），不用于装饰。参考：卡片 `0 1px 2px rgba(0,0,0,.05)`，弹层 `0 10px 15px rgba(0,0,0,.1)`。

### 3.4 图标规范

- 统一 **SVG 图标集**（Web：项目内 `assets/*.svg`；App：wot `wd-icon` 图标），**禁止 emoji 当图标**。
- 图标语义一致：接单/接收/提交/审核/结算/报告各自两端用同一图标语义。

---

## 4. 组件语义映射（同一语义，两套载体）

| 语义 | Web（Element Plus + Fa 组件） | App（wot-ui） | 约定 |
|---|---|---|---|
| 列表 | `FaTable` | 卡片列表 | 骨架屏 → 加载态 → 空/错误态 → 数据 |
| 状态标签 | `FaStatusTag`（type=统一语义） | `wd-tag`（type=统一语义） | **共用同一份 status→色/文案映射**（§2） |
| 危险操作确认 | `useConfirm`（type:warning） | `globalDialog.confirm` | 标题 + 影响描述 + 确认/取消 |
| 表单 | `FaForm` + rules | `wd-form` | 字段级即时校验 + 提交中禁用防重复 |
| 空态 | `ElEmpty`（CTA 化） | `wd-empty`（CTA 化） | 区分「空/筛选无结果/失败」三态 |
| 错误态 | 错误块 + 重试 | `ErrorState` + 重试 | 失败必带重试，禁止静默 catch |
| 金额 | 右对齐 + 千分位 | `¥` + 两位小数 | 金额格式统一 |

---

## 5. 交互反馈契约（两端一致）

| 场景 | 反馈 |
|---|---|
| 列表加载中 | 骨架屏（首屏）/ 行内 loading（增量） |
| 列表加载失败 | 错误态块 + 「重试」（禁止把失败当空态） |
| 动作成功 | toast「已<动作>」（"已发布/已接单/已提交/已通过/已驳回"）+ 状态即时刷新 |
| 动作失败 | toast「<原因>，请重试」，保留已填内容 |
| 危险操作 | 二次确认，文案写清影响 |
| 表单校验失败 | 字段旁红字 + 定位第一个错误字段 |

- **动作词一致**：按钮「发布」→ toast「已发布」；按钮「接单」→ toast「已接单」。
- **触控（App）**：交互目标 ≥ 44×44，相邻间距 ≥ 8dp，安全区 `safe-area-bottom`。
- **键鼠（Web）**：键盘焦点可见（`:focus-visible`）、`:hover` 反馈、`prefers-reduced-motion` 尊重。
- **反馈节奏**：转场 150–300ms，toast 时长一致，两端不出现一端极花哨一端极简陋。

---

## 6. 两端落地位置

| 端 | 令牌落地文件 | 状态映射落地文件 |
|---|---|---|
| Web | 沿用上游 `styles/core/_fa-tokens.scss` + `tailwind.css @theme`（**不修改**） | `src/api/module_market/constants.ts`（单一来源，已是统一映射） |
| App | 沿用上游 `styles/theme.scss` + `uno.config.ts` presetWot（**不修改**） | `src/constants/market.constant.ts`（**新增**，与 Web 对齐） |

---

## 7. 已知偏差（上游约束，待统一主题决策）

1. **EP 默认 success 为 teal `#13deb9`**，参考真值 success 为绿 `#22C55E`。由于「不修改上游主题文件」约束，Web 端「通过/已结算」暂按 EP 语义色（teal）渲染，App 端按 wot（绿）渲染。二者**语义类型一致**（同为 `success`），仅 hex 不同。待上游主题统一决策后，在 `_fa-tokens.scss` 一处改 `$fa-success` 即可两端同步。
2. App `theme.json` 的 `tabSelectedColor: #0165FF` 与主色 `#4080FF` 接近但不等，属上游 tabBar 配置，未纳入本次改动。
