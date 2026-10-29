# 开发过程记录（DEVELOPMENT LOG）

> **本文档是后续开发的强制入口。**
>
> - **开发前**：必须先读完本文档（尤其「硬口径」与「踩坑记录」两节），再动手。
> - **开发后**：必须在本文件「开发记录」一节**追加一条新记录，或更新既有相关记录**；若产生新的硬口径或踩坑，同步回填「硬口径」与「踩坑记录」两节。

---

## 一、本文档定位

| 文件 | 受众 | 记录内容 |
|---|---|---|
| `CHANGELOG.md` | 用户 / 版本发布 | 面向外部的版本变更说明 |
| **`DEVELOPMENT-LOG.md`（本文件）** | **开发者** | **为什么改、改了什么、踩了什么坑、怎么解决** |

权威设计文档：`docs/01-PRD-产品需求文档.md`、`docs/02-系统设计文档.md`、`docs/03-流程与状态流转.md`（2026-10-22 重新产出，旧设计文档已作废，勿沿用旧口径）。

---

## 二、硬口径（开发前必读，长期有效）

这些是跨文件拼出的硬约束，违反会导致隐蔽 bug 或测试全线崩坏：

1. **数据库 = PostgreSQL 18**（一期即 PG，不是基座默认的 MySQL）。
   - JSON 列用 `sqlalchemy.dialects.postgresql.JSONB`，不是通用 `JSON`。
   - 唯一键冲突码是 `23505`（不是 MySQL 的 `1062`）。
   - 主键 `BigInteger`。

2. **迁移走「双轨制」，勿手写 alembic migration**。
   - 空库：`create_all` 建表 + `stamp head`；改 model 后测试直接通过，无需 migration。
   - 存量库升级：dev 启动时自动 `autogenerate` 增量迁移，开发者审查后提交。
   - 手写 migration 会与 autogen 产物形成 multiple heads，导致 `init_db` 抛 `CommandError: Multiple heads`。

3. **git 合并一律 `--no-ff`**，禁止 fast-forward，保留合并提交节点便于回溯。

4. **动态表单结构（`form_schema`）由后端 Pydantic 模型权威定义**（如 `FormSchemaField`），前端 TS 类型只对齐、不做定义源；字段 `type` 要覆盖完整类型（含 `image` 图片上传 / `file` 文件附件）。

5. **代码真实落点**：`backend/app/modules/<域>/<模块>/`，每个模块遵循 `controller / service / crud / model / schema` 五件套，统一响应结构。抽象目录（如 `app/platform`）是设计文档的落点示意，不是待建目录。

---

## 三、开发记录

### 2026-10-23 — 基于重庆任务成果素材与省平台模板的深度设计对齐（仅文档）

#### 1. 原因

分析 `docs/materials/重庆任务成果素材`（30 个成果 xlsx + 9 份分析报告 pptx）与 `docs/materials/重庆-省平台项目模版`（10 个官方空白模板），对照现有三份设计文档与 `market` 域代码。发现现有设计只覆盖了「对内任务 → 成果 → 对内结算」半边，对外服务项目结算、分析报告、采集表单结构存在结构性缺口。

#### 2. 分析结论（关键发现）

1. **素材是完整真实案例**：复星万邦（医药公司）委托「聚苯乙烯磺酸钙散」市场服务，平台分派给熊丽/熊志鹏执行，产出三类交付物——对内任务成果、对外服务项目结算单（37 项，合计 57400）、分析报告（9 份 pptx，每服务项目一份）。
2. **模板 vs 计价项是两层**：9 类采集模板（form_schema 宿主）→ 44 个计价项（结算单行，任务号 1–44）。现有 `market_task_type` 把两层混为一层，form_schema 挂在每个计价项上（44 套，重复且丢失「多行子表」语义）。
3. **采集表单 ≠ 计价项**：如「等级医院管理」一个表单含配送协调/销售对账/库存盘点三个多行子表，对应 5/6/7 三个计价项。
4. **对外服务项目结算单无模型**：37 服务项目（两级，含对内没有的「调研报告服务」「专项调研服务」）与对内 44 任务价目独立、金额不挂钩。
5. **form_schema 缺 section/table 两种结构**：真实采集表是「分节 + 键值对 + 多行子表 + 图片/附件」混合体。
6. **采集对象不全是机构**：访谈问卷对象是医务人员/店员/患者（个人），`institution_id` 无法覆盖。
7. **执行要求需拆解**：required(必选) + min_qty(最低数量「1家起」) + exec_standard(达成标准) + dedup_rule(去重「单月单项目一次」) + max_per_period(上限「每月不超过20次」)。
8. **执行主体分两类**：结算单分「市场管理人员 / 非市场管理人员」两个 Sheet（任务 35–44 两类主体都能做，1–34 仅市场管理人员）。

#### 3. 修改内容（仅文档，不改代码）

- `docs/02-系统设计文档.md`：新增 `market_template`（采集模板）、`market_service_item`（对外价目）、`market_service_item_task`（映射）；`market_task_type` 移除 form_schema、改挂 `template_id`、新增 `task_no`/`min_qty`/`max_per_period`/`dedup_rule`；`market_submission` 新增 `subject_type`/`subject_name`、`institution_id` 改可空；`market_report` 改按服务项目/任务类型粒度；新增 §3.3 form_schema 结构规范（section/table）；更新 ER 图与模块目录。
- `docs/01-PRD-产品需求文档.md`：§5.2 任务类型清单改为「9 采集模板 + 44 计价项」两层结构，补充对外 37 服务项目说明。

#### 4. 待办（后续落地代码时）

- seed 拆两层：新增 `market_template` 种子（9 条，承载 form_schema）+ `market_task_type` 引用 `template_id`；新增 `market_service_item` 种子（37 条）+ `market_service_item_task` 映射。
- form_schema 升级：`FormSchemaField` 增 `section` 与 `type: table`（含 columns），并回填 44 计价项的表单字段（当前已扁平化，需补多行子表语义）。

---

### 2026-10-23 — 市场模块按设计文档完成改造（发放 / 项目归集 / 接单限量）

**提交**：`4d7d91b4 feat: 市场模块按设计文档完成改造（发放/项目/接单限量 + 测试 + 前端）`

#### 1. 原因

2026-10-22 用户推倒旧设计，基于 `docs/materials/` 原始素材重新产出三份设计文档（医药市场管理服务平台）。此前市场模块的初步实现与设计文档语义不一致，需要对齐改造，具体偏差包括：

- 早期用 `quota`（额度）表达「每月发放上限」，而设计文档拆分为 `payout_config`（每月发放额度）+ `allowance`（个人津贴）两个独立概念。
- 设计文档新增「任务多对多归集到项目」的 `project` 概念，初步实现缺失。
- 任务分类 `task_kind`（`periodic` 周期性 / `quota` 定额）未落地，定额任务「限定时间范围」的约束缺失。
- 「接单限量」语义不明确：设计文档要求**接单即占名额（先到先得）**，而非提交成果才占名额。

#### 2. 修改内容

**后端（`backend/app/modules/market/`）**

- 删除 `quota` 模块，新增 `payout` 模块（发放额度 + 津贴），补齐 `controller/crud/model/schema/service`。
- 新增 `project` 模块：任务多对多归集；`TaskOutSchema` 补 `project_ids`，`ProjectUpdateSchema` 补 `code`。
- `task` 模型新增 `task_kind`（`periodic`/`quota`）；定额任务创建时强制校验 `exec_time_start/end` 限定时间范围。
- 接单限量语义修正：`claim`（大厅接单）对定额任务**接单即占名额**，用 Redis 原子计数防超卖；`assign_limit` 语义同步修正。
- 移除 `assignment` 对 `company` 的预加载，改为 `task.project_links`（公司概念从分派链路剥离）。
- 菜单 seed 同步（`backend/sql/sys_menu.json`）。

**测试**

- 重写 `test_market_task` / `test_market_flow`，新增 project 更新用例；共 **158 个测试通过**。

**前端**

- `frontend/web` 与 `frontend/app` 的 payout / project 页面与字段对齐（`my-earnings` 等）。

**依赖**

- 新增 `mypy`（`backend/pyproject.toml`）。

#### 3. 遇到的问题与处理

1. **异步环境懒加载 `MissingGreenlet`**
   - 现象：`AssignmentOutSchema` 序列化 `TaskOutSchema`（含 `task_type` 等嵌套审计关系）时，`detail()/page()/accept()` 在 async 下触发懒加载报 `MissingGreenlet`。
   - 处理：统一维护 `_ASSIGNMENT_PRELOAD` 预加载清单，完整加载各层审计关系（`task.created_by/updated_by`、`task.task_type.*` 等）；`create()` 落库后重新 `detail()` 重载，而非直接 `model_validate` 落库对象。

2. **定额任务接单「防超卖」**
   - 现象：公开大厅定额任务「先到先得」，若用「先查数量、再插入」会存在竞态，超卖。
   - 处理：`claim` 用 Redis `incr_with_limit` 原子计数占名额；返回负值即「名额已满」拒绝接单；落库失败时 `decr` 回滚计数，保证计数与 DB 一致。同一用户同一任务幂等防重（先查已存在即拒绝）。

3. **手写 migration 导致 multiple heads（历史踩坑，详见「踩坑记录」）**
   - 本轮改 model 字段时不再手写 migration，交由双轨制处理，避免重蹈 2026-10-22 的 `Multiple heads` 全线测试 ERROR。

---

### 2026-10-23 — 合并上游 master 到三个本地分支（--no-ff）

**提交**：`fa6cd8ac`（master）、`18b7db53`（feature/xuanhu）、`d28ffe53`（refactor/xuanhu-v1.1）

#### 1. 原因

同步上游 FastapiAdmin master 最新改动（`upstream/master` 从 `60d5519b` 推进到 `f9263b27`，共 17 个提交），把 FastHub 能力、SSH 运维、SQL 控制台、跨方言 JSONType 等纳入本地三个分支。

#### 2. 修改内容

- 三个分支各用 `--no-ff` 合并 `upstream/master`，均保留合并提交（parent 数 = 2）。
- 引入上游新模块：`dbconsole`（SQL 控制台）、`ops/ssh`（SSH 运维）、`monitor/cache/browser`（Redis 键浏览）、`utils/lazy_sdk`（SDK 懒加载）等。

#### 3. 遇到的问题与处理

1. **`routers.py` 路由注册冲突**（feature/xuanhu 与 refactor/xuanhu-v1.1 均出现）
   - 现象：本地新增 `/market` 域，上游新增 `/dbconsole`、`/ops` 域，三者在 `DOMAIN_CONTROLLERS` 同一位置冲突。
   - 处理：三者**都保留**，合并为 `"/market" + "/dbconsole" + "/ops"` 三个域并存（market 域内容在 feature 分支为 `QuotaRouter`，在 refactor 分支为 `ProjectRouter/PayoutRouter`）。
2. **`base_model.py` 注释冲突**
   - 现象：`JSONType = JSONB().with_variant(JSON(), "sqlite", "mysql")` 定义两边一致，仅注释不同（上游追加「统一使用 JSONType 而非硬编码 JSONB」）。
   - 处理：合并两端注释，保留完整说明。

---

### 2026-10-23 — 修复后端启动失败（过时迁移文件导致 create_table 撞表）

#### 1. 原因

后端启动报 `asyncpg.exceptions.DuplicateTableError: relation "market_company" already exists`，失败点在 `f3ff2ec1f595` 迁移的 `op.create_table('market_company')`。

排查发现：`versions/` 目录残留 3 个「市场模块改造过程中的中间态」迁移文件（`f3ff2ec1f595`/`b4d8b815d8a8`/`eac2426693e1`，此前被误提交），与当前 model 严重脱节——`f3ff2ec1f595` 会创建已删除的 `market_quota_*` 三张表，`eac2426693e1` 又缺最新的 `market_payout_config`/`market_project`/`market_project_task`。而数据库 55 张表早已是 `create_all` 按最新 model 自举的结果，`alembic_version` 表为空。启动走「存量库」分支 `upgrade head`，从根迁移重建 `market_company`，撞上已存在的表。

#### 2. 修改内容

- 删除 3 个过时迁移文件，恢复「versions/ 仅保留 `__init__.py`」的纯净态（符合「本仓库不提交迁移历史」口径）。
- 启动后 dev autogen 自动补齐上游合并引入的 3 张新表（`dbconsole_connection`/`ops_ssh_host`/`ops_ssh_snippet`），数据库 55→58 张表。
- 清理自动迁移临时产物与 `alembic_version` 残留记录，库回到「create_all 自举后的纯净态」（58 张表 = 最新 model，`alembic_version` 空）。

#### 3. 遇到的问题与处理

1. **过时迁移文件与自举库脱节导致 DuplicateTableError**
   - 现象：库已是最新（create_all 自举），但 versions/ 残留过时迁移，upgrade 从根迁移重建已存在表报错。
   - 处理：删除过时迁移文件；已实测「空 versions/ 下 `upgrade head` 为 no-op（退出码 0）」，且 dev autogen 会按 model vs 库差异自动补齐缺失表。

---

### 2026-10-23 — 市场域两端前端体验统一重构（任务 9）

#### 1. 原因

任务 1–8 市场域代码落地后，两端（运营平台 `frontend/web` + 小程序 `frontend/app`）视觉规范、组件、交互反馈、页面跳转各自为政，且存在路径断层（小程序缺任务详情页、`my-earnings` 标题语义混乱、两端状态色/文案不一致、管理端零跨页导航）。需做一次「以任务流为主线的两端一致性重构」。本任务只改前端体验与交互，不引入新后端接口。

#### 2. 修改内容

**新增文件**
- `design-system/default/MASTER.md`：两端统一设计令牌（语义色 + 状态色统一规则 + 组件语义 + 交互反馈契约）。显式覆盖了 `ui-ux-pro-max` 生成的 teal 主色（`#0D9488`），保留品牌蓝 `#4080FF`。
- `frontend/app/src/constants/market.constant.ts`：C 端状态/文案/语义色唯一真值源（与 Web `api/module_market/constants.ts` 同文案同语义色）。
- `frontend/app/src/subPages/module_market/task-detail/index.vue`：补齐任务详情页（接单/接收/去提交三动作收敛于此）。
- `docs/05-前端体验重构落地说明.md`：页面结构说明 + 两端流程图 + 缺接口清单。

**修改文件（均属市场域项目新增部分，未改上游）**
- `frontend/app/src/constants/index.ts`：导出 market.constant。
- `frontend/app/src/api/module_market/index.ts`：`TaskTypeItem` 接口补 `service_type/service_item/service_task/exec_standard/default_kind` 等字段。
- `frontend/app/src/locales/langs/{zh,en}.json`：market 段补词条 + `common.retry`。
- `frontend/app/src/pages.json`：新增 task-detail 路由；`my-earnings` 标题「我的额度」→「我的收益」。
- `frontend/app/src/subPages/module_market/{task-hall,my-task,submission-form,my-earnings}/index.vue`：统一状态映射、卡片跳详情、修 my-task「进行中」Tab 映射（ACCEPTED → SUBMITTING）、提交回跳我的任务。
- `frontend/web/src/views/module_market/task/index.vue`：任务页升级为流程枢纽（「分派」「结算单」跨页跳转 + 流程提示条）。
- `frontend/web/src/views/module_market/{assignment,settlement}/index.vue`：读取 `route.query.task_id` 预填筛选。

#### 3. 遇到的问题与处理

1. **用户硬约束「只改项目新增部分，不改上游」**
   - 现象：任务书原本要求「token 落到 `_fa-tokens.scss` + `theme.scss`」，但这两个是上游主题文件，改它们会影响整个管理端/小程序全局外观。
   - 处理：令牌落地改为**语义类型对齐**——两端各维护一份 `{ 状态值 → { text, type } }` 映射（type 限定 primary/success/warning/danger/info），不改上游主题 hex；MASTER.md 里把「EP 默认 success 为 teal `#13deb9` vs 参考绿 `#22C55E`」记为已知偏差，留待上游主题统一决策。状态徽标「待审核=橙/通过=绿/驳回=红」的语义两端一致。

2. **缺单详情接口**
   - 现象：小程序端无 `GET /market/mini/tasks/{id}`、`GET /market/mini/assignments/{id}` 单详情接口，任务详情页与提交页无法按 id 现取模板。
   - 处理：按任务书要求「不造接口」，降级为从 `getTaskHall`/`getMyAssignments` 列表按 id 查找；`submission-form` 改为 `assignment_id` 现取 form_schema（消除 URL 透传，规避超长与模板陈旧）。已把 5 项缺接口列入 `docs/05` §6 清单（含 `SubmissionQueryParam` 缺 `task_id` 过滤、结算单缺 `company_id` 等）。

3. **`useRouter` 无 `redirectTo` 方法**
   - 现象：提交成果后想「回跳我的任务」，`router.redirectTo` 报「Router 上不存在 redirectTo」。
   - 处理：改用 `router.replace({ name: 'market-my-task' })`（`@wot-ui/router` 提供 vue-router 兼容的 `replace`）。

