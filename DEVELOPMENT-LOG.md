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

- 对内结算单（熊丽 20900 / 熊志鹏 5100）：按计价项序号分组，一个计价项一个 task（`exec_qty` 汇总各执行人数量）→ 每执行人一条 assignment + settlement（合计 26000）
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

- 熊丽 8 行（20900）+ 熊志鹏 4 行（5100）+ 万邦 9 服务项目（57400）
- task 8（exec_qty 汇总正确：5→6、31→16、32→10、34→31）、assignment 12、settlement 12（26000）、report 9
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