4. **ts-plugin 对已改 `.ts` 类型文件的缓存**
   - 现象：扩展 `api/module_market/index.ts` 的 `TaskTypeItem` 后，`read_lints` 仍报 task-detail 用到的 `exec_standard/service_type` 等「不存在」，类型显示为旧的内联类型。
   - 处理：已核对文件实际内容正确（唯一 `TaskItem/TaskTypeItem` 定义在 `api/module_market/index.ts`，字段齐全）；属语言服务缓存未失效，重启 TS 服务/IDE 后消除，非代码问题。

---

### 2026-10-23 — 修复前端 TypeScript 类型检查（ts:check）3 处错误

#### 1. 原因

运行 `pnpm ts:check`（`vue-tsc --noEmit --skipLibCheck`）发现 3 处类型错误，阻断类型校验通过。

#### 2. 修改内容

- `frontend/web/src/components/forms/form-schema-editor/index.vue`：`saveField` 中 `editing.value.name` 类型为 `string | null | undefined`（对齐后端 `FormSchemaField.name?: string | null`），直接 `.trim()` 触发 TS18049，改为 `editing.value.name?.trim() ?? ""`。
- `frontend/web/src/views/module_market/task-type/index.vue`：`createApi`/`updateApi` 用 `{ ...form, template: undefined }` 向 `TaskTypeForm` 传参，但 `template` 不在 `TaskTypeForm`（仅存在于响应类型 `TaskTypeTable` 与本地表单类型 `TaskTypeLocalForm`）中，触发 TS2353 多余属性检查。改用解构剥离：`const { template: _template, ...payload } = form; void _template;`（沿用代码库既有 `_ignored` + `void` 约定消费被解构变量），再以 `payload` 拼提交体。

#### 3. 遇到的问题与处理

1. **`TaskTypeForm` 与 `TaskTypeLocalForm` 结构不对称**
   - 现象：`template` 字段只在「详情返回」（`TaskTypeTable.template`）和「本地表单」（`TaskTypeLocalForm.template`）中存在，提交体 `TaskTypeForm` 无此字段；详情/编辑复用同一本地表单，导致提交时需显式剥离。
   - 处理：用「解构 + rest」剥离 `template`，而非在对象字面量里写 `template: undefined`（后者会触发 TS2353）。多余属性检查只作用于对象字面量显式写的属性、不作用于 rest 展开，故 `...payload`（含 `id` 等非提交字段）不会报错。

---

### 2026-10-23 — 市场域任务/分派/成果提交服务补齐业务逻辑缺口

#### 1. 原因

审阅 `market` 域任务/分派/成果提交四个 Service（`task/service.py`、`assignment/service.py`、`submission/service.py`）后发现若干业务逻辑缺口：

- `SubmissionService.update()` 驳回重提（REJECTED → PENDING）未重新执行表单必填校验，可绕过校验直接提交不完整表单；且未驱动分派状态回流。
- `SubmissionService.review()` 审核通过/驳回后未驱动分派状态联动，`assignment.status` 一直停在 `SUBMITTED`。
- `AssignmentService.accept()`（定向分派接收）缺少与 `claim()` 一致的「限定时间范围」校验。
- `TaskService.complete()` 定额任务完成后未清理 Redis 接单计数，残留内存。

#### 2. 修改内容

- `submission/service.py`
  - `update()`：驳回重提分支先加载 `assignment`（含 `task.task_type.template`），按最终生效的表单数据（`new_data.form_data` 缺省回退 `submission.form_data`）重新执行 `_validate_form`；重提成功后把 `assignment.status` 回写为 `SUBMITTED`。
  - `review()`：审核后把 `assignment.status` 回写为 `SUBMITTING`（回到进行中）。
- `assignment/service.py`：`accept()` 新增 `exec_time_end` 过期校验（与 `claim()` 一致）。
- `task/service.py` + `task/controller.py`：`complete()` 新增 `redis` 参数，定额任务完成后 `RedisCURD.delete` 清理 `MARKET_TASK_CLAIM` 计数键。

#### 3. 遇到的问题与处理

1. **`review(approve)` 驱动到 `REVIEWED` 会破坏「定额任务可重复提交」**
   - 现象：首次实现时把审核通过的分派置为 `REVIEWED`，导致 `test_payout_cap_and_allowance` 里同一 assignment 第二份成果提交失败——`create()` 的允许状态集合 `{ACCEPTED, SUBMITTING, SUBMITTED}` 不含 `REVIEWED`。
   - 处理：一个 assignment 对应多份 submission（定额任务单月可重复提交），`REVIEWED` 无法表达「单份成果审核通过」这一中间态。改为审核（通过/驳回）后统一把 assignment 回写到 `SUBMITTING`（进行中）——定额任务可继续提交，周期任务由 `create()` 的单月查重拦截。`AssignmentStatus.REVIEWED` 保持为预留枚举值（结算 `settle()` 直接按 `SubmissionStatus.APPROVED` 计数并置 `SETTLED`，不依赖 `REVIEWED`）。

---

### 2026-10-23 — 任务1：form_schema 结构扩展（section/table）

#### 1. 原因

设计文档 §3.3 明确 form_schema 需支持三种承载形态：键值对字段、分节标题（`type=section`）、多行子表（`type=table`，`columns` 子列）。后端 Pydantic 模型、前端 TS 类型、小程序渲染、seed 数据均已就绪，唯独运营端可视化编辑器 `form-schema-editor` 仍停留在「扁平键值对」阶段，无法配置 section/table 结构。

#### 2. 修改内容

- `frontend/web/src/components/forms/form-schema-editor/index.vue` 重构，补全 section/table 编辑能力：
  - 类型下拉新增「多行子表 table」「分节标题 section」。
  - 编辑表单按类型动态显隐：section 只填「分节标题」；table 增「子表列」编辑器（列标识/列显示名/列类型 text|textarea|number|date，增删子列）；普通字段增「所属分节」输入框。
  - `saveField`/`handleEdit` 读写 `section`/`columns` 字段；section 跳过 name 必填与查重，table 校验至少一个子列。
  - 表格「字段标识/必填/选项」列对 section/table 类型差异化展示（table 显示子列摘要）。
  - 示例字段更新为含 section/table 的完整示例。
- 新增 `frontend/web/src/views/module_market/template/index.vue`：采集模板 CRUD 页面，作为 `form-schema-editor` 的宿主（此前编辑器是孤立组件）。form_schema 通过 FaForm 的具名 slot（`#form_schema`）接入 `FormSchemaEditor`，code/name/scope 用标准 FaForm 项；详情用 FaDescriptions + 只读表格展示（含 section/table 差异化）。菜单 `MarketTemplate`、权限 `module_market:template:*`、路由已在 `sys_menu.json`/`routers.py` 中就绪。

#### 3. 遇到的问题与处理

1. **子列类型需防无限嵌套**
   - 现象：`FormSchemaField.columns` 自引用，若子列也放开 table/section 类型会导致子表无限嵌套。
   - 处理：子列类型下拉限定为简单字段（text/textarea/number/date），与 seed 数据子列（全为 text/number/date）一致。
2. **ElTable 详情行类型为 `DefaultRow`**
   - 现象：详情表格 `fieldSummary(row)` 的 `row` 推断为 Element Plus `DefaultRow`，不满足 `FormSchemaField`（缺 `label`/`type`）。
   - 处理：调用处加类型断言 `fieldSummary(row as FormSchemaField)`。

#### 4. 验证

- 前端 `pnpm ts:check` 通过；`pnpm eslint` 新页面与编辑器均无报错。
- 后端 `uv run pytest tests/test_market_template_service_item.py -q` 11 passed（含 seed 数据 section/table 校验 + `/market/templates` 路由 + 模板关联任务类型 + 服务项目映射）。

---

### 2026-10-23 — 修复后端启动失败（market_task_type 残留旧种子 + 迁移加 NOT NULL 列）

#### 1. 原因

后端启动 `upgrade head` 阶段报 `NotNullViolationError: column "task_no" of relation "market_task_type" contains null values`。根因：`market_task_type` 表残留 44 条「推倒重做设计」前的旧种子（旧模型带 `form_schema`、无 `task_no`/`template_id`），而迁移 `c7296f450c35` 要给该非空表加 `task_no`、`template_id` 两个 `NOT NULL` 字段，PostgreSQL 直接拒绝。

#### 2. 修改内容（仅数据清理，无代码改动）

1. 删除 `market_task_type` 44 条陈旧数据 → 迁移在空表上顺利加列（`alembic_version` 推进到 `c7296f450c35`）。
2. dev autogen 自动补齐缺失的 `market_service_item`/`market_service_item_task` 两表，及 `market_report`/`market_submission`/`market_task` 补列（生成并应用 `b57ff284aad6`）。
3. 重新播种时出现第二处失败：`market_service_item_task` 映射种子写死 `task_type_id` 1~44，但删除旧行后 `market_task_type` 自增序列已跑到 88，重新插入的 44 行拿到 ID 45~88，映射 FK 引用断裂。
4. 最终 `TRUNCATE` 全部 `market_*` 表 `RESTART IDENTITY CASCADE` 归位序列 → 重跑 `init_db` 播种成功（`market_template` 9 / `market_task_type` 44 / `market_service_item` 37 / 映射 22，ID 均从 1 起，FK 零孤儿）。

#### 3. 遇到的问题与处理

1. **seed 数据硬编码 ID 依赖「空库从 1 自增」**
   - 现象：`market_service_item_task.json` 写死 `task_type_id` 1~44、`service_item_id` 1~37，依赖「空库按 seed 顺序从 1 自增」这一前提；对存量库「删数据重播种」时序列不归位就会 ID 错位、FK 引用断裂。
   - 处理：清理 market 域种子数据时务必用 `TRUNCATE ... RESTART IDENTITY CASCADE`（而非裸 `DELETE`），同步把自增序列归位到 1。

---

### 2026-10-26 — 成果导入功能（market/import_center 模块）

#### 1. 背景

重庆省平台项目真实成果素材（对内任务成果 + 对外服务项目成果）需要**可复用导入功能**：上传结算单 xlsx / 报告 pptx，后端解析入库。方向经确认：可复用导入接口、对内+对外都导、基础数据（执行人用户 / 委托公司）一并创建、报告作为附件引用。

#### 2. 新增模块

`backend/app/modules/market/import_center/`（无 model/crud，复用其它模块的 CRUD 写库）：
- `parser.py`：结算单解析（对内/对外自动识别 + 合并单元格 forward fill）
- `service.py`：导入编排（基础数据创建 + task/assignment/settlement/report 写库，幂等）
- `controller.py`：`POST /market/import/settlement`（结算单导入）+ `POST /market/import/report`（报告附件关联）
- `schema.py`：导入结果统计

`backend/app/modules/market/models.py`：market 域 17 个模型统一注册入口（解决 TYPE_CHECKING 循环引用在独立加载时的 mapper 缺失）。

#### 3. 导入映射

- 对内结算单（熊丽 20900 / 熊志鹏 1600）：按计价项序号分组，一个计价项一个 task（`exec_qty` 汇总各执行人数量）→ 每执行人一条 assignment + settlement（合计 22500）
- 对外结算单（万邦 57400）：创建委托公司 + 每实际执行服务项目一条 report（summary 记录数量金额）
- 报告 pptx：作为 report.attachment 附件路径引用

#### 4. 遇到的问题与处理

1. **结算单合并单元格 forward fill 误伤稀疏列**：实际执行数量/金额是稀疏数据（仅执行行有值），不能与「类型/项目/单价」等定义列一起 fill，需按列范围区分。
2. **model TYPE_CHECKING 循环引用依赖全量导入**：独立使用 ImportService 时 mapper 缺失，建 `models.py` 统一注册。
3. **task_no 唯一冲突**：不同执行人同计价项，task_no 不含执行人导致冲突 → 改为一个计价项一个 task、`exec_qty` 汇总各执行人数量。
4. **分文件导入汇总丢失**：逐文件处理导致 exec_qty 只算单执行人 → 改为先收集所有文件的行再统一分组汇总。
5. **UserCreateSchema 密码强度校验**：默认密码 `123456` 不满足「至少两类」→ 仿 `batch_import` 先 hash 再传 schema。
6. **TRUNCATE CASCADE 误清 seed**：`market_service_item` 有 FK 指向 `market_company`，`TRUNCATE market_company CASCADE` 级联清空服务项目 → 清理业务数据改用 `DELETE`（非 CASCADE）。

#### 5. 验证

- 熊丽 8 行（20900）+ 熊志鹏 2 行（1600）+ 万邦 9 服务项目（57400）
- task 8（exec_qty 汇总正确：5→5、32→10）、assignment 10、settlement 10（22500）、report 9
- 幂等重跑全 0；报告附件关联成功；`ruff check` all passed

---

### 2026-10-26 — 成果导入测试补齐 + 执行人去重 + 上传文件名解析 bug 修复

#### 1. 原因

上一记录「成果导入功能」落地后缺测试覆盖，且审阅发现两个缺陷：
1. **同音姓名合并**：执行人 username 由拼音生成（`_username_from_name`），「黄莉」「黄丽」同拼 `huangli`，仅按 `username` 查询会把两个不同的人合并到同一账号。
2. **上传文件名被污染**：`controller._save_upload` 用 `UploadUtil.generate_safe_filename` 保存，会追加 `_时间戳A随机码` 后缀；对内结算单执行人从文件名解析（`0.重庆-省平台项目结算单-重庆熊丽.xlsx` → 执行人「熊丽」），被存成 `...重庆熊丽_20261026…A123.xlsx` 后 `_executor_from_filename` 解析出 `熊丽_20261026…A123`。对外结算单公司名不受影响（时间戳落在「服务项目结算单」之后被切掉）。

#### 2. 修改内容

- `import_center/service.py`：`_get_or_create_user` 改为「先按 `name` 精确匹配（同名视为同一人，幂等）→ 拼音 `username` 冲突则追加数字后缀」，新增通用 `_next_available(base, crud, field)`；`_get_or_create_company` 同步用 `_next_available` 生成不冲突的 `code`（`CompanyModel.code` 也有唯一约束）。
- `import_center/controller.py`：`_save_upload` 保存文件名改用 `UploadUtil.sanitize_filename`（保留原始文件名、仅清理危险字符），不再追加时间戳。导入场景同名覆盖可接受（同一结算单重复导入本就幂等）。
- 新增 `tests/test_market_import_center.py`（15 用例）：文件名约定/拼音转换、单元格转换、forward fill、detect_kind、对内/对外结算单解析。
- 新增 `tests/test_market_import_center_flow.py`（7 用例）：对内导入、对外导入、幂等重跑、同音去重（黄莉/黄丽 → `huangli`/`huangli2`）、同名跨文件复用、报告附件关联与不存在分支。

#### 3. 遇到的问题与处理

1. **generate_safe_filename 时间戳污染文件名解析**
   - 现象：HTTP 上传对内结算单后执行人被识别成 `熊丽_20261026…A123`，导致误建带时间戳的用户。
   - 处理：导入专用上传保留原始文件名（sanitize），文件名约定解析与落盘名解耦。
2. **同名执行人合并语义**
   - 现状：完全同名（如两个「黄莉」）按同一人合并，因文件名仅保留姓名、无工号/手机号等辅助标识，暂无法区分。若日后出现同名不同人需引入额外标识。

#### 4. 验证

- `pytest tests/test_market_import_center.py` 15 passed；`test_market_import_center_flow.py` 7 passed。
- market 全量 81 passed；`ruff check` all passed。

---

### 2026-10-26 — 成果导入前端集成（运营端上传页面）

#### 1. 原因

后端导入接口（`POST /market/import/settlement`、`POST /market/import/report`）与菜单（`MarketImport`，`component_path=module_market/import/index`）已就绪，运营端缺上传页面。

#### 2. 修改内容

- 新增 `frontend/web/src/api/module_market/import.ts`：`ImportAPI.importSettlement`（多文件）+ `ImportAPI.linkReport`（单文件），均走 FormData multipart；`ImportResult` 类型对齐后端 `ImportResultSchema`。
- 新增 `frontend/web/src/views/module_market/import/index.vue`：两个 Tab ——「结算单导入」（周期 + 多选 xlsx 拖拽上传 + 导入结果统计与跳过告警列表）、「报告附件关联」（服务项目号 + 周期 + 单份 pptx 上传）。

#### 3. 遇到的问题与处理

1. **el-upload 文件类型谓词 TS2677**：`UploadUserFile.raw` 类型为 `UploadRawFile`（`File & { uid }`），用 `File` 做 filter 类型谓词触发 TS2677/TS2345；改为 `f is UploadRawFile` 后 `UploadRawFile[]` 兼容 `File[]` 形参。

#### 4. 验证

- `pnpm ts:check` 通过；eslint 无报错。

---

### 2026-10-26 — 成果导入「同名不同人」处理：同名冲突告警

#### 1. 原因

执行人仅凭姓名区分，完全同名（两个「黄莉」）会按 `name` 精确匹配合并到同一账号，无法区分「同一人重复导入」与「同名不同人」。真实素材（文件名 + 结算单内容）均不含工号/手机号，经确认采用「告警 + 人工确认」策略，暂不引入新标识字段。

#### 2. 修改内容

- `import_center/schema.py`：`ImportResultSchema` 新增 `warnings` 字段（需人工确认的告警），与 `errors`（跳过/错误）分离。
- `import_center/service.py`：`_get_or_create_user` 同名命中复用账号时追加告警「执行人「X」与已有账号（username）同名，成果已归并至该账号；若为不同人员请人工拆分」。
- 前端 `import.ts`：`ImportResult` 增 `warnings`；`import/index.vue`：结果区新增同名冲突告警展示（`type=warning`），`errors` 展示改为 `type=error`。
- 测试：`test_market_import_center_flow.py` 同名复用用例增 `warnings` 断言。

#### 3. 验证

- 后端 22 passed（15 单元 + 7 集成）；`ruff check` 通过。
- 前端 `pnpm ts:check` 通过；eslint 无报错。

---

### 2026-10-26 — 成果导入端到端验证 + 真实素材冒烟测试 + 菜单同步

#### 1. 原因

前端页面与后端导入链路完成后，需用真实素材端到端验证，并沉淀自动化冒烟测试防止解析回归；验证中发现「新增菜单不自动同步到已初始化库」的问题。

#### 2. 端到端验证

- 启动后端（8001，reload 模式）+ 前端 vite（5181），浏览器登录 super/123456（含滑块验证码）。
- 进入「市场管理 → 成果导入」，上传真实素材（熊丽/熊志鹏对内 + 万邦对外）周期 2099-01。
- 结果：新增任务 8、分派 10、结算 10、报告 9；同名冲突告警 10 条（熊丽/熊志鹏已在开发库有账号）。
- 页面正确渲染「结算单导入 / 报告附件关联」两个 Tab 与导入结果统计、同名冲突告警。

#### 3. 真实素材冒烟测试

- 新增 `tests/test_market_import_center_real_data.py`（3 用例）：用 `docs/materials/重庆任务成果素材` 真实文件断言解析数字——熊丽 8 行/20900、熊志鹏 2 行/1600、万邦 9 行/57400。
- 前端仅透传文件、xlsx 解析在后端，故冒烟测试落在后端 parser 层（服务前端「成果导入」页面的解析链路）。

#### 4. 遇到的问题与处理

1. **新增菜单不自动同步到已初始化库**
   - 现象：`sys_menu.json` 新增「成果导入」菜单后，开发库 fastapiadmin 侧栏无该菜单（前端 `#/market/import` 404）。
   - 根因：`InitializeData.__init_data` 对「表已有数据则整体跳过」（幂等），`sys_menu` 非空即不重播，故新增菜单不会 upsert。
   - 处理：手动向开发库插入「成果导入」菜单（id=202）+「导入」按钮（id=203，parent_id=12）。**待办**：如需可重复部署，建议将菜单种子改为按 `route_name` 增量 upsert，或提供菜单同步命令。
2. **前端菜单加载时序**：菜单同步后直接 `page.goto` 到仅 hash 不同的 URL 不会触发完整 reload，菜单未重新拉取仍 404；完整刷新（`page.reload`）后菜单与路由才更新。

#### 5. 验证

- `pytest tests/test_market_import_center_real_data.py` 3 passed；`ruff check` 通过。
- 修正早期记录中熊志鹏数字：4 行 5100 → 2 行 1600（assignment/settlement 12→10，合计 22500）。

---

### 2026-10-26 — 成果导入修复：明细模板文件被误识别为结算单

#### 1. 原因

运营上传真实素材时把执行人目录下除结算单外的明细模板文件（如 `1.等级医院管理采集模板（必选）-重庆熊丽.xlsx`）一并上传。这些模板的**首个 sheet 也叫「结算单」**（含「实际执行」），`detect_kind` 按内容识别为 inner；但其文件名不含「省平台项目结算单-」，`_executor_from_filename` 把整个模板文件名当执行人姓名，`_username_from_name` 生成超长拼音账号，触发 `UserCreateSchema` 校验失败（username 最长 32 字符）。

#### 2. 修改内容

- `import_center/service.py` `import_settlements`：inner/outer 分支增加文件名二次校验——对内必须含「省平台项目结算单-」、对外必须含「服务项目结算单」，否则跳过并记入 errors，明细模板等非结算单文件不再误导入。
- 新增测试 `test_market_import_center_flow.py::TestSkipNonSettlement`：明细模板（内容含「实际执行」+ 文件名非结算单约定）应跳过，不误建账号/任务/结算。

#### 3. 验证

- 26 passed（15 单元 + 8 集成 + 3 真实素材冒烟）；`ruff check` 通过。

---

### 2026-10-27 — 新增 PostgreSQL 线上 docker-compose 部署 + 服务器 SSH 密钥加固

#### 1. 原因

用户要求：①在当前基础上添加 docker-compose 部署线上环境（新服务器 `118.24.244.36`，域名 `admin.xfoxlab.com.cn` / `wxh5.xfoxlab.com.cn`，用 Caddy 反代）；②服务器改为密钥登录、关闭密码登录、仅密钥登录。

#### 2. 修改内容

**部署文件（新增，与旧 MySQL 版 `docker-compose.yaml` 平行）**
- `docker/docker-compose.prod.pg.yaml`：`postgres:18-alpine` + `redis:7-alpine` + `backend`（`DB=postgres` 构建）+ `caddy:2-alpine` 四容器完整编排。
- `docker/Caddyfile`：两个域名 `/api/v1/*` 反代 `backend:8001` + 静态站点 + Caddy 自动 HTTPS。
- `docker/.env.prod.pg.example`：PG/Redis/安全/域名等环境变量模板（`ALLOWED_HOSTS`/`OAUTH_ALLOWED_HOSTS` 为 JSON 数组）。
- `docker/README.prod.pg.md`：部署前置条件与上线步骤。

**服务器 SSH 加固（118.24.244.36）**
- 生成专用密钥对 `~/.ssh/foxwork_prod`（ed25519），公钥推入 ubuntu 用户 authorized_keys。
- 关闭密码登录：新增 `/etc/ssh/sshd_config.d/99-hardening.conf` + 修正 cloud-init 的 `50-cloud-init.conf`（`PasswordAuthentication no`）；`PermitRootLogin prohibit-password`。
- SSH 端口 22 → 12211：改 systemd socket override（`/etc/systemd/system/ssh.socket.d/port-12211.conf`）并同步改 sshd_config `Port` 备用。

#### 3. 遇到的问题与处理

1. **服务器实际是全新的，与「仅连宿主机」选择矛盾**
   - 现象：探查发现 118.24.244.36 是空 Ubuntu 26.04（无 PG/Redis/docker/caddy，仅监听 22/53）。用户此前选择「服务器已有 PG/Redis、仅连宿主机」的前提不成立。
   - 处理：改为**完整容器化**（PG/Redis 也进 compose，用用户给的 `xfoxlab` / Redis 密码初始化）。
2. **Ubuntu 26.04 SSH 端口由 systemd socket activation 控制**
   - 现象：sshd_config 的 `Port` 全是注释，端口实际由 `ssh.socket` 的 `ListenStream` 决定。
   - 处理：改 ssh.socket override，先加 12211 保留 22 兜底 → 验证 12211 可登录 → 再撤 22。
3. **腾讯云 cloud-init 写死 `PasswordAuthentication yes`**
   - 现象：drop-in 的 `PasswordAuthentication no` 被词法序更靠前的 `50-cloud-init.conf`（cloud-init 注入 yes）覆盖。
   - 处理：直接 sed 改 `50-cloud-init.conf` 为 no，`sshd -T` 复核后 reload。
4. **22 端口「nc 可达但 SSH 被拒」假象**：撤掉 22 后 `nc -z` 仍显示可达（腾讯云网络层 TCP 假响应），但 `ss` 已无 22 监听、SSH 登录 `Connection closed`，确认为已关闭。

#### 4. 验证

- `docker compose config` 语法通过；SSH 密钥登录 12211 OK、密码登录被拒、22 已停用。

---

### 2026-10-27 — 线上发布部署完成（拉起 caddy + 双域名 HTTPS 签发）

#### 1. 原因

上一记录落地了 compose 编排与 SSH 加固，但线上只起了 `foxwork-backend`，`foxwork-caddy` 未启动——对外 80/443 无服务、双域名无法访问、HTTPS 证书未签发。用户要求「发布部署没完成就继续完成」。

#### 2. 完成内容

- 拉起 `foxwork-caddy`（拉取 `caddy:2-alpine` 镜像 + `docker compose up -d caddy`），80/443 对外监听就绪。
- 双域名 Let's Encrypt 证书自动签发成功：`admin.xfoxlab.com.cn` / `wxh5.xfoxlab.com.cn`。
- 验收：两域名首页均 200；`/api/v1/monitor/health/check` 返回 `db_status=1 / redis_status=1 / environment=prod`；`foxwork-backend` healthy + `foxwork-caddy` up。

#### 3. 遇到的问题与处理

1. **admin 域名首次签发失败（跨境 secondary validation 超时）**
   - 现象：`wxh5` 走 `tls-alpn-01`（443）一次成功；`admin` 的 `tls-alpn-01` 未通过、回退 `http-01`，但 Let's Encrypt 海外 secondary 校验节点访问 80 报 `Timeout during connect (likely firewall problem)`，签发失败后回退到连不上的 ZeroSSL 卡住。
   - 处理：`docker compose restart caddy` 重新触发签发（wxh5 证书已缓存不受影响），`admin` 第二次走 `http-01` 通过，证书生效。

---

### 2026-10-27 — 腾讯云安全组拆分优化（服务器/数据库独立安全组）

#### 1. 原因

三类资源（CVM `ins-2j0mc4d2` / PG `postgres-hdiavxkv` / Redis `crs-ooea4ubc`）此前共用一个系统默认安全组 `sg-fpqyb3b2`，规则混杂：SSH 12211 全网开放、PG 5432 / Redis 6379 对整个 VPC 网段 `172.30.0.0/20` 开放。用户要求按最佳实践拆分为独立安全组、数据库最小权限。

#### 2. 修改内容

- 新建服务器安全组 `sg-kie3663c`（foxwork-server）：入站 80/443/12211（全网）+ 出站全放行，绑定 CVM。
- 新建数据库安全组 `sg-e9vg2lm8`（foxwork-database）：入站 5432/6379 仅 `172.30.0.13/32`（CVM 内网 IP）+ 出站全放行，绑定 PG + Redis。
- 清空 default 安全组 `sg-fpqyb3b2` 的 8 条入站规则（保留全放行出站）。
- 顺带修正 `docker-compose.prod.pg.yaml` 注释中 PG/Redis 内网地址写反、`Caddyfile` ACME 邮箱改为 `service@xfoxlab.com.cn`。

#### 3. 遇到的问题与处理

1. **API 创建的安全组无默认出站规则 → CVM 切组后连不上数据库**
   - 现象：CVM 切到新 server 组后，backend 报 `Timeout connecting to server`，PG/Redis 连不上；但 SSH、Web 仍正常。
   - 根因：`CreateSecurityGroup` API 创建的安全组出站默认全拒（只有控制台创建才会自动带全放行出站）。SSH/Web 是入站连接（有状态，响应自动放行），而 CVM 主动访问 PG/Redis 是出站连接，需显式出站规则。
   - 处理：给 server 组和 database 组补「出站全放行」规则后恢复。教训见踩坑 11。

#### 4. 验证

- 最终绑定：CVM→`sg-kie3663c`、PG/Redis→`sg-e9vg2lm8`；default 组入站 0 条。
- `/api/v1/monitor/health/check` 返回 `db_status=1 / redis_status=1`；SSH 12211 可达、双域名 HTTPS 200。

---

### 2026-10-27 — 修复前端静态资源 MIME type 错误（SPA base 前缀与 Caddy root 不匹配）

#### 1. 原因

运营后台 / 小程序 H5 打开白屏，浏览器报 `Failed to load module script: Expected a JavaScript module but the server responded with MIME type "text/html"`。

#### 2. 根因

前端构建产物的 `base` 分别是 `/web/`（运营后台）与 `/app/`（小程序 H5），`index.html` 用 `/web/js/*.js`、`/app/assets/*.js` 绝对路径引用资源；但 Caddy 的 `root` 直接指向产物根（`/srv/web`、`/srv/app`），未剥离 `/web/`、`/app/` 前缀，导致请求 `/web/js/xxx.js` 时实际查找 `/srv/web/web/js/xxx.js`（多一层），找不到便 `try_files` 回退到 `index.html`，返回 HTML 而非 JS。

#### 3. 修改内容

`docker/Caddyfile` 两个站点改用 `handle_path` 剥离前缀：

- `admin`：`handle_path /web/*` → root `/srv/web`；根路径 `redir / /web/ 308`
- `wxh5`：`handle_path /app/*` → root `/srv/app`；根路径 `redir / /app/ 308`

#### 4. 验证

`/web/js/index.sSvSqKWy.js` 与 `/app/assets/index-BSh6nfjC.js` 均返回 `200 text/javascript`；两站点首页 200；根路径 308 跳转正确；API 健康检查 `db_status=1 / redis_status=1`。

---

### 2026-10-27 — 修复前端运行时错误（WS 端点未配置 + 旧产物 page_size 超限）

#### 1. 原因

运营后台登录后报两个错误：① `TypeError: Cannot read properties of undefined (reading 'replace')`（`httpEndpoint`）；② `GET /api/v1/system/user/list?page_size=1000` 返回 422 `Input should be less than or equal to 100`。

#### 2. 根因

① `httpEndpoint(import.meta.env.VITE_APP_WS_ENDPOINT)` 中 `VITE_APP_WS_ENDPOINT` 未配置（仓库只有 `.env.production.example`，无真实 `.env.production`），`httpEndpoint` 里 `endpoint.replace(...)` 对 undefined 直接崩溃。
② 服务器上的前端产物是 10-22 的旧构建，`loadOptions` 当时用 `page_size=1000`；当前源码已改为 `page_size=100`，但产物未重新构建。

#### 3. 修改内容

- `frontend/web/src/utils/sse/index.ts`：`httpEndpoint` 增加 undefined 兜底，回退到 `window.location.origin`（同源 SSE）。
- 新建 `frontend/web/.env.production`：设置 `VITE_APP_WS_ENDPOINT = wss://admin.xfoxlab.com.cn`、`VITE_APP_ENV = prod`、`VITE_DROP_CONSOLE = true`。
- 重新构建 `frontend/web`（`pnpm run build:prod`）并 rsync 部署到服务器 `docker/nginx/web/dist/`。

#### 4. 验证

新 bundle `index.CvYtKwlp.js` 中 `page_size:1000` 为 0、`page_size:100` 与 `window.location.origin` 兜底均已打入；`/web/js/index.CvYtKwlp.js` 返回 `200 text/javascript`；SSE 端点 `/api/v1/monitor/health/stream` 正常返回健康数据。

---

### 2026-10-27 — 修复小程序 H5 登录 CORS 错误（app 端未迁移同源部署）

#### 1. 原因

线上小程序 H5（`wxh5.xfoxlab.com.cn`）登录页验证码获取失败，浏览器报 CORS 错误：`Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present`，请求地址为 `https://service.fastapiadmin.com/api/v1/system/auth/captcha/get`。

#### 2. 根因

`frontend/app/.env.production` 未跟上新域名同源部署方案：`VITE_API_BASE_URL` 仍指向旧域名 `service.fastapiadmin.com`，导致 H5 跨域请求旧域名，而旧域名后端 CORS 白名单无 `wxh5.xfoxlab.com.cn`，preflight 被拒。web 端（运营后台）此前已迁移同源（见上一记录），仅 app 端遗漏。

#### 3. 修改内容

- `frontend/app/.env.production`：`VITE_API_BASE_URL` 由 `https://service.fastapiadmin.com` 改为**留空**（走同源相对路径 `/api/v1`）；`VITE_APP_WS_ENDPOINT` 由 `wss://service.fastapiadmin.com` 改为 `wss://wxh5.xfoxlab.com.cn`。

#### 4. 部署与验证

- 重新构建 H5（`pnpm run build:h5`）并 `rsync --delete` 上传至服务器 `/home/ubuntu/foxwork/docker/nginx/app/dist/build/h5/`（Caddy `/srv/app` ro 挂载，file_server 读盘无需重启）。
- 验证：产物中 `service.fastapiadmin.com` 出现次数为 0；同源验证码接口 `https://wxh5.xfoxlab.com.cn/api/v1/system/auth/captcha/get` 返回 `200 application/json`（`{"code":0,"msg":"获取验证码成功"}`）。

#### 5. 遇到的问题与处理

1. **本机 curl 线上 443 被网络层拦截（SSL_ERROR_SYSCALL）**：本机到 `118.24.244.36` 的 443 出站被拦，验证需 SSH 到服务器本机执行；且 Caddy 自动 HTTP→HTTPS 重定向，用 `http://127.0.0.1` 测会得到 308 误导，需用 `--resolve wxh5.xfoxlab.com.cn:443:127.0.0.1 -k` 走 HTTPS 正确验证。

---

### 2026-10-27 — 腾讯云资源 Terraform 编排（安全组/CAM 子账号/COS 自定义域名）

#### 1. 原因

用户要求：①把安全组、CAM 子账号等腾讯云资源改用 Terraform 编排（IaC 化）；②对象存储 COS 配置自定义域名，用 `xfoxlab.com.cn`，前缀由助手定（定为 `cos`，即 `cos.xfoxlab.com.cn`）。

#### 2. 修改内容

**新增 `terraform/` 目录**（IaC 项目；当日已独立为同级独立 git 仓库 `../foxwork-infra`，脱离本仓库单独版本控制）：
- `provider.tf`：`tencentcloudstack/tencentcloud` provider（region=ap-chongqing），认证走环境变量 `TENCENTCLOUD_SECRET_ID/SECRET_KEY`（与 tccli 根账号同源），密钥不进库。
- `variables.tf`：region / project / domain / cos_domain_prefix / cvm_private_ip 及派生 locals。
- `security_groups.tf`：`foxwork-server`（入站 80/443/12211 + 出站全放行）、`foxwork-database`（入站 5432/6379 仅 172.30.0.13/32 + 出站全放行），各配 `security_group_rule_set`。
- `cam.tf`：`foxwork` 子账号（console_login=false, use_api=true）+ `foxwork-cos-access` 策略 + 用户策略绑定。
- `cos.tf`：生产桶 `foxwork-prod-1516998879`（private）+ `origin_domain_rules` 绑定 `cos.xfoxlab.com.cn`（REST）。
- `dnspod.tf`：新增 `cos` CNAME → `foxwork-prod-1516998879.cos.ap-chongqing.myqcloud.com`。
- 其余：`outputs.tf`、`.gitignore`（忽略 tfstate/tfvars/.terraform）、`terraform.tfvars.example`。

**导入已有资源**（`terraform import`，将存量基础设施纳入管理）：
- 安全组 `sg-kie3663c`/`sg-e9vg2lm8` + 两组 rule_set（按 SG id 导入）。
- CAM 用户 `foxwork`、策略 `foxwork-cos-access`（PolicyId 291479731）、用户策略绑定（导入 ID 为 `foxwork#291479731`）。
- COS 桶 `foxwork-prod-1516998879`。

导入后 `terraform plan` 零 drift（安全组/CAM/策略的描述字符串精确匹配云端），仅剩 2 处新增：COS 域名绑定 + DNS 记录。

#### 3. 遇到的问题与处理

1. **本机无 Terraform 且 homebrew-core 已移除 terraform 公式**
   - 现象：`brew install terraform` 报 `No available formula`（Hashicorp 已把 terraform 移出 core，只有 terraform-ls/terraformer 等周边）。
   - 处理：改为从 `releases.hashicorp.com` 直接下载官方二进制 v1.17.0 到 `~/.local/bin/terraform`（已在 PATH），绕开 `brew tap hashicorp/tap`（走 GitHub，国内慢）。

2. **COS 自定义域名绑定被 ICP 备案拦截（未解决，待用户完成备案）**
   - 现象：`terraform apply` 时 DNS 记录创建成功，但 COS 桶 `PUT Bucket domain` 报 `451 DomainAuditFailed: Please complete the ICP registration of your domain before use it in Mainland China`。
   - 结论：`xfoxlab.com.cn`（主体「玄狐（重庆）人工智能科技有限公司」）尚未完成 ICP 备案（或备案未与本账号 100054224426 关联）。COS 回源自定义域名是**硬性备案要求**（比 CVM 更严格）；域名已实名但 `ba` 接口无该域名备案记录。
   - 影响：`cos.xfoxlab.com.cn` CNAME 已生效，但 COS 侧域名绑定未写入，请求会被 COS 拒绝。Terraform 状态中 `cos_bucket.prod` 保持「待加 origin_domain_rules」，备案完成后重跑 `terraform apply` 即可补齐。

3. **`cam_user_policy_attachment` 导入 ID 格式**
   - 现象：用 uid（27836463）导入报 `ResourceNotFound.UserNotExist`。
   - 处理：正确格式是 `user_name#policy_id`（即 `foxwork#291479731`），非 uid。

#### 4. 验证

- `terraform validate` 通过；`terraform plan` 显示已有资源零 drift。
- `dig cos.xfoxlab.com.cn` 返回 `foxwork-prod-1516998879.cos.ap-chongqing.myqcloud.com`（CNAME 生效）。
- 待备案完成后 `terraform apply` 补齐 COS 域名绑定即可闭环。

---

### 2026-10-27 — 运营工作台（市场数据统计）+ 运营端/C 端权限收紧

#### 1. 原因

用户要求：①为运营设计独立 dashboard（市场数据统计）；②运营角色权限仅限「运营工作台 + 市场管理」菜单；③C 端用户权限仅限 C 端专属菜单，不能有全部页面权限。

#### 2. 修改内容

**后端：运营工作台统计 API**
- 新增 `app/modules/market/dashboard/` 模块（schema/service/controller），`GET /market/dashboard/overview`，权限码 `module_market:dashboard:query`。
- 统计：任务（总数/进行中/已完成/已结算）、成果（总数/待审核/通过/驳回）、结算（总数/应发金额合计）、基础数据（项目/公司/机构/服务项目计数），均排除软删除。
- `routers.py` 注册 DashboardRouter 到 `/market` 分组。

**前端：运营工作台页面**
- `api/module_market/dashboard.ts` + `views/module_market/dashboard/index.vue`（统计卡片）。

**菜单**
- `sys_menu.json` 新增「运营工作台」目录（/ops-dashboard）+「工作台概览」子菜单（component_path=module_market/dashboard/index，权限码 module_market:dashboard:query，scope=web）。

**权限脚本（ops/prod/）**
- `base.py` 增加 `ensure_menu` / `collect_subtree_ids` / `bind_menus_to_role` 菜单辅助。
- `init_ops_account.py`：运营角色（OPERATOR）只关联「运营工作台 + 市场管理全部菜单」；创建 admin（超管）+ operator（OPERATOR）。
- `init_c_account.py`：USER 角色只关联 scope=app 的 C 端菜单（首页/同事/打卡/消息/我的）；创建 user。
- 脚本幂等，密码/密钥走 `.env`。

#### 3. 关键设计

- 菜单用 `scope` 字段区分端：`web`（管理端，运营）/ `app`（移动端，C 端）；C 端 5 个菜单 scope=app。
- 权限模型 = 角色-菜单关联（sys_role_menus）→ 前端菜单渲染 + 后端 API 权限码校验（AuthPermission，超管 is_superuser 绕过）。

#### 4. 验证

- `ruff check` 通过（dashboard 模块 + routers.py）；`python -m py_compile` 通过（ops/prod 脚本）。
- basedpyright 对新建 dashboard 目录有 reportImplicitRelativeImport 误报（import 与其它 controller 完全一致），ruff 已确认正确。

---

### 2026-10-27 — 生产部署完成（前端上线 + 菜单 redirect 数据修复 + PasswordHash→PwdUtil）

#### 1. 原因

后端已部署完成，需完成前端运营后台上线（让「运营工作台」页面生效）；上线联调中发现线上 `GET /user/current/info` 返回 400，且 `ops/prod/` 初始化脚本仍引用已重命名的 `PasswordHash`。

#### 2. 完成内容

**前端构建部署**
- `frontend/web` 执行 `pnpm build:prod`（`base=/web`，terser 压缩 + gzip/brotli），产物 rsync 到服务器 `~/foxwork/docker/nginx/web/dist/`（Caddy 挂载 `/srv/web`）。
- 验收：`https://admin.xfoxlab.com.cn/web/` 首页、入口 JS、健康检查均 200。

**线上菜单数据修复**
- 现象：`GET /api/v1/system/user/current/info` 返回 400「目录类型必须填写重定向地址」。
- 根因：`sys_menu` 里「运营工作台」目录（id=214，type=1）`redirect` 为 NULL——它是后加的种子菜单，在存量库上重新初始化时以不完整方式写入（丢了 redirect）。响应模型 `MenuOutSchema` 继承 `MenuCreateSchema` 的 `validate_fields` 写入校验，读取菜单时对该目录抛错，连带登录后首个接口整体 400。
- 处理：`UPDATE sys_menu SET redirect='/ops-dashboard/overview' WHERE id=214`，补回与 `sys_menu.json` 一致的 redirect 值。

**PasswordHash→PwdUtil 修复**
- `ops/prod/base.py`、`init_c_account.py`、`init_ops_account.py` 中 `from app.utils.password_util import PasswordHash` 改为 `PwdUtil`（类早已改名，旧引用会导致 ImportError）。提交 `1dcce22d fix: 类型`。

#### 3. 遇到的问题与处理

1. **前端部署验证时 curl 返回 SSL error（exit 35）**：本机/服务器 curl `localhost`、`127.0.0.1` 均 TLS 握手失败——Caddy 只对配置域名（`admin.xfoxlab.com.cn` 等）签发证书，`localhost` SNI 不匹配。处理：`curl --resolve admin.xfoxlab.com.cn:443:127.0.0.1` 指定 SNI 后验证通过；对外域名访问实际正常。

---

### 2026-10-28 — 任务模块重新设计（推倒重来，后端已落地）

#### 1. 原因

用户指出市场域现有设计有缺陷，要求**重新设计、不做兼容**。依据 `docs/materials/任务/`（6 个药品示例任务目录，各 38 文件）与 `docs/重庆-省平台-市场管理-项目任务清单.xlsx` 重新分析，给出 7 点硬要求：①任务配置 JSONB + Pydantic；②任务层级两级（`市场机构管理-等级医院管理`）；③添加项目时选一级/二级；④C 端任务名 = `项目名-二级任务名`（如 `一心坦-等级医院管理`）；⑤任务发布有周期（如一年），周期内每月重复提交成果 + 每月提交报告给甲方；⑥按项目任务清单 TO C 任务制作任务模板，发布项目可选关联；⑦后台收敛为 4 模块（项目管理/任务管理/发放管理/机构管理）。

#### 2. 分析结论（关键发现）

1. **目录是两级**：一级（市场机构管理/市场档案信息调研/专项调研/会议服务）→ 二级（等级医院管理/…）；`配送协调/库存盘点/价格核查/竞品调研/销售对账` 是二级任务采集表内的**多行子表工作区**，不是独立任务层级。
2. **单价挂在二级任务**：`等级医院管理`=2000 元/月/家（一个二级任务内多个工作区共享同一单价），v1.x 把单价拆到 44 计价项是错的。
3. **结算单只有一套**（类型/任务/单位/单价/执行标准/实际执行），v1.x 的 `service_item(37)+task_type(44)` 两套 + 映射是过度设计。
4. **任务设计应聚合为一份 JSONB**：表单 + 单价 + 执行标准 + 执行人要求 + 提交/去重规则 + 执行子模式，由 Pydantic `TaskConfig` 权威定义。

#### 3. 修改内容（仅新增设计文档）

- 新增 `docs/06-任务模块重新设计.md`：两级任务目录（5 一级 + 22 二级）、`TaskConfig`/`FormSchemaField` Pydantic 模型、4 模块收敛（project/task/payout/institution）、状态机、API 摘要、分模块并行实施计划。
- 关键模型变更：`market_task_category` + `market_task_template(config JSONB)` 取代 `market_task_type(44)+market_template(9)`；`market_project_template` 承载「项目选二级模板」；`market_task.name` 自动生成 `{项目}-{二级}`；`market_report` 改月度、按「项目×二级任务×月份」生成；新增 `market_institution_image` 归集 C 端图片。

#### 4. 评审拍板（用户确认）

- 单价：专项调研 4 项、宣传 2 项先按「可配、暂空」落地（`price=null`）。
- 月度报告：运营**手动**点「生成月度报告」，不自动。
- 节奏：推倒重写，不兼容。

#### 5. 后端落地内容（已完成，4 个并行 Agent + 主 Agent）

- **删除旧模块**：`service_item`/`template`/`quota`/`import_center`/`dashboard`/`company`/`report`/`assignment`/`submission`/`settlement`（后 5 个迁入新目录重写）；删除旧种子 `market_template/task_type/service_item/service_item_task.json`；删除 `alembic/versions` 3 个中间态迁移（恢复「仅 __init__.py」）。
- **共享件**：`config.py`（`TaskConfig`/`SubmitRule`/`ExecMode`）、`enums.py`（移除 `TaskKind`，新增 `SubjectType`/`PricingMode`/`SubmitCadence`）、`models.py`（16 模型注册）、`routers.py`（13 个 market Router）、`initialize.py`（seed 清单 `TaskCategory→TaskTemplate`）、`mini_controller.py`（C 端接口，补 `tasks/{id}`/`assignments/{id}` 详情）。
- **种子**：`market_task_category.json`（5 一级）、`market_task_template.json`（22 二级，含完整 `form_schema`）。
- **4 个模块重写**（五件套 model/schema/crud/service/controller）：
  - `project`（项目管理）：`CompanyModel`/`ProjectModel`/`ProjectTemplateModel`/`ReportModel`；`ProjectService.publish` 按关联模板批量生成任务、`ReportService.generate` 手动生成月度报告。
  - `task`（任务管理）：`TaskCategoryModel`/`TaskTemplateModel`/`TaskModel`/`AssignmentModel`/`SubmissionModel`；`TaskService.publish/hall_tasks`、`AssignmentService.accept/claim`、`SubmissionService.review`。
  - `payout`（发放管理）：`SettlementModel(带 period)/SettlementItemModel(两级 category_name/template_name)/PayoutConfigModel/AllowanceModel/AllowanceDetailModel`；`SettlementService.settle/confirm`、`PayoutService.my_payout`。
  - `institution`（机构管理）：`InstitutionModel`/`InstitutionImageModel`；`InstitutionImageService.list_by_institution` 归集图片。

#### 6. 验证结果

- `ruff check`：All checks passed。
- `import`：16 模型 + 13 market Router（/mini /companies /projects /reports /categories /templates /tasks /assignments /submissions /settlements /payout /institutions /institution-images）全部成功。
- `configure_mappers`：全量 relationship 字符串引用（含跨模块 TaskTemplateModel/SubmissionModel/UserModel）解析成功。
- 种子校验：22 个二级模板 `config` 全部通过 `TaskConfig.model_validate`。

#### 7. 剩余待办

- 前端：web 4 菜单（项目管理/任务管理/发放管理/机构管理）+ 菜单 seed + app C 端页面。
- 测试：`tests/test_market_*.py` 基于旧模型，需重写（当前会 collection 失败）。
- `dashboard`（运营工作台）与 `import_center`（成果导入）随旧模型一并删除，若需保留需基于新模型重建。

---

### 2026-10-28 — 市场模块重写收尾：修复索引名冲突 + 前端 web 类型错误

#### 1. 原因

4 个并行 Agent 完成后端 4 模块（task/project/payout/institution）重写后，遗留两处阻断：

1. **后端全量测试 ERROR**：`create_all` 自举时抛 `DuplicateTableError: relation "ix_market_task_template_id" already exists`，所有依赖 TestClient 布局的用例（含 market 集成测试）失败。
2. **前端 web `pnpm ts:check` 14 处报错**：`form-schema-editor` 引用已删除的 `task-type` 模块、`institution-image` 用不存在的 `formatter` 属性、`task-template` 布尔选项类型不匹配。

#### 2. 修改内容

**后端索引名冲突修复**

- 根因：SQLAlchemy 命名约定 `ix_%(column_0_label)s` 下，`market_task.template_id`（列索引）与 `market_task_template.id`（表名+主键列）都渲染为 `ix_market_task_template_id`，`create_all` 建到第二个同名索引时撞名。
- 处理：`task/model.py` 的 `TaskModel.template_id` 移除 `index=True`，改为在 `__table_args__` 显式声明 `Index("ix_market_task_template_fk", "template_id")`（SQLAlchemy 的 `Column.index` 仅接受布尔，不接受字符串名，需用显式 `Index` 对象）。
- 删除 dev autogen 残留的根迁移 `alembic/versions/2026_10_28_1158_8bbefa5ae3cb.py`（恢复 versions/ 仅 `__init__.py` 纯净态，见踩坑 15）。

**前端 web 类型修复**

- 新建 `api/module_market/form-schema.ts`：`FormSchemaField`/`FormSchemaFieldType`/`FormSchemaOption`，对齐后端 `form_schema.py` 权威定义。
- `form-schema-editor/index.vue`：import 由已删除的 `task-type` 改为 `form-schema`。
- `task-template.ts`：`TaskConfig.form_schema` 由 `Record<string, unknown>[]` 改为 `FormSchemaField[]`。
- `institution-image/index.vue`：`FaDescriptions` 的 `DescriptionsItem` 无 `formatter` 属性，改为 `slot` + 具名插槽渲染 `#来源成果`。
- `task-template/index.vue`：`ENABLED_OPTIONS` 布尔值改为字符串 `"true"/"false"`（`OptionType.value` 仅 `string | number`），搜索表单 `enabled` 类型同步。

#### 3. 验证

- 后端：`pytest tests/` 242 passed；`ruff check app/modules/market/` all passed。
- 前端：`pnpm ts:check` 通过（0 错误）。

#### 4. 剩余待办（未阻断，待决策）

- 小程序端 `api/module_market/index.ts` 仍残留旧模型类型（`TaskTypeItem`/`TaskItem`/`AssignmentItem` 引用 `task_type`/`service_item`/`task_kind`/`unit_price`/`exec_qty` 等已删除概念）；各页面已改用本地类型 + `as any` 绕过，类型定义待清理对齐。
- `sys_menu.json` 仍保留「运营工作台」菜单（`module_market/dashboard/index`），但 dashboard 模块已删除；需决策「删除该菜单」或「基于新模型重建 dashboard」并同步 `ops/prod/init_ops_account.py` 的角色菜单绑定。

---

### 2026-10-28 — 市场模块重写终检：清理再生迁移 + 全量验证通过

#### 1. 原因

4 个并行 Agent 重写完成后，主 Agent 做最终校验与收尾。发现 dev autogen 在「收尾」记录删除 `2026_10_28_1158_8bbefa5ae3cb.py` 之后，又生成了新的根迁移 `2026_10_28_1248_5101bfa2ec1c.py`（`down_revision=None`，针对旧 schema 的增量），违反「versions/ 仅 __init__.py」口径。

#### 2. 修改内容

- 删除残留根迁移 `alembic/versions/2026_10_28_1248_5101bfa2ec1c.py`，恢复 versions/ 仅 `__init__.py`。

#### 3. 验证

- 后端：`ruff check app/modules/market/` All checks passed；`models.py` 16 模型 + `routers.py` 13 market Router 导入成功；`pytest tests/` **242 passed**。
- 前端 web：`pnpm ts:check` 通过（0 错误）。

#### 4. 剩余待办（仍待决策，与「收尾」记录一致）

- 小程序端 `api/module_market/index.ts` 旧模型类型清理（页面已用本地类型 + `as any` 绕过，无运行时影响）。
- `sys_menu.json`「运营工作台」菜单去留（dashboard 模块已删）。

---

### 2026-10-28 — 收尾两项待办落地：小程序端类型对齐 + 基于新模型重建 dashboard

#### 1. 原因

用户拍板两项待办：①小程序端旧模型类型残留顺手对齐；②「运营工作台」菜单不删，改为**基于新模型重建 dashboard 统计**。

#### 2. 小程序端类型对齐（frontend/app）

- `api/module_market/index.ts`：删除已废弃的 `TaskTypeItem`（旧 `market_task_type` 概念），`TaskItem`/`AssignmentItem` 对齐新 `TaskOutSchema`/`AssignmentOutSchema`（`task_no`/`project_id`/`template_id`/`template.config`/`name`/`assign_mode`，移除 `task_type`/`task_kind`/`unit_price`/`exec_qty`/`exec_time_*` 等已删概念）；`SubmissionItem` 补 `period`/`reviewer_id`/`ai_check_*`；新增 `TaskConfig`/`TaskCategoryItem`/`TaskTemplateItem` 三级类型（对齐 `config.py`/`form_schema.py`）。
- `constants/market.constant.ts`：删除 `TASK_KIND_MAP` 与 `taskKindText()`（引用已删的 `task_kind` 周期/定额概念，且全仓库无调用）。

#### 3. 基于新模型重建 dashboard

**后端（`app/modules/market/dashboard/` 五件套缺 crud/model，与旧版一致仅 schema/service/controller/__init__）**
- `schema.py`：`DashboardOverviewSchema` 将 `service_item_count` 替换为 `category_count`（一级分类）+ `template_count`（二级模板）。
- `service.py`：`overview()` 统计对象从旧 `ServiceItemModel` 改为新 `TaskCategoryModel`/`TaskTemplateModel`；其余（任务/成果/结算/项目/公司/机构）模型不变，均排除软删除。
- `controller.py`：`GET /market/dashboard/overview`，权限码 `module_market:dashboard:query` 不变。
- `routers.py`：重新注册 `DashboardRouter` 到 `/market` 分组（14 个 market Router）。

**前端 web**
- `api/module_market/dashboard.ts`：`DashboardOverview` 增 `category_count`/`template_count`、删 `service_item_count`。
- `views/module_market/dashboard/index.vue`：基础数据卡片由「服务项目」改为「一级分类 + 二级模板」两张；修复 `getOverview()` 取值（`res.data.data` 而非 `res.data`，响应拦截器返回完整 AxiosResponse）。

**测试**
- 新增 `tests/test_market_dashboard.py`（3 用例）：结构完整性、种子计数（一级分类 5 / 二级模板 22）、未认证 401。

**ops/prod**
- `init_ops_account.py` 无需改动：`ensure_dashboard_menu` 本就按 `component_path=module_market/dashboard/index` + `permission=module_market:dashboard:query` 建菜单并绑定 OPERATOR 角色，与重建后的模块/前端/菜单 seed 完全一致。

#### 4. 验证

- 后端：`ruff check` all passed；`pytest tests/` **245 passed**（+3 dashboard 用例）。
- 前端 web：`pnpm ts:check` 通过（0 错误）。

---

### 2026-10-28 — 任务目录：分类+模板合并为树形表格，form_schema 可视化编辑

#### 1. 原因

用户要求把「任务分类」「任务模板」两个页面合并为**树形结构**展示（分类父行 + 模板子行），并明确：任务模板的采集表单结构 `form_schema` 不能用 JSON 文本（运营人员太难用），改为可视化表单编辑器。

#### 2. 后端：新增分类树接口

- `task/schema.py`：新增 `TaskTemplateTreeOutSchema`（树子节点，**不含 category 嵌套**，避免 `MissingGreenlet` 懒加载冗余）+ `TaskCategoryTreeSchema`（继承分类出参 + `children: list[TaskTemplateTreeOutSchema]`）。
- `task/service.py`：`TaskCategoryService.tree()` 一次查全部分类（`order_by sort`）→ 逐个查其下模板（`search category_id`）→ 组装树；`_template_tree_out()` 用 `TaskConfig` 解析 config。
- `task/controller.py`：`GET /market/categories/tree`（权限码 `module_market:task_category:query`），**注册在 `/detail/{id}` 之前**避免 `/tree` 被路径参数路由吞掉。

#### 3. 前端：树形表格 + 可视化 form_schema

- `api/module_market/task-category.ts`：新增 `treeCategory()` + `TaskCategoryTreeItem`/`TaskTemplateTreeItem` 类型（`category_id` 必填，用于类型守卫）。
- 新建 `views/module_market/task-catalog/index.vue`：`FaTable` + `tree-props="{ children: 'children' }"` + `row-key="id"`（与菜单管理一致）；`useTableColumns` 定义列；操作列用 `isTemplate(row)`（`"category_id" in row` 类型守卫）区分父行（新增模板/编辑/删除分类）与子行（详情/编辑/删除模板）；分类表单走 `FaDialog`+`FaForm`，模板表单 `form_schema` 用 `FormSchemaEditor`（`v-model` 绑定 `FormSchemaField[]`，经 FaForm 具名 slot `#form_schema` 接入）。
- 删除旧 `views/module_market/task-category/index.vue` 与 `task-template/index.vue`（菜单已不再引用）。

#### 4. 菜单合并（`sql/sys_menu.json`）

- 「任务分类」「任务模板」两个 type 2 菜单合并为单个「任务目录」：`route_name=MarketTaskCatalog`、`route_path=task-catalog`、`component_path=module_market/task-catalog/index`；children 合并为 6 个按钮（新增分类/编辑分类/删除分类 + 新增模板/编辑模板/删除模板），权限码沿用原有两套不新增。
- 用 `json.load`+`json.dump(indent=4, ensure_ascii=False)` 精确改写，已 dry-run 验证与原文字节级一致（diff 0）。

#### 5. 验证

- 后端：`ruff check` all passed；`pytest tests/` **248 passed**（新增 `tests/test_market_task_catalog.py` 3 用例：树结构/归属、sort 排序、未认证 401）。
- 前端 web：`pnpm ts:check` 通过（0 错误）。

---

### 2026-10-28 — 重建 dev 库 + 开发环境初始化（站点/存储/账号）

#### 1. 原因

「任务目录」菜单合并改了 `sys_menu.json`（种子数据），seed 幂等（表已有数据则跳过），需重建数据库让新菜单生效；同时补齐开发环境的站点信息、对象存储、运营/C 端账号。

#### 2. 开发环境对象存储：dev 桶 + 独立子账号

- 开发环境 COS 用 `xfoxlab-dev-1516998879`（与生产 `foxwork-prod` 隔离）。
- `foxwork-infra`（独立 Terraform 仓库）`cam.tf` 新增 dev 子账号 `foxwork-dev`（UIN `100054319693`）+ 策略 `foxwork-dev-cos-access`（仅限 dev 桶）+ 绑定 + `tencentcloud_cam_access_key`（API 密钥进 state）；`outputs.tf` 输出 dev 密钥（sensitive）。
- `terraform apply` 用 `-target` 只落地 4 个 dev 资源，**跳过 `foxwork-prod` 桶的 `origin_domain_rules` 更新**（那是 ICP 备案遗留 drift，带上会因 `DomainAuditFailed` 失败）。

#### 3. 脚本与代码改动

- `ops/prod/init_storage_node.py`：新增 `COS_DESCRIPTION` 环境变量（原 description 硬编码「生产 COS 存储」，dev 复用需可配）；节点名 `COS_NODE_NAME` 已支持。
- dev 环境初始化执行顺序（均连 dev 库，`PYTHONPATH=backend` + `uv run`）：
  1. `init_site_info.py` → 站点/品牌参数 12 项
  2. `init_storage_node.py`（export `COS_*` 覆盖 ops/prod/.env 生产值：dev 桶 + foxwork-dev 密钥）→ 节点「COS 开发存储」is_default
  3. `init_ops_account.py` → OPERATOR 角色绑定 52 菜单（含新「任务目录」）、admin/operator 账号
  4. `init_c_account.py` → USER 角色 + 5 C 端菜单、user 账号

#### 4. 验证

- `task_storage_node`：`COS 开发存储`（xfoxlab-dev-1516998879 / ap-chongqing / is_default=t）。
- `sys_user`：super / admin（超管）/ operator / user 四账号就绪；`sys_menu` 含「任务目录」；`sys_param.sys_name`=玄狐科技。

---

### 2026-10-28 — 任务目录优化：树形展开修复 + 类型列中文 + form_schema 分组结构重构

#### 1. 原因

用户反馈任务目录 4 个优化点：① 树形展开异常（子项展开为空、收起子项误关父级）；② 表格「类型」列显示英文 `template`/`category`；③ 二级模板的一级分类显示编号而非名称；④ 采集表单结构出现「一、会议信息（必填）」式分节标题，且生成 JSON 应为分组结构。

#### 2. 改动

- **树形展开（row-key 冲突）**：`task-catalog/index.vue` 原 `row-key="id"`，一级分类与二级模板各自独立自增（分类 id=1..5、模板 id=1..22 撞车）导致 Element Plus 树形表格渲染错乱。改为 `loadTree` 给节点生成复合唯一 key（`category-{id}` / `template-{id}`），`row-key="_rowKey"`。
- **类型列中文**：formatter 返回「模板」/「分类」，删除未生效的 `status` 死配置。
- **一级分类名称**：后端 `TaskTemplateTreeOutSchema` 增 `category_name`，`tree()` 循环时填充；前端表格模板子行增「一级分类」列。
- **form_schema 结构重构**：由「扁平数组 + section 标记」改为「按分节分组的对象」`dict[分节名, dict[字段名, 字段定义]]`。字段定义去掉 `name`/`section`（由两层 key 表达）、`type=section` 取消；`table` 子列抽为 `FormSchemaColumn`。分节标题清洗（去「一、」序号与「（必填）」后缀）。

#### 3. 涉及文件

- 后端：`form_schema.py`（重写，新增 `FormSchemaColumn` + `FormSchema` 别名）、`config.py`（`form_schema` 类型改 dict）、`task/schema.py` + `task/service.py`（tree 补分类名）。
- 种子数据：`backend/sql/market_task_template.json` 22 个模板的 `form_schema` 全部迁移为分组结构（脚本一次性迁移）。
- 前端 web：`api/module_market/form-schema.ts`、`task-template.ts`、`task-category.ts`、`task.ts` 类型对齐；`form-schema-editor/index.vue` 重写为分组编辑；`task-catalog/index.vue` 适配。
- 小程序：`api/module_market/index.ts` 类型对齐；`submission-form/index.vue` 改为按分节嵌套遍历渲染，`form_data` 提交结构保持扁平不变（字段名仍作为 form_data 的 key）。

#### 4. 验证与注意

- `uv run` 验证 22 个模板 config 均能被新 `TaskConfig` 解析，分节标题已清洗（如「会议信息」「会议照片」）。
- 前端 web / 小程序 lint 零错误；后端改动无新增 lint 错误。
- 种子数据幂等（表已有数据则跳过），**需重建 dev 库**让新的 form_schema 分组结构生效（同「重建 dev 库」记录）。

---

### 2026-10-28 — form_schema 分节结构再调整：中文 key → code/name 分离

#### 原因

用户反馈分节名（中文）直接作为 form_schema 外层 key 不规范——展示名与标识耦合，将来分节改名/按分节落库/国际化都会变成负担。改为分节「英文 code + 中文 name」分离，与字段一致。

#### 改动

- `form_schema` 由 `dict[分节名, dict[字段名, 字段定义]]` 改为**有序分节数组** `list[FormSchemaSection]`，`FormSchemaSection = {code, name, fields}`。
- 后端 `form_schema.py` 新增 `FormSchemaSection`；`config.py` 的 `form_schema` 类型改为 `list[FormSchemaSection]`。
- 种子数据 22 个模板迁移：分节名映射为英文 code（「执行信息」→ execution_info、「会议信息」→ meeting_info 等，共 29 个分节名）。
- 前端 web / 小程序类型对齐；`form-schema-editor` 分节编辑增「分节标识 code + 分节名 name」两输入，code 校验字母开头、仅字母数字下划线、唯一。
- `form_data` 提交结构仍保持扁平不变（字段名英文作为 key，分节名不落库）。

#### 验证与注意

- 22 个模板均能被新 TaskConfig 解析，分节 code 唯一；前端 web / 小程序 lint 零错误。
- dev 库 `market_task_template` 表已 `TRUNCATE ... RESTART IDENTITY CASCADE`（级联清空引用它的 market_task/project_template/report/assignment/settlement/submission 等业务表）后重新播种。

---

### 2026-10-28 — 任务目录三级化：类型→类型→任务（按 Excel 清单重排）

#### 原因

用户指出任务目录的层级设计不对，应按 `docs/重庆-省平台-市场管理-项目任务清单.xlsx`：**TO B 的「类型」为一级，TO C 的「类型」为二级，TO C 的「任务」为三级**。原实现是两级（分类+模板），且「配送协调/库存盘点」等任务被埋在模板 `form_schema` 的 table 分节里。

#### 三级结构（权威 = Excel 清单）

- **一级（TO B 类型，6 个）**：商务管理服务、市场机构调研服务、访谈问卷调研服务、市场宣传服务、专项管理报告、会议服务（会议服务为 Excel 清单外、用户要求保留）。
- **二级（TO C 类型，18 个）**：如商务管理服务下等级医疗管理/基层医疗管理/民营医疗管理/零售药店管理/商业公司管理；市场档案信息调研（原 5 个档案调研模板合并为 1 个二级）。
- **三级（TO C 任务，51 个）**：如等级医疗管理下配送协调/库存盘点/价格核查/竞品调研/销售对账。

#### 数据模型

- 新增 `TaskItemModel`（`market_task_item` 表）：code、name、template_id（`uq(template_id, code)` 联合唯一）、config（`TaskItemConfig`）、sort、enabled。
- `TaskItemConfig = {columns, multi, unit, price, exec_standard, executor_requirement, max_per_month}`，`columns` 用扩展后的 `FormSchemaColumn`（完整类型含 radio + options）。
- `FormSchemaField.type` 去掉 `table`（多行子表提升为三级任务）；`TaskConfig` 去掉 `exec_modes`（问卷/宣传类的「医务人员/非医务人员调研」「户外/媒介宣传」提升为三级任务）。
- 任务三形态映射：商务类任务 = 原 table 分节（`multi=true`）；档案/问卷/宣传类任务 = 原字段组或 exec_modes（`multi=false`）。

#### 种子数据

- 迁移脚本从旧 22 模板生成三份：`market_task_category.json`（6）、`market_task_template.json`（18，form_schema 只留通用字段）、`market_task_item.json`（51，脚本一次性迁移）。

#### 前后端

- 后端：schema（TaskItem 系列 + tree 三级 + `TaskTemplateOutSchema.items`）、service（`TaskItemService` + tree 三级 + `_TASK_PRELOAD` 加 `template.items`）、controller（`/market/items` 路由，复用 task_template 权限）、crud、routers、initialize（prepare_init_models 加 TaskItemModel）。
- 前端 web：`task-catalog` 三级树 + 三级 CRUD（新增 `columns-editor.vue` 编辑任务采集字段）；`form-schema-editor` 去 table。
- 小程序：`submission-form` 消费「通用字段（form_schema）+ 三级任务（多行/单行）」；`form_data` 提交结构保持扁平。

#### 验证

- 22/18/51 三级数据入库正确；后端全量导入 + 路由注册通过；前端 web / 小程序 lint 零错误；dev 库已 DROP + CREATE 重建并重新播种 + 重跑 4 个环境初始化脚本（站点/存储/账号）。

---

### 2026-10-28 — 三级任务采集字段改回分节 form_schema（columns → FormSchemaSection 列表）

#### 1. 原因

用户反馈：三级任务（如「价格核查」）的采集表单应为**完整的分节结构**，自包含「执行信息」「价格核查」「管理核实」等分节，数据形态类似 `{"执行信息":{"区域":"xxx","医院等级":"xxx"},"价格核查":{}}`，且在**添加/编辑/详情展示**时都按分节分别添加与展示。此前「模板通用字段（form_schema）+ 任务专属字段（columns 数组）」拆成两块、且任务字段用扁平 `columns`（`FormSchemaColumn`，name 在列内）的方案不符合预期。

#### 2. 修改内容

**后端（权威定义源）**

- `form_schema.py`：删除 `FormSchemaColumn`（三级任务不再用数组形式，字段名与字段定义分离，统一用 `FormSchemaField`）。`FormSchemaField` 改为「二级模板 + 三级任务」共用定义。
- `config.py`：`TaskItemConfig.columns: list[FormSchemaColumn]` → `form_schema: list[FormSchemaSection]`（与 `TaskConfig.form_schema` 同构）；`multi` 保留（商务类任务多行子表 True / 档案·问卷·宣传类任务单行 False）。

**种子**

- `market_task_item.json` 51 条任务：`config.columns` 迁移为 `config.form_schema`，每条任务折叠为单个分节（`code`=任务 code、`name`=任务名、`fields`=列名 → `{label/type/required/placeholder/options}`）。已用 `TaskItemConfig.model_validate` 全量校验通过。

**前端 web**

- `form-schema.ts`：删除 `FormSchemaColumn`/`FormSchemaColumnType`，`FormSchema` 明确为「二级模板 + 三级任务共用」。
- `task-item.ts`：`TaskItemConfig.columns` → `form_schema: FormSchema`。
- `task-catalog/index.vue`：三级任务编辑由 `ColumnsEditor` 改用 `FormSchemaEditor`（分节可视化编辑）；详情展示由「任务采集字段（列数组）」改为「任务采集字段（分节，含分节列）」。
- 删除 `columns-editor.vue`（数组形式列编辑器，已被 FormSchemaEditor 取代）。

**前端 app（小程序）**

- `api/module_market/index.ts`：删除 `FormSchemaColumn`，`TaskItemConfig.columns` → `form_schema`。
- `submission-form/index.vue`：新增 `taskFields(task)` 把三级任务 `form_schema` 展平为字段列表；多行子表（multi）与单行字段组的列渲染由 `task.config.columns` 改为 `taskFields(task)`。

#### 3. 关键口径

- 三级任务 `form_schema` 与二级模板 `form_schema` **同构**（都是 `list[FormSchemaSection]`），字段名由分节 `fields` 的 key 表达，不再用 `FormSchemaColumn.name`。
- `multi` 仍为**任务级**开关：`multi=true` 的任务整体渲染为一张可重复的多行子表（其 form_schema 字段即为列），`multi=false` 渲染为单行字段组。当前种子每条任务仅一个分节，多分节 + multi 的组合语义（按分节粒度多行）未展开，留待后续明确。

#### 4. 验证

- 后端：`ruff check app/modules/market/` All checks passed；`app.api.v1.routers` 15 个 market Router 导入成功；51 条种子 `TaskItemConfig.model_validate` 全量通过。
- 前端 web：`pnpm ts:check` 通过（0 错误）；小程序：`pnpm type-check` 通过（0 错误）。

---

### 2026-10-28 — form_schema 加回分节内多行子表（type=table）+ form_data 按分节嵌套

#### 1. 原因

用户给出真实采集表（重庆省平台「价格核查」表单）示例图：一张表单 = 三个分节（一、执行信息（必填）键值对字段；二、价格核查（必填）——**多行明细子表**（产品名称/规格/生产企业/挂网价/采购价/销售价）+ 表后单字段（异常说明）；三、管理核实（必填）——打卡照片等）。即分节内可「键值对字段 + 多行子表 + 单字段」混排。上一轮把多行子表整体提升为三级任务（任务级 `multi` 开关）的方案仍不匹配；且成果详情按「通用采集字段（模板级）」扁平表格展示（带分节列）被用户划掉，要求按分节块展示。

#### 2. 修改内容

**后端（权威定义源）**

- `form_schema.py`：`FormSchemaField.type` 加回 `"table"`（多行子表），新增 `columns: list[FormSchemaColumn] | None`（子列定义，`FormSchemaColumn` 回归，子列类型不允许再嵌套 table）；`FormSchemaSection` 新增 `required: bool`（分节必填标记，展示「(必填)」）。
- `config.py`：`TaskItemConfig` 移除 `multi`（多行语义由分节内 table 字段表达，任务级开关无法表达「子表 + 表后单字段」混排）。

**种子（脚本一次性迁移后删除）**

- `market_task_item.json` 51 条：原平铺字段按 `multi` 拆分——`multi=true` 的商务类任务折叠为分节内 `type=table` 字段（字段名=分节 code、label=分节名、columns=原子段）；`multi=false` 保持平铺；全部分节补 `required: true`；删除 `config.multi`。
- `market_task_template.json` 18 条：全部分节补 `required: true`。

**前端 web**

- `form-schema.ts`：`FormSchemaColumn` 回归、`FormSchemaFieldType` 加 `table`、`FormSchemaField.columns?`、`FormSchemaSection.required?`。
- `form-schema-editor/index.vue`：类型下拉加回「多行子表」；`type=table` 时展示子列编辑器（列显示名/列标识/类型/必填，增删、查重、防嵌套）；分节编辑加「是否必填」开关；类型列/选项列对 table 展示「子表 N 列：…」摘要；示例更新为「执行信息 + 价格核查(子表+异常说明) + 管理核实」。
- `task-item.ts` / `task-catalog/index.vue`：`TaskItemConfig` 去 `multi`，编辑表单去「是否多行」开关；三级任务详情由「模板通用字段 + 任务采集字段两张扁平表」改为**按分节块展示**（模板通用分节 + 任务自有分节按序合并，每分节一个带标题块 + 字段表格，table 字段显示子列摘要）。

**前端 app（小程序）**

- `api/module_market/index.ts`：类型同 web 对齐（`FormSchemaColumn` 回归、table 类型、section required、去 multi）。
- `submission-form/index.vue`：重构为**分节渲染 + 分节嵌套提交**——`allSections` = 模板通用分节 + 全部三级任务分节按序合并；`form_data` 改为 `{分节code: {字段名: 值}}`，其中 `type=table` 字段值为 `list[dict[子列名, 值]]`（行可增删）；必填校验覆盖单值必填字段与子表必填列；分节标题展示「（必填）」。

#### 3. 关键口径

- **form_data 按分节 code 嵌套落库**：`{"execution_info": {"region": "..."}, "price_check": {"price_check": [{"product_name": "..."}]}, "management_verification": {"door_photo": "url"}}`——对齐用户示例 `{"执行信息":{...},"价格核查":{...}}`（key 用分节英文 code）。多行子表数据挂在「分节内 table 字段名」下。
- **多行子表 = 分节内 `type=table` 字段**（columns 子列），不再是任务级 `multi` 开关；分节内可与单值字段混排（如价格明细表 + 异常说明）。
- 展示口径：模板 `form_schema`（执行信息/管理核实等通用分节）+ 任务 `form_schema`（任务专属分节）按序合并为一个分节表单，web 详情、web 编辑器、C 端提交页三处一致。

#### 4. 验证

- 后端：`ruff check app/modules/market/` All checks passed；15 market Router 导入成功；18 模板 + 51 任务种子全量 `model_validate` 通过。
- 前端 web：`pnpm ts:check` 通过；小程序：`pnpm type-check` 通过。

#### 5. 遗漏修复：数据库未重播种导致任务分节「缺失」

- 现象：用户反馈「价格核查里缺少价格核查、配送协调里缺少配送协调」——详情只显示模板通用分节（执行信息/管理核实），任务自有分节整个不见。
- 根因：种子初始化 `__init_data` 幂等（表已有数据即整体跳过）。改了 `market_task_item.json` 后，库内 `market_task_item.config` 仍是**最旧的 `{multi, columns}` 结构**，后端 `TaskItemConfig.model_validate` 解析时 `form_schema` 取默认空列表，任务分节因此「缺失」。
- 处理：`TRUNCATE TABLE market_task_item, market_task_template RESTART IDENTITY CASCADE`（级联清空引用它们的业务数据）后按新种子重播种 18 模板 + 51 任务，验证 `price_check` 的 config 已为 `form_schema[分节 price_check → 子表 price_check(columns)]`。
- 教训：凡改 market 域种子文件（含 form_schema 结构迁移），**必须同时清库重播种**，否则幂等跳过导致「代码改了、库还是旧的」的假象（与踩坑 6 同源）。

#### 6. 落地一键重置脚本

- 新增 `app/scripts/reseed_market.py`：动态收集全部 `market_` 表（来自 `MappedBase.metadata`），`TRUNCATE ... RESTART IDENTITY CASCADE` 清空，再按依赖顺序重播种「任务分类 → 任务模板 → 三级任务」三张种子表；非 DEV 环境需 `--force`。
- 用法（backend 目录）：`PYTHONPATH=. uv run python -m app.scripts.reseed_market`。实测清空 17 张表、重播种 6 分类 + 18 模板 + 51 任务，`price_check`/`grade_hospital_manage` 种子结构验证正确。

#### 7. 执行信息/管理核实/基本信息不是模板「通用节点」

- 现象：用户明确纠正「执行信息/管理核实不是通用节点，是这几个任务碰巧都有而已」。此前把 `execution_info`/`management_verification`（管理类）与 `basic_profile`（调研类）当成模板级 `TaskConfig.form_schema` 的「通用采集字段」，三级任务通过 `TaskItemService._template_sections` 继承/合并来获得，属错误抽象。
- 处理：
  1. 种子 `market_task_template.json`：清空管理类（category 1，5 个）与调研类（category 3，7 个）模板的 `form_schema`；仅「无三级任务的叶子模板」（category 2/4/6：档案调研、宣传、科普、3 个会议活动）保留 `form_schema`。
  2. `service.py`：删除 `TaskItemService` 的 `_template_sections` 继承逻辑，三级任务完全自包含、不从模板继承分节。
  3. `config.py` / 前端 `task-catalog`：`TaskConfig.form_schema` 口径改为「仅无三级任务的叶子模板使用」，清除「通用采集字段」「含继承自模板的通用分节」等误导文案。
- 口径：**凡有三级任务的模板不承载 `form_schema`，表单结构完全由三级任务自包含**；详情/编辑只渲染任务自身 `form_schema`。

---

### 2026-10-29 — 市场模块 code 改「类型前缀+数字」自动编号（并发/分布式安全）

#### 1. 原因

用户要求：市场管理模块所有业务实体的 `code`（一级分类/二级模板/三级任务/医药公司/项目）由「手填英文编码」改为「数字编号」，页面添加时不再让用户输入，由后端按规则自动生成；并特别提醒**注意并发冲突与分布式冲突**。任务实例流水号 `task_no` 一并纳入。

#### 2. 编号规则

- 格式：`{类型前缀}-{NNN}`，序号从 1 起独立递增，补齐到至少 4 位（超 9999 自动扩展，后续按需求可再调宽）。
- 前缀映射：`CAT`(一级分类) / `TPL`(二级模板) / `ITEM`(三级任务) / `CO`(医药公司) / `PRJ`(项目) / `TK`(任务实例 task_no)。
- 生成：后端创建时自动生成，前端不提供输入；编号一旦生成不可修改。

#### 3. 修改内容

**后端**
- 新增 `app/modules/market/numbering.py`：`NumberPrefix` 前缀常量 + `MarketNumberCounterModel` 计数器表（`market_number_counter`，`prefix` 主键 + `current_value` BigInteger）+ `next_code` 原子生成 + `sync_counter` seed 对齐。
- `models.py` 注册 `MarketNumberCounterModel`。
- 模型：`TaskItemModel.code` 由「模板内唯一 `UniqueConstraint(template_id, code)`」改为全局 `unique=True, index=True`；`CompanyModel.code` 由可空改非空 `unique=True`；`code`/`task_no` 注释「编码/流水号」统一改「编号」。
- Schema：各 `CreateSchema`/`UpdateSchema` 移除 `code`/`task_no` 字段（编号不可改、前端不传）；`OutSchema`/`QueryParam` 保留用于展示与搜索。
- Service：`create` 时调 `next_code` 自动生成编号，移除所有 code/task_no 重复检查；`ProjectService.publish` 的 task_no 由 `TK{period}-{uuid8}` 改为 `next_code(NumberPrefix.TASK)`。
- 种子 JSON：6 分类 / 18 模板 / 51 任务的**顶层** code 重写为 `CAT-0001..`/`TPL-0001..`/`ITEM-0001..`（`config.form_schema` 分节 code 不动）。
- `reseed_market.py` / `initialize.py`：seed 后调 `sync_counter` 对齐计数器。

**前端 web**
- `api/module_market` 5 个 Form 类型移除 `code` 字段（Table/PageQuery 保留）。
- `company`/`project`/`task-catalog` 三页移除「编码」输入框与必填校验；列表/详情/搜索栏 label「编码」→「编号」；`task` 页 task_no label「任务号」→「任务编号」。
- 测试 `test_market_company_institution.py` 移除创建公司时传 `code`。

#### 4. 关键口径（并发/分布式安全）

- 序号取自 `market_number_counter` 计数器表，用**单条 `INSERT ... ON CONFLICT DO UPDATE ... RETURNING`** 原子自增：PG 主键冲突 + 行级锁保证并发事务与多实例（分布式）下同一前缀序号严格递增、不重复；事务回滚时计数一并回滚，序号不产生空洞。
- 计数器表是普通 ORM 表，随 `create_all`/autogen 自动建表，无需独立 PG SEQUENCE。
- **seed 预置编号后必须 `sync_counter`**（`GREATEST` 只增不减）对齐计数器，否则 `TRUNCATE`/reseed 后计数器空，下次自动编号会与预置编号撞唯一约束。

#### 5. 验证

- 后端：`ruff check app/modules/market/ app/scripts/reseed_market.py app/scripts/initialize.py` All checks passed；`numbering`/`initialize`/`reseed_market` 导入成功。
- 前端 web：read_lints 零错误。

---

### 2026-10-29 — 机构管理数据来源纠正：C 端提交成果归集，运营端去除手动新增

#### 1. 原因

用户纠正：市场管理里「机构管理」及医院相关数据**不是运营人员添加的**，而是 **C 端人员提交的成果数据归集**而来。原实现机构（`market_institution`，含等级医院/基层医疗/民营医疗/零售药店/商业公司）由运营端手动 CRUD，C 端提交成果时从运营预置的机构列表「选择」，方向反了。

#### 2. 修改内容

**后端**
- `institution/schema.py`：删除 `InstitutionCreateSchema`（机构不再由运营端创建）。
- `institution/crud.py`：`InstitutionCRUD` 泛型 CreateSchemaType 改为 `dict[str, Any]`（归集创建走 dict）。
- `institution/service.py`：删除 `create` 方法；新增 `collect`（按名称归集：同名复用、否则创建）、`extract_institution_info`（从 form_data 提取机构名称/区域/等级）、`map_institution_type`（二级模板名 → 机构类型）。
- `institution/controller.py`：删除 `POST /institutions/create` 路由。
- `task/service.py` `SubmissionService.create`：采集对象类型以模板 `TaskConfig.subject_type` 为准；对象为机构时从 form_data 归集机构并回填 `institution_id`。

**前端 web**
- `institution/index.vue`：去掉「新增」按钮与 `createApi`，仅保留查询/编辑/删除（运营可修正归集来的机构信息）。
- `api/module_market/institution.ts`：删除 `createInstitution`。

**前端 app（小程序）**
- `submission-form/index.vue`：移除「机构选择器」，机构信息由采集表单字段提交、后端归集。
- `api/module_market/index.ts`：删除 `InstitutionItem`/`getInstitutions`。

**测试**
- `test_market_company_institution.py`：`TestInstitution` 移除 `test_create`，新增 `test_create_route_removed`（验证 POST /institutions/create 404），其余用例改「同步 Session 直接落库」准备机构数据。
- 新增 `test_market_institution_collect.py`（7 用例）：覆盖 `extract_institution_info` 与 `map_institution_type`。

#### 3. 关键口径

- **机构类型由任务模板权威映射**：`map_institution_type` 按二级模板名映射（等级医疗管理→grade_hospital 等）；宣传/科普/会议类模板采集对象非机构主数据，不归集。
- **机构名称字段候选**：`hospital_name`（商务类）/ `org_name`（档案调研类）/ `institution_name`，跨分节按字段名匹配，兼容不同任务的采集表单。
- **查重维度 = 机构名称**：同名复用、否则创建；归集时机为提交成果即归集（草稿也归集）。
- **运营端权限**：仅保留「编辑/删除」修正能力；`module_market:institution:create` 权限码保留给「图片归集」页新增图片按钮复用，菜单 seed 未动（避免重建库）。

#### 4. 验证

- `ruff check`：institution/task 模块 + 测试 All checks passed。
- `pytest`：market 域 4 个测试文件 29 passed + 新增归集单元 7 passed。
- 模块导入正常（无循环导入）。

---

### 2026-10-29 — 项目管理「添加项目」表单三处体验优化（委托方可输入 / 周期限定 / 关联模板树形级联）

#### 1. 原因

用户反馈「项目管理 → 添加项目」三个字段体验问题：① 委托方只能选、列表为空时无法选择；② 周期自由文本输入、系统无法校验；③ 关联模板平铺下拉、数量多了不好选。要求：委托方支持输入、周期限定、关联模板改为树形 + 级联选择 + 多选 + 筛选。

#### 2. 修改内容

**后端（`app/modules/market/project/schema.py`）**
- `ProjectCreateSchema.period` / `ProjectUpdateSchema.period` 由自由文本改为 `pattern=r"^\d{4}$"`（项目周期 = 年份，如 `2026`），与「任务发布有周期（如一年）」口径一致；description 同步改「项目周期年份」。

**前端 web（`views/module_market/project/index.vue` + `api/module_market/project.ts`）**
- **委托方支持输入**：`company_id` 下拉改为 `el-select` `filterable + allow-create + default-first-option`；`ProjectForm.company_id` 类型放宽为 `number | string`（新增时输入新公司名为 string）。提交前 `normalizeCompanyId()` 把 string 名称转公司 id——同名复用 `companyOptions`、否则 `CompanyAPI.createCompany({ name })` 自动创建并回填 `company_id` + 追加进下拉选项。委托方为空时也能直接输入公司名创建。
- **周期限定**：表单与搜索栏的周期均由 `input` 改为 `FaDatePicker`（`type="year"`，`value-format="YYYY"`），只能选年份、无法乱输；rules 文案改「请选择项目周期年份」。
- **关联模板树形级联多选筛选**：数据源由平铺 `TaskTemplateAPI.listTemplate` 改为 `TaskCategoryAPI.treeCategory()`（一级分类 → 二级模板树）；下拉由 `select` 改为 `el-tree-select`（`multiple + filterable + collapse-tags`，未设 `check-strictly` 即父子级联——勾选分类全选其下模板）；详情模板名 `templateMap` 同步从树构建。

#### 3. 关键口径 / 踩坑

1. **分类 id 与模板 id 各自自增会撞车，树形选择必须用「负值 value + 复合 nodeKey」**
   - 现象：一级分类（`market_task_category`）与二级模板（`market_task_template`）各自独立自增（分类 id 1..6、模板 id 1..22），若直接用 `id` 作树节点 value / node-key，el-tree-select 回显 `template_ids=[3]` 会同时匹配到「分类 id=3」与「模板 id=3」，导致勾选错乱（与踩坑 15、task-catalog 的 row-key 冲突同源）。
   - 处理：`buildTemplateTree()` 给分类节点 `value = -id`（负数）、模板节点 `value = id`（正数），node-key 用字符串复合 `category-{id}` / `template-{id}`；空分类 `disabled=true` 防勾选。这样正/负值天然隔离，模板正数 id 直接作为 `template_ids` 提交与回显，无需二次映射。
   - 结论：凡「多张自增表拼一棵树」的树形选择（tree-select / cascader），节点 value 与 node-key 都不能直接用各自的 `id`，须用「类型前缀 + 复合 key」或「符号/偏移区隔」保证全局唯一。

#### 4. 验证

- 后端 `uv run ruff check app/modules/market/project/schema.py` All checks passed。
- 前端 `pnpm ts:check` 通过（0 错误）。

---

### 2026-10-29 — 项目管理「周期」改为截止日期（DateStr 类型 + 快捷选项）

#### 1. 原因

用户纠正上一轮「周期限定为年份（YYYY）」的方案：年份仍不满足，要求「周期」改为**具体截止日期**，选择框支持快捷选「一个月 / 三个月 / 六个月 / 一年」，也可手选具体日期；并质疑字段类型为何是 `str`——截止日期应是日期类型而非字符串。

#### 2. 修改内容

**后端**
- `project/schema.py`：`ProjectOutSchema/CreateSchema/UpdateSchema.period` 由 `str`（上一轮 `pattern=r"^\d{4}$"`）改为项目标准日期类型 `DateStr`（`app.core.validator.DateStr`：内部 `date`、JSON 序列化 "YYYY-MM-DD"、非法日期自动拒绝）。
- `project/model.py` / `task/model.py`：`period` 列由 `String(16)` 改为 `Date`（`Mapped[date]`），注释改「截止日期」。
- `task/schema.py`：`TaskOutSchema/CreateSchema/UpdateSchema.period` 同步改 `DateStr`（任务截止日期继承项目截止日期）。
- 搜索参数 `ProjectQueryParam/TaskQueryParam.period` 仍为 `str`（搜索入参走字符串，`q="eq"` 精确匹配日期列）。

**前端 web（`views/module_market/project/index.vue` + `api/module_market/project.ts`）**
- 表单「周期」→「截止日期」：FaForm 具名 slot `#period` 渲染 `el-date-picker`（`type=date` + `value-format="YYYY-MM-DD"`），配 `shortcuts`「一个月/三个月/六个月/一年」（dayjs 相对今天推算），也可手选具体日期。
- 搜索栏「周期」→「截止日期」日期选择器；表格列/详情/校验文案同步「截止日期」。

#### 3. 关键口径

- **日期字段统一用项目 `DateStr` 类型**（内部 `date`、序列化字符串），不要用 `str + pattern` 正则硬校；模型列对应 `Date` 而非 `String`。
- 上一轮「年份限定」方案作废：周期语义 = 项目/任务截止日期（`YYYY-MM-DD`），与报告/成果的「月份」（`YYYY-MM`）字段解耦、互不影响。

#### 4. 验证

- 后端 `ruff check` All checks passed；`ProjectCreateSchema(period='2026-12-31')` 解析为 `date`，`'2026-13-45'` 被拒绝。
- market 域 5 个测试文件 36 passed；前端 `pnpm ts:check` 通过（0 错误）。

---

### 2026-10-29 — 数据库迁移：project/task 的 period 由 VARCHAR 改为 DATE

#### 1. 背景

本轮把 `market_project.period` / `market_task.period` 由 `String(16)` 改为 `Date`（截止日期语义）。本地 dev 库（OrbStack PG）为存量库，需执行迁移对齐。

#### 2. 执行

- 确认库状态：`alembic_version=ed9e3a008acc`，两表 `period` 仍为 `varchar`，且均无数据。
- 修复 autogen 产物缺 `USING`：给 `416002c63901`（project.period）与 `837416e7827d`（task.period）的 `alter_column` 补 `postgresql_using='period::date'`（详见踩坑 18）。
- `uv run python main.py upgrade --env=dev` 应用全部迁移，最终 `alembic_version=837416e7827d`。
- 复核：`information_schema.columns` 显示 `market_project.period`、`market_task.period` 均为 `date`。

#### 3. 验证

- `market_project.period` / `market_task.period` 列类型已变为 `date`，与 model `Mapped[date]` 一致。
- 迁移链线性（ed9e3a008acc → 416002c63901 → 837416e7827d），无 multiple heads。

---

### 2026-10-29 — 项目管理「关联模板」修复搜索过滤 + 父级选择

#### 1. 原因

用户反馈「添加项目」的关联模板：① 无搜索过滤；② 无法选择父级（一级分类）。根因是上一版用 `FaForm type="treeselect"` 且给 el-tree-select 配了 `props.value`，用法错误（详见踩坑 19）。

#### 2. 实现

- 关联模板由 `formItems type="treeselect"` 改为 FaForm 具名 slot `#template_ids` 直接渲染 `ElTreeSelect`：`multiple + filterable + collapse-tags + clearable + node-key="id"` + 自定义 `filter-node-method`（按 name 过滤）。
- `TemplateTreeNode` 接口改为 `{ id, name, disabled?, children? }`；`buildTemplateTree` 用「分类 `id=-cat.id`（负数）/ 模板 `id=tpl.id`（正数）」保证 node-key 全局唯一，模板正数 id 即提交的 `template_ids`。
- 父级选择靠 `check-strictly` 默认 false（父子联动）：勾选一级分类级联全选其下模板，v-model 只输出叶子（模板正数 id）。

#### 3. 验证

- 前端 `pnpm ts:check` 通过（0 错误）。

---

### 2026-10-29 — 修复定向分派任务发布未指定分派人员导致 C 端不可见

#### 1. 原因

用户反馈：任务管理里「定向分派」任务必须指定分派人员，但现状是定向分派任务发布时无分派人员入口，发布后没有任何分派记录——C 端任务大厅（只展示 `assign_mode=open` 任务）看不到、被分派人的「我的任务」（依赖 `market_assignment` 记录）也看不到，任务等于「发不出去」。

附带缺陷：分派页「批量分派」接口前后端不匹配（前端传 `user_ids` 数组、后端 `AssignmentCreateSchema` 只有单 `user_id`），批量分派会 422。

#### 2. 修改内容

**后端（`app/modules/market/task/`）**

- `schema.py`：`AssignmentCreateSchema` 由单 `user_id` 改为 `user_ids: list[int]`（批量）；新增 `TaskPublishSchema`（`assignee_ids: list[int] | None`）。
- `service.py`：
  - `TaskService.publish(id, assignee_ids)`：`direct` 任务必须传 `assignee_ids`，否则报错「定向分派任务必须指定分派人员」；发布时调用 `AssignmentService.batch_assign` 批量创建分派（跳过已分派用户）；`open` 任务忽略 `assignee_ids` 直接发布。
  - `AssignmentService`：新增 `batch_assign`（用户去重、跳过已分派），`create` 改为批量返回 `list[AssignmentOutSchema]`；`detail/page/my_assignments` 补 `_ASSIGNMENT_PRELOAD` 预加载任务链（此前 `_ASSIGNMENT_PRELOAD` 是死代码，序列化 `task` 会触发异步懒加载 MissingGreenlet）。
- `controller.py`：`publish/{id}` 接受 `TaskPublishSchema` body；`assignments/create` 响应改为 `list[AssignmentOutSchema]`。

**前端 web**

- `api/module_market/task.ts`：`publishTask(id, body)` 支持 `assignee_ids`。
- `views/module_market/task/index.vue`：发布时 `open` 任务直接发布；`direct` 任务弹窗多选分派人员后发布（`userOptions` 从 `UserAPI.listUser` 加载）。

**测试**

- 新增 `tests/test_market_task_publish.py`（3 用例）：direct 不带分派人员被拒、direct 带分派人员发布并生成 assignment、open 无需分派人员可发布。

#### 3. 验证

- 后端 `pytest tests/test_market_*.py` 39 passed；`ruff check` all passed。
- 前端 `pnpm ts:check`、`pnpm eslint` 均 0 错误。

#### 4. 注意

- 项目发布（`ProjectService.publish`）批量生成的 `market_task` 硬编码 `assign_mode="direct"`，因此项目级发布后还需逐个任务在「任务管理」里指定分派人员再发布；公开大厅任务需单独 `POST /market/tasks/create` 用 `assign_mode=open` 创建（项目发布流程暂未提供 open 选项）。

---

### 2026-10-29 — 市场管理创建表单草稿缓存（误关恢复）

#### 1. 原因

用户要求：市场管理里所有「新建/创建/添加」表单都要有本地草稿缓存——填写一半误关窗口后重开，之前填写的内容自动恢复，不用重新输入；**编辑表单不缓存**（由详情接口回填）。

#### 2. 修改内容

**通用工具与 hook**

- 新增 `frontend/web/src/utils/form-draft.ts`：
  - `loadFormDraft/saveFormDraft/clearFormDraft`：localStorage 读写（统一 `market-form-draft:` 前缀，保存时剔除 `id`）。
- 新增 `frontend/web/src/hooks/core/useFormDraft.ts`：
  - `useFormDraft`：面向「自管对话框」手写表单的组合式函数——`watch` 监听关闭自动保存草稿、`openCreate` 打开恢复（支持 preset 预填），页面只需提交成功后 `done()`。
- `hooks/core/useCrudForm.ts`：新增可选 `cacheKey` 参数。提供后自动启用「新增表单」草稿缓存——打开 create 时恢复草稿、关闭 create 时保存草稿、提交成功清草稿、页面卸载兜底保存；编辑/详情表单不缓存。

**接入页面**

- `useCrudForm` 页面（加 `cacheKey`）：company / project / institution-image / task。
- 手写表单页面（用 `useFormDraft`）：task-catalog 的「一级分类/二级模板/三级任务」三个表单、payout 的「新增发放额度配置」、settlement 的「归集结算」、report 的「生成报告」、assignment 的「批量分派」。
- 未接入：institution（无新增，仅编辑）、submission（仅审核）、dashboard/import（无表单）。

#### 3. 关键口径

- 缓存范围严格限定「创建态」：`useCrudForm` 仅在 `type === "create"` 时读写草稿；手写页面用 `useFormDraft` 的 `mode`（create/update）区分，仅新建态读写草稿。
- 提交成功后必须 `done()`/`clearFormDraft` 清草稿并跳过本次关闭保存，否则 `visible=false` 触发的关闭回调会再次写回草稿。

#### 4. 验证

- `pnpm ts:check` 通过（0 错误）。
- `pnpm eslint`：本次改动文件无新增错误；顺手清理了 3 处历史遗留 unused 告警（`institution-image` 的 `selectedRows`、`task-catalog` 的 `FormSchemaColumn`/`columnChecks`）。

---

### 2026-10-29 — 任务与任务分派合并（分派内嵌任务详情抽屉）

#### 1. 原因

用户反馈「任务管理里的任务和任务分派太隔离」——两个平级菜单、两个独立页面，运营分派时要在「任务」与「任务分派」页之间来回跳。数据上 `market_assignment` 本就是 `market_task` 的接收记录（`task_id` 外键），拆成平级页面割裂感强。方案（用户拍板）：以任务为中心，分派作为任务的子明细内嵌；不保留全局分派记录视图。

#### 2. 修改内容

**后端**
- `task/schema.py`：`TaskOutSchema` 新增 `assignment_count`（已分派/接收人数，列表聚合字段）。
- `task/service.py`：`TaskService.page` 查询后按 `task_id` 分组 `COUNT` 回填 `assignment_count`（一次 `GROUP BY`，非 N+1）。

**前端**
- `views/module_market/task/index.vue`：新增「接收人数」列、行操作「分派」；新增 `FaDrawer` 详情抽屉（任务信息 `FaDescriptions` + 分派明细 `ElTable`），抽屉内支持「添加分派」（`assignment:create`）与「撤销」（`assignment:delete`，仅 PENDING）；`onMounted` 补载 `market_assignment_status` 字典。
- `api/module_market/task.ts`：`TaskTable` 增加 `assignment_count` 类型。
- 删除 `views/module_market/assignment/index.vue`（`assignment.ts` API 保留，供抽屉调用）。

**菜单**
- `sql/sys_menu.json`：删除「任务分派」二级菜单，其 `assignment:create/update/delete` 三个权限点并入「任务」菜单（重命名「分派/修改分派/撤销分派」），RBAC 授权能力不丢失。

#### 3. 关键口径

- 分派明细按 `task_id` 过滤查询（`AssignmentAPI.listAssignment({ task_id })`），抽屉内一次性拉取（`page_size=100`）。
- 分派来源 `assigned/claimed` 是本地常量（无字典），状态走 `market_assignment_status` 字典。
- 菜单是 `sys_menu.json` 种子数据，改动后需重建库（或 reseed）才生效；本次直接 `DROP DATABASE + CREATE DATABASE` 重建，后端启动 `init_db` 全量 seed。

#### 4. 验证

- 前端 `task/index.vue`、`task.ts` 零 lint 错误；`sys_menu.json` JSON 语法校验通过。
- 重建库后：`sys_menu` 已无 `MarketAssignment` 路由，「任务」菜单下 7 个按钮权限点（含 3 个 assignment 权限）正确；`market_assignment_status` 六态齐全；后端启动 `postgres/Redis/调度器` 均就绪。

---

### 2026-10-29 — 修正：任务默认分配方式改为公开大厅（direct → open）

#### 1. 原因

用户反馈「项目发布后任务的默认分配方式应该是公开大厅，不应该是定向分派」。原默认值 `direct` 导致新建任务/发布项目生成的批量任务默认走定向分派，发布时还强制要求指定分派人员，不符合「公开大厅接单」的主流场景。

#### 2. 修改内容

- `task/schema.py`：`TaskOutSchema` / `TaskCreateSchema` 的 `assign_mode` 默认值 `direct` → `open`。
- `task/model.py`：`TaskModel.assign_mode` 列默认值 `direct` → `open`。
- `project/service.py`：`publish` 发布项目批量生成任务时 `assign_mode="open"`（原 `"direct"`）。
- 前端 `task/index.vue`：新增任务表单 `assign_mode` 初始值 `direct` → `open`。
- 测试 `test_market_task_publish.py`：direct 流程改为显式创建任务（新增 `_create_task` helper），新增 `test_publish_project_creates_open_task` 验证发布项目默认生成 open 任务。

#### 3. 关键口径

- 纯 Python/前端默认值改动，不涉及 DB schema（`default=` 非 `server_default`），**无需重建数据库**，后端 reload 自动生效。

---

### 2026-10-29 — 任务批量分配与批量发布

#### 1. 原因

运营在任务列表需一次性处理多个任务：批量给多个任务分派执行人、批量发布草稿任务，避免逐条操作。方案（用户拍板）：批量分配 = 多任务 × 多用户交叉分派；批量发布 = 统一弹窗选分派人员（公开大厅任务忽略，定向分派任务用它建分派）。

#### 2. 修改内容

**后端**
- `task/schema.py`：新增 `TaskBatchPublishSchema`（ids + assignee_ids）、`TaskBatchPublishResultSchema`（published + failed）、`AssignmentBatchCreateSchema`（task_ids + user_ids）。
- `task/service.py`：`TaskService.batch_publish`（逐个 publish，单任务失败不影响其余，返回成功/失败明细）；`AssignmentService.batch_assign_multi`（多任务 × 多用户交叉，跳过已存在，返回新建数量）。
- `task/controller.py`：新增 `POST /market/tasks/batch-publish`（`task:publish` 权限）、`POST /market/assignments/batch-create`（`assignment:create` 权限）。

**前端**
- `api/module_market/task.ts`：新增 `batchPublishTask` + `TaskBatchPublishResult`。
- `api/module_market/assignment.ts`：新增 `batchCreateAssignment`。
- `views/module_market/task/index.vue`：工具栏新增「批量分配」「批量发布」按钮（勾选后出现）；新增两个弹窗：批量分配（选多用户）、批量发布（含 direct 任务时选分派人员，全 open 直接发布）。

#### 3. 关键口径

- 批量发布逐个调用 `publish`，部分失败不阻断整体，返回 `{published, failed[]}` 供前端提示。
- 批量分配复用 `batch_assign`（单任务多用户），外层遍历 task_ids 去重。
- 权限沿用既有 `task:publish` / `assignment:create`，无新增权限点。

#### 4. 验证

- 后端三个文件 lint 无新增错误（仅既有 implicit-import 提示）；路由已注册（openapi 含 `/market/tasks/batch-publish`、`/market/assignments/batch-create`）；reload 无报错、无模型变更迁移。
- 前端零 lint 错误。

---

### 2026-10-29 — 修正：定向分派时自动把任务分配方式改为定向

#### 1. 原因

用户反馈「批量分配（及抽屉添加分派）后任务仍是公开大厅模式」——`batch_assign` 只创建分派记录，未回写任务 `assign_mode`，导致「已指定执行人但任务仍可被大厅接单」的矛盾状态。

#### 2. 修改内容

- `task/service.py`：`AssignmentService.batch_assign` 在运营定向分派（`source=assigned`）时，自动将任务 `assign_mode` 改为 `direct`（幂等）。大厅接单 `claim` 不走此方法，不受影响。
- 测试 `test_market_task_publish.py`：新增 `test_assign_open_task_switches_to_direct`，验证 open 任务分派后变为 direct。

#### 3. 关键口径

- 改 `assign_mode` 的时机统一收敛在 `batch_assign`，覆盖单任务分派（`create`）、批量分配（`batch_assign_multi`）、发布定向任务（`publish`）三类场景；仅 `source=assigned` 时改写，`claimed`（大厅接单）不改。

---

## 四、踩坑记录（长期有效）

> 这些坑已用时间验证，后续开发遇到相关场景请直接参考，不要重新踩。

1. **改 SQLAlchemy model 后手写 alembic migration → multiple heads**（2026-10-22）
   - 现象：手写 migration 后，dev autogen 在测试运行时又基于旧 head 自动生成一个 migration，两个都指向同一父 revision，`upgrade/stamp head` 抛 `CommandError: Multiple heads`，全部测试 ERROR。
   - 结论：**改 model 不要手写 migration**。空库测试直接跑即可；存量库升级靠 dev 启动自动迁移生成。

2. **一期数据库口径：PG 18 而非 MySQL**（2026-10-22）
   - 曾误判为「一期 MySQL」导致 ORM JSON 列用通用 `JSON` 而非 `JSONB`；已统一为 PG 18 口径。

3. **动态表单 `form_schema` 照片/附件字段被误设为 `textarea`**（2026-10-22）
   - 结论：表单结构必须由后端 Pydantic 权威定义，`type` 覆盖 `image`/`file` 等完整类型，前端只对齐。

4. **异步 SQLAlchemy 序列化触发懒加载 `MissingGreenlet`**（2026-10-23）
   - 结论：凡是嵌套关系的出参 Schema 序列化，必须用 `preload` 完整预加载各层审计关系，勿依赖懒加载。

5. **过时迁移文件与 create_all 自举库脱节 → 启动 DuplicateTableError**（2026-10-23）
   - 现象：versions/ 残留「模型演进中间态」的迁移文件（含已删字段/表、缺新字段/表），而库已由 create_all 按最新 model 自举、`alembic_version` 为空。启动走存量库分支 `upgrade head`，从根迁移重建已存在表，报 `relation "xxx" already exists`。
   - 结论：versions/ 只保留 `__init__.py`（不提交迁移历史）。遇到 DuplicateTableError 先核对「库实际表结构」与「迁移文件」是否脱节：库是 create_all 自举则删除过时迁移文件，交由 dev autogen 按 model 对齐；空 versions/ 下 `upgrade head` 是 no-op，可放心删除。

6. **存量库「加 NOT NULL 列 + 删种子重播种」的连锁坑**（2026-10-23）
   - 现象：① autogen 给已有数据的表加 `NOT NULL` 列（产物无默认值）报 `NotNullViolationError`；② 删旧种子重新播种时若只用 `DELETE`（序列不归位），后续插入拿到的自增 ID 错位，导致写死 ID 的映射表（如 `market_service_item_task`）FK 引用断裂。
   - 结论：market 域 seed 用硬编码 ID 引用（`template_id`/`task_type_id`/`service_item_id`），依赖「空库从 1 自增」。存量库遇结构变更需重置种子时，用 `TRUNCATE ... RESTART IDENTITY CASCADE` 清空并归位序列，不要裸 `DELETE`。

7. **SQLAlchemy model 循环引用（TYPE_CHECKING + 字符串 relationship）依赖全量导入**（2026-10-26）
   - 现象：market 域 17 个 model 用 `TYPE_CHECKING` 延迟导入对方，字符串 `relationship` 靠 `routers.py` 全量导入才注册 mapper；独立 import 某模块（脚本/单测）时 mapper 初始化失败，报 `failed to locate a name ('XxxModel')`，且是「逐个冒泡」（补一个又缺下一个）。
   - 结论：需要独立加载模型集的场景（导入服务、脚本、单测）必须显式触发全量注册。market 域已建 `models.py` 统一入口（17 个 model），`import_center/service.py` 引入；后续若新增跨模块 relationship，记得同步登记进 `models.py`。

8. **Ubuntu 24/26 SSH 端口由 systemd socket activation 控制，改 sshd_config `Port` 不生效**（2026-10-27）
   - 现象：sshd_config 里 `#Port 22` 全是注释，端口实际由 `ssh.socket` 的 `ListenStream=0.0.0.0:22` 决定；只改 sshd_config 的 Port 不会改监听端口。
   - 结论：改端口要写 `/etc/systemd/system/ssh.socket.d/*.conf` override（`ListenStream=` 清空默认再列新端口），然后 `systemctl daemon-reload && systemctl restart ssh.socket`；同时把 sshd_config 的 Port 同步改掉（socket activation 关闭时的备用）。改端口是高风险操作：**先加新端口保留旧端口兜底 → 验证新端口可登录 → 再撤旧端口**。

9. **腾讯云 cloud-init 在 `sshd_config.d/50-cloud-init.conf` 写死 `PasswordAuthentication yes`**（2026-10-27）
   - 现象：自定义 drop-in 里写 `PasswordAuthentication no` 被忽略，`sshd -T` 仍显示 yes——因为 sshd_config 的 `Include /etc/ssh/sshd_config.d/*.conf` 按词法序处理，`50-cloud-init.conf`（cloud-init 注入）排在 `99-*.conf` 之前，其 `yes` 先匹配生效。
   - 结论：关密码登录前先 `grep -r PasswordAuthentication /etc/ssh/sshd_config.d/` 排查 cloud-init 残留，直接 sed 改 `50-cloud-init.conf`（或改主配置），`sshd -t` 校验后 reload，并用 `sshd -T` 复核最终生效值。

10. **中国服务器 + Let's Encrypt 跨境校验偶发超时导致证书签发失败**（2026-10-27）
   - 现象：`tls-alpn-01`/`http-01` 校验时，Let's Encrypt 海外 secondary validation 节点访问中国服务器 80/443 偶发 `Timeout during connect (likely firewall problem)`；同一 Caddy 实例下两个域名结果可能不同（`wxh5` 一次过、`admin` 失败回退到连不上的 ZeroSSL 卡住）。
   - 结论：证书签发失败时先别急着改防火墙——用本机 `curl -I http://<ip>/`（返回 308 即 80 端口实际可达）排除真实防火墙问题，再 `docker compose restart caddy` 重试签发即可（已缓存证书不受影响）；属跨境网络抖动，非配置问题。

11. **腾讯云 `CreateSecurityGroup` API 创建的安全组无默认出站规则**（2026-10-27）
   - 现象：API/CLI 创建安全组后出站默认为「全拒绝」，CVM 切到该组后主动访问数据库/公网全部超时；但入站型服务（SSH/Web）因安全组有状态、响应包自动放行而不受影响，造成「SSH 通、Web 通、就是连不上数据库」的迷惑现象。
   - 结论：用 API/CLI 创建安全组后，务必显式补「出站全放行」规则（`Protocol=ALL, CidrBlock=0.0.0.0/0, Action=ACCEPT`）；只有控制台创建才会默认带出站放行。排查「连不上下游」时，先检查本机所在安全组的**出站**规则，而非只盯着下游的入站规则。

12. **SPA 前端 `base` 前缀与 Caddy `root` 不匹配 → 静态资源回退 index.html 报 MIME 错误**（2026-10-27）
   - 现象：页面白屏，浏览器报 `Expected a JavaScript module but got MIME "text/html"`——前端 `index.html` 用 `/web/`、`/app/` 前缀引用资源，但 Caddy root 直接指向产物根，未剥离前缀，资源 404 后 `try_files` 回退到 `index.html`。
   - 结论：部署带 `base` 前缀的 SPA 时，Caddy 用 `handle_path /前缀/*`（剥离前缀）+ root 指向产物根，勿让 root 直接叠加请求路径；根路径用 `redir / /前缀/ 308` 跳转。验证方式：`curl -I` 资源 URL 应返回 `text/javascript`，而非 `text/html`。

13. **前端 `import.meta.env.VITE_XXX` 未配置时是 `undefined`，直接链式调用会运行时崩溃**（2026-10-27）
   - 现象：`VITE_APP_WS_ENDPOINT` 未配置时，`httpEndpoint(import.meta.env.VITE_APP_WS_ENDPOINT)` 里 `endpoint.replace(...)` 抛 `Cannot read properties of undefined (reading 'replace')`，触发 ErrorBoundary。
   - 结论：读 `import.meta.env.VITE_XXX` 用于字符串操作（replace/URL 构造）前必须兜底（`?.` 或回退同源 origin）；关键运行时变量应在 `.env.production` 显式配置，仓库里的 `.env.production.example` 只是模板，上线前要真正落地。前端改动必须重新构建 + 部署，否则线上仍是旧产物（旧 bug 依然复现）。

14. **COS 自定义域名（回源）必须完成 ICP 备案，否则 `PUT Bucket domain` 报 `DomainAuditFailed`**（2026-10-27）
   - 现象：`terraform apply` 绑定 `cos.xfoxlab.com.cn` 时，`tencentcloud_cos_bucket` 报 `451 DomainAuditFailed: Please complete the ICP registration of your domain before use it in Mainland China`；DNS CNAME 已成功、只有域名绑定这步被拦。
   - 结论：COS 回源自定义域名是硬性备案要求（比 CVM 更严格），域名需先完成 ICP 备案且备案主体与本账号一致。`xfoxlab.com.cn` 当前未备案（或未关联账号 100054224426）。备案完成后重跑 `terraform apply` 即可补齐域名绑定；DNS 记录与 Terraform 配置可先行落地，无需回退。

15. **SQLAlchemy 索引命名约定 `ix_%(column_0_label)s` 下「表名+列名」拼接会产生跨表同名索引冲突**（2026-10-28）
   - 现象：`market_task.template_id`（列索引）与 `market_task_template.id`（ModelMixin 主键 `index=True`）都渲染为 `ix_market_task_template_id`，`create_all` 建到第二个同名索引时抛 `DuplicateTableError: relation "ix_market_task_template_id" already exists`，全部测试在 TestClient 布局阶段 ERROR。
   - 结论：当出现「`X.Y_id` 列」与「`X_Y` 表的主键 `id`」并存时，默认命名约定会把两者拼成同一个 `ix_X_Y_id`。修复需给冲突列改用**显式 `Index` 对象**（`__table_args__` 里 `Index("ix_X_Y_fk", "Y_id")`），因为 `Column.index` 参数只接受布尔、不接受字符串名。给新模型加 `_id` 外键列时，先扫一遍是否存在 `前缀_该后缀` 形式的表名，避免重名。
   - 附带：dev autogen 在「旧库 → 新模型」时生成的根迁移（`down_revision=None`）是对旧 schema 的增量，不是从空库的干净迁移，且版本文件目录应保持「仅 `__init__.py`」，勿提交这类中间态迁移（否则与 create_all 自举库撞表/撞索引）。

16. **编号计数器表被 `TRUNCATE` 清空后未对齐 seed → 自动编号撞预置编号唯一约束**（2026-10-29）
   - 现象：market 域编号改用计数器表 `market_number_counter` 原子自增，但 `reseed_market.py` 的 `_market_tables()` 会收集所有 `market_` 前缀表（含计数器表）一并 `TRUNCATE`，重播种后计数器为空；下次创建分类 `next_code(CAT)` 从 1 重新开始，与 seed 预置的 `CAT-001` 撞唯一约束。
   - 结论：凡「预置编号 + 计数器自增」并存，seed/reseed 后必须用 `sync_counter`（`INSERT ... ON CONFLICT DO UPDATE SET current_value = GREATEST(current_value, :seq)`）把计数器对齐到预置编号的最大序号；`GREATEST` 保证只增不减、幂等。与踩坑 6（seed 用硬编码 ID 依赖空库自增）同源：market 域的种子与计数器都要和 `TRUNCATE ... RESTART IDENTITY` 的语义保持一致。

17. **同步测试里用 `asyncio.run` 操作全局 `async_db_session` → `Event loop is closed`**（2026-10-29）
   - 现象：集成测试 `TestInstitution` 需要先落库准备机构数据，用 `asyncio.run(_run())` 里 `async with async_db_session()` 直接插入，运行时报 `RuntimeError: Event loop is closed`——模块级 `async_engine` 的连接池绑定在 TestClient lifespan 的事件循环上，`asyncio.run` 新建的临时循环与引擎循环不一致，池内连接已随旧循环关闭。
   - 结论：同步测试（`def test_xxx`）里不要用 `asyncio.run` 碰全局 `async_db_session`/`async_engine`；改用**同步引擎** `engine`（`create_sync_engine` 已在 `database.py` 暴露）配 `Session(engine)` 直接落库。真正的异步逻辑测试再走 pytest-asyncio（`asyncio_mode=auto`），且需和引擎生命周期对齐。

18. **存量 `VARCHAR` 列改 `Date`，autogen 不生成 `USING` 子句 → `DatatypeMismatchError`**（2026-10-29）
   - 现象：`market_project/market_task.period` 由 `String(16)` 改 `Date` 后，dev autogen 生成的迁移 `batch_op.alter_column(type_=sa.Date())` 缺 `postgresql_using`，`upgrade` 报 `column "period" cannot be cast automatically to type date`（提示 `USING period::date`）。
   - 结论：**这不是模型设计问题，而是「跨类型收窄迁移」的正常代价**——`varchar` 与 `date` 无隐式 cast，PG 要求显式转换表达式，而 autogen 无法推断「旧字符串如何转日期」，必须手动补 `postgresql_using='period::date'`。若列有历史脏数据（如「2026 全年」），`::date` 会转换失败，需先清洗数据或写更复杂的转换表达式。凡「字符串/文本列 → 强类型（Date/DateTime/Int 等）」的迁移，都要检查 autogen 产物是否漏 `USING`；更彻底的做法是设计阶段就用强类型，避免自由文本列事后收窄。

19. **el-tree-select 的节点值取自 `node-key`，不是 `props.value`；`show-checkbox` 与 `filter-node-method` 都需显式声明**（2026-10-29）
   - 现象：① 配 `props: { label, children, value, disabled }` 时 TS 报 `'value' does not exist in type 'TreeOptionProps'`——`TreeOptionProps` 根本没有 `value` 字段，选中输出值 = `node[nodeKey]`；② `multiple` 下树节点**没有 checkbox**（父级/叶子都无法勾选）——`multiple` 只控制多选 tags，不会自动开启 el-tree 的 `show-checkbox`，官方多选示例也是显式写 `show-checkbox`；③ 节点 label 字段改名（如 `name`）后，默认 filterable 过滤按 `label` 匹配会失效。
   - 结论：el-tree-select 的「值」与「唯一标识」统一由 `node-key`（默认 `id`）承载，`props` 只配 `label/children/disabled`；凡「多张自增表拼树 + 值取 id」的场景，`node-key` 必须全局唯一（用「分类负数 id / 模板正数 id」这类符号区隔，与踩坑 15 同源），父级级联勾选时 v-model 只输出叶子值；多选必须显式 `show-checkbox`；label 字段改名时必须显式 `filter-node-method`（如 `(value, data) => data.name.includes(value)`）；`collapse-tags` 会把多选 tag 折叠成「+N」，需要完整展示时不要加。
