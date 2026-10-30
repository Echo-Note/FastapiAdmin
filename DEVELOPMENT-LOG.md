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

### 2026-10-29 — C 端移动端 4 个查询接口 403：放宽为仅登录可读

#### 1. 原因

C 端移动端（uni-app H5）首页/工作/我的页调用管理端接口 `/system/ticket/list`、`/system/ticket/stats`、`/system/notice/list`、`/monitor/online/stats`，这些接口挂了 `AuthPermission` 权限码校验。C 端账号 `user`（角色 USER，非超管）登录时仅绑定 5 个 `scope=app` 菜单且 `permission` 全空，会话 `permissions=[]`，鉴权通过但权限为空 → 403。前端虽用 `catch { /* silent */ }` 兜住不崩，但 C 端首页/我的页统计显示为「- / 空」。

#### 2. 修改内容

按用户拍板「后端放宽权限」，把这 4 个查询接口从 `AuthPermission([...])` 降为 `get_current_user`（仅要求登录）：

- `system/ticket/controller.py`：`/stats`、`/list` 由 `AuthPermission(["module_system:ticket:query"])` → `get_current_user`（并补 `get_current_user` 导入）。
- `system/notice/controller.py`：`/list` 由 `AuthPermission(["module_system:notice:query"])` → `get_current_user`。
- `monitor/online/controller.py`：`/stats` 由 `AuthPermission(["module_monitor:dashboard:query"])` → `get_current_user`。

写操作（create/update/delete/batch/export 等）保持原权限码不变。

#### 3. 关键口径

- 数据安全靠 `data_scope` 兜底：`CRUDBase._build_conditions` 统一挂 `Permission._permission_condition()`，USER 角色 `data_scope=1`（仅本人）会把工单查询追加 `created_id == user.id`，放开入口权限后 C 端用户仍只能看到自己的工单，不泄漏他人数据。
- `notice/list` 与 `online/stats` 无数据范围过滤，属「登录即可读」的全局数据（用户明确要求放宽，非遗漏）。

---

### 2026-10-29 — C 端市场任务页面视觉重构 + 分页/详情接口修复

#### 1. 原因

C 端市场任务 5 个页面（任务大厅/我的任务/任务详情/提交成果/我的收益）沿用模板化白卡片（`bg-white` + `bg-gray-50`），与首页/login 的品牌语言不一致；且存在两处体验问题：

- `MarketAPI` 的 `http.Get(url, params)` 把分页对象直接当 alova 的 config 传，`page_no/page_size` 未拼入 URL，后端只返回默认前 10 条。
- 详情页/提交页用「拉 100 条列表再 find」而非后端已有的 `/mini/tasks/{id}`、`/mini/assignments/{id}` 单详情接口，列表超 10 条时 find 失败 → 详情「加载失败」。

#### 2. 修改内容

- API 层：GET 统一改 `{ params }` 传递；新增 `getTaskDetail(id)`、`getAssignmentDetail(id)`；补 `TaskTemplateItem.items`（三级任务）与 `TaskItemDetail` 类型。
- 详情页/提交页：改用单详情接口（一次直达，消除 find 失败）。
- 视觉统一为项目既有语言：品牌渐变 Hero（`linear-gradient(135deg, primary-6→primary-4)`）、`wot-bg-filled-oppo` 卡片、品牌蓝金额、状态语义色条、克制阴影、按压态 `scale(0.98)`、骨架屏；子表原生 `input` 改 `wd-input`，上传占位改品牌虚线框。

#### 3. 关键口径

- 设计令牌以 `design-system/default/MASTER.md` 与 wot token 为准：页面底 `wot-bg-filled-bottom`、卡片 `wot-bg-filled-oppo`、品牌蓝 `--wot-primary-6`，支持暗黑模式。
- 金额统一品牌蓝大字；红色（`wot-text-error-main`）仅用于「删除/异常」等负面语义，津贴余额/待发放用 warning 橙语义。

---

### 2026-10-30 — 修复 C 端任务/工单详情跳转 query 丢失导致加载失败

#### 1. 原因

任务大厅/我的任务点击任务卡片进入详情页后「加载失败」，且后端日志只有 `/market/mini/tasks`、`/market/mini/assignments` 列表请求，无 `/market/mini/tasks/{id}`、`/market/mini/assignments/{id}` 详情请求。根因：跳转用 `router.push({ name: 'xxx', query: {...} })`，而 `@wot-ui/router@1.1.2` 的 `resolve` 在 `to.name` 分支误写 `const finalQuery = to.params || {}`（应为 `to.query`），导致 `query` 被丢弃、跳转 URL 不带参数。详情页 `onLoad` 拿不到 `task_id`/`assignment_id`，`load()` 两个分支都不触发请求，`task` 为 null → 显示「加载失败」。

#### 2. 修改内容

将 4 处 `router.push({ name, query })` 改为 `router.push({ path, query })`（走 `resolvePath` 分支，query 正确拼进 URL）：
- `task-hall/index.vue`：跳任务详情带 `task_id`
- `my-task/index.vue`：跳任务详情带 `assignment_id`
- `task-detail/index.vue`：跳提交页带 `assignment_id`
- `tickets/index.vue`：跳工单详情带 `id`（同根因，一并修复）

#### 3. 关键口径

`@wot-ui/router` 的 `router.push({ name, query })` 会丢 query（库 bug）。凡需传参的跨页跳转，一律用 `path`（`resolvePath` 分支正确处理 query），不要用 `name`。

---

### 2026-10-30 — 重建本地开发库清理市场演示数据

#### 1. 背景

C 端「我的任务」出现 5 条 `test-*`/`demo-*` 任务（`user` 账号），排查确认是 `super` 演示「定向分派」功能时把演示项目（`test`/`demo`）下的 direct 任务分派给了 `user`。代码过滤（`my_assignments` 的 `user_id = auth.user.id`）正确，属演示数据残留而非隔离缺陷。按用户要求直接重建本地开发库。

#### 2. 操作

停后端 → `DROP DATABASE fastapiadmin WITH (FORCE)` + `CREATE DATABASE` → 重启后端自举（`create_all` + 种子导入）。重建后 `market_task`/`market_assignment`/`market_project` 均 0，种子分类 6 / 模板 18 / 三级任务 51 / 用户 3 正常，后端 8001 就绪。

#### 3. 备注

- 本地库重建流程：OrbStack 容器 `docker --context orbstack exec postgres psql ...`，先停 `main.py run` 进程再 drop（否则连接占用）；重启即触发 `InitializeData.init_db()`。
- 演示账号 `super`/`admin`/`user` 密码均 `123456`（seed 固定，生产必须改）。

---

### 2026-10-30 — 任务大厅按用户隔离「已领取」任务 + 领取后自动返回大厅

#### 1. 需求

- 任务大厅领取任务成功后，自动返回任务大厅。
- 领取后任务从**当前用户**的大厅消失（出现在「我的任务」），但**其他用户的大厅仍可见**（其他用户还没领取）。

#### 2. 实现

- 后端 `TaskService.hall_tasks`：查询当前用户已领取（`source=claimed`）的 `task_id` 列表，用 `("notin", claimed_ids)` 条件从大厅结果中排除。任务本身**不改** `assign_mode`（仍为 `open`，其他用户可领）。
- 后端 `CRUDBase._resolve_condition`：新增 `notin` 操作符（空集合返回无排除条件）。
- 前端 `task-detail`：`handleClaim` 成功后 `setTimeout(() => router.back(), 600)` 自动返回大厅。
- 前端 `task-hall`：`onLoad` 改为 `onShow(() => reload())`，每次显示（含领取返回）都重置到第一页刷新。

#### 3. 关键口径

- 大厅可见性 = 「任务仍公开」∩「当前用户未领取」，是**按用户隔离**的过滤，不改变任务全局状态。这与运营「定向分派」（`batch_assign` 把 `assign_mode` 改 `direct`，任务对所有人下架）是两条不同的路径。

---

### 2026-10-30 — 修复分派详情 `MissingGreenlet`（嵌套任务审计关系未预加载）

#### 1. 原因

`GET /market/mini/assignments/{id}` 序列化 `AssignmentOutSchema.task`（`TaskOutSchema`）时，`task.created_by` / `task.updated_by` 报 `MissingGreenlet`。根因：`_ASSIGNMENT_PRELOAD = ["task", *[f"task.{p}" for p in _TASK_PRELOAD]]`，而 `_TASK_PRELOAD` 未显式列出 `TaskModel` 自身的 `created_by`/`updated_by`（此前靠 `CRUD._loader_options` 对**顶层模型**的自动审计预加载兜底，`TaskCRUD` 用没问题，但 `AssignmentCRUD` 的自动预加载只覆盖 `AssignmentModel` 自己，覆盖不到嵌套的 `task`）。

#### 2. 修改

补全预加载链（`backend/app/modules/market/task/service.py`）：
- `_TASK_PRELOAD` 增加 `created_by`、`updated_by`、`template.items.created_by`、`template.items.updated_by`。
- `_TEMPLATE_PRELOAD` 同步增加 `items.created_by`、`items.updated_by`（同类隐患，一并修复）。

#### 3. 关键口径

- 嵌套关系序列化时，`_loader_options` 的「自动审计预加载」只作用于**当前 CRUD 的顶层模型**，不会自动下钻到 `task.created_by` 这类二级路径——凡是 `OutSchema` 里带 `created_by`/`updated_by` 的嵌套对象，必须在 preload 链里**显式**写全（如 `task.created_by`）。

---

### 2026-10-30 — 新增分模块 subagent 定义（backend-agent / frontend-agent）

#### 1. 原因

用户要求按前后端拆分建立两个可复用的分模块 Agent，用于后续并行分析/编码。经确认采用**持久化 subagent 定义文件**（`.codebuddy/agents/`），而非运行时团队成员（team member）。

#### 2. 修改内容

- 新增 `.codebuddy/agents/backend-agent.md`：后端开发专家，负责 `backend/`（modules/api/core/tests/sql/scripts），内置 PG18/双轨制迁移/五件套/异步预加载防 MissingGreenlet/编号计数器等硬口径。
- 新增 `.codebuddy/agents/frontend-agent.md`：前端开发专家，负责 `frontend/`（web + app），内置 useDictStore/树形 key 唯一/`@wot-ui/router` 用 path 等硬口径。
- 两文件均为标准 subagent 格式（YAML frontmatter：`name`/`description`/`tools`/`model` + Markdown 系统提示），`tools: Read, Grep, Glob, Bash, Edit, Write`，`model: inherit`。

#### 3. 规范（同步到 SKILL.md 第 10 节）

- 遇到不确定的框架/库用法，先调用 `context7` skill 查询最新官方文档，不凭记忆猜测过时示例（两个 agent 均适用）。
- 前端页面/组件设计先调用 `ui-ux-pro-max` 与 `frontend-design` skill，遵循其设计规范，避免模板化默认样式（仅 frontend-agent）。

#### 4. 注意

- 手动添加到 `.codebuddy/agents/` 后，下次启动会话自动加载；立即生效用 `/agents` 命令确认/重载。

---

### 2026-10-30 — C 端任务大厅/我的任务细化到最小单元任务 + 按项目分组

#### 1. 需求

任务大厅、我的任务、任务详情三个 C 端页面「细化到最小单元任务」：补全最小单元任务的完整归属链路（项目 → 一级分类 → 二级模板 → 三级任务）+ 执行标准/执行要求透出，并按「项目」分组组织列表。前后端分模块多 Agent 并行（backend-agent + 3×frontend-agent）。

#### 2. 后端改动

- `TaskOutSchema` 新增顶层 `exec_standard` / `executor_requirement`（item.config 优先回退 template.config），service 统一 `_fill_task_exec_fields` 回填所有产出 `TaskOutSchema` 的位置。
- 新增 C 端分组接口：`GET /market/mini/tasks/grouped`（任务大厅，复用 `_hall_visibility_search` 可见性）与 `GET /market/mini/assignments/grouped`（我的任务，按当前用户 + 可选 status）。
- 新增分组 schema：`MiniTaskGroupSchema`（`tasks: list[TaskOutSchema]`，任务大厅）与 `MiniAssignmentGroupSchema`（`assignments: list[AssignmentOutSchema]`，我的任务）。

#### 3. 关键口径（易错点）

- **分组接口元素形状必须区分**：任务大厅分组返回「任务」（TaskOutSchema），我的任务分组必须返回「分派单」（AssignmentOutSchema，含 id/status/task），否则前端拿不到分派单 id/status，状态 Tab、进度轨道、成果角标与卡片跳转全部失真。首版误把 `[a.task for a in assignments]` 丢给 `_group_orm_tasks`，丢失分派单字段，已拆出 `_group_orm_assignments` 修复。
- 分组接口不分页（一次性返回全部），前端相应去掉触底加载/「没有更多了」。
- 前端 `@wot-ui/router` 跳转仍用 path + query（见踩坑 20）。

#### 4. 前端改动

- `api/module_market/index.ts`：`TaskItem` 补 `project`/`exec_standard`/`executor_requirement`；新增 `MiniTaskGroup`/`MiniAssignmentGroup` 类型与 `getTaskHallGrouped`/`getMyAssignmentsGrouped`。
- `task-hall`/`my-task`：改为按项目分组渲染，卡片补「一级分类 · 二级模板」路径 + 执行要求。
- `task-detail`：Hero 卡补项目/分类/模板路径 + 执行要求。
- 三页面的「执行要求」文案暂用中文字面量（未加 i18n key），待补 `market.executorRequirement`。

#### 5. 验证

- 后端 `ruff check` + `pytest -q`（259 passed）全绿；前端 `vue-tsc --noEmit` + read_lints 全绿。

---

### 2026-10-30 — 修复「提交成果无采集字段/列表显示大类」：模板级脏任务拦截 + 数据细化重建

#### 1. 原因

C 端提交成果页只有「周期」无任何采集字段；我的任务/任务大厅显示的是二级模板名（大类）而非三级任务。根因：demo 项目的 6 条任务（TK-0001~0006）被**按二级模板直接创建**（`item_id` 为空），而这些模板（商务管理服务类等）均含 5~7 个三级任务且按口径**不承载 `form_schema`**（表单由三级任务自包含）→ 模板级任务无任何采集分节可渲染。

缺陷点：`TaskService.create/update` 的 `template_id` 分支与 `ProjectService` 模板关联入口（`add_template`/`_sync_task_unit_links`）都**没有校验「叶子模板」**，有三级任务的模板也能按模板级建任务/关联。

#### 2. 修改内容

**后端强校验（`task/service.py` + `project/service.py`）**

- `TaskService._get_leaf_template()`：查询并校验模板为叶子（`preload=["items"]` 后断言 `items` 为空，否则报「模板[X]含 N 个三级任务，请按三级任务创建任务」）；`create`/`update` 的 `template_id` 分支统一走该校验。
- `ProjectService._ensure_template_exists()`：从「仅校验存在」升级为「存在 + 叶子」校验，覆盖 `add_template`/`_sync_task_unit_links`；`publish` 的模板 link 分支加同款防御（拦截历史脏关联）。

**数据修复（一次性 SQL，单事务）**

- 6 条模板级脏任务 → 按「其模板下全部三级任务」细化重建：33 条任务实例（`name = 项目-模板-三级任务`，状态/周期/分配方式继承，`task_no` 从 TK-0007 续编）+ 20 条分派（原用户 × 该模板全部新任务，状态/时间继承）。
- 引用链按序清理：institution_image → submission（1 条测试成果被删）→ assignment → task。
- 编号计数器 `TK` 用 GREATEST 对齐到 39。

#### 3. 关键口径

- **凡有三级任务的模板，必须按三级任务创建任务**；模板级任务仅对「无三级任务的叶子模板」（如会议服务）合法。后端已强校验，运营端选错会收到明确报错。
- 待办（可选）：运营端 web 任务创建表单可把「有三级任务的模板」节点禁用，从选择源头避免（当前靠后端报错提示兜底）。

#### 4. 验证

- `ruff check` + `pytest -q`（259 passed）全绿。
- 复核：33 条任务 `item_id` 全非空、每条三级任务 `form_schema` 有 3 个分节、计数器 TK=39。

---

### 2026-10-30 — 提交成果表单体验优化（周期只读/省市区联动/执行人自动填/日期控件/校验）

#### 1. 需求

提交成果页表单体验问题：周期可改、区域自由填写、执行人需手填、执行日期无日期控件、表单无校验。区域口径先误定为「七大区」，用户纠正为「全国行政区划省市区三级联动」。

#### 2. 改动

**后端（form_schema 语义扩展）**

- `FormSchemaField.type` 新增 `region`（全国省市区三级联动）；新增 `autofill: Literal["current_user"]`（自动填当前登录用户并只读）。
- 种子 + 数据迁移：`app/scripts/form_schema_semantics.py`（规则，幂等）+ `apply_seed_form_schema_semantics.py`（改两张种子 JSON）+ `migrate_form_schema_semantics.py`（就地更新库内 JSONB，不 TRUNCATE）。规则：`region` → `type=region`（移除旧七大区 options）、`executor` → `autofill=current_user`，按字段名匹配非 label。

**前端（submission-form + 类型）**

- 周期只读（弱化样式）；`date` → `wd-datetime-picker`（YYYY-MM-DD）；`region` → `wd-cascader`（省市区三级联动，`text-key="label"`，confirm 取完整路径 `/` 拼接）；`autofill=current_user` → 自动填 `userInfo.name` 只读；校验按字段类型措辞（请选择/请填写）并定位首个缺失项。

#### 3. 关键口径

- 区域 = 全国省市区三级联动（`type=region`），数据源 `element-china-area-data` 的 `pcaTextArr`（31 省级，前端内置，仅 import 该导出）。
- 执行人 = `autofill=current_user`（后端权威定义），前端按字段名 `executor` 自动填当前用户姓名（`userInfo.name ?? username`）。
- 迁移脚本与种子改造共用同一套规则，避免种子与库内数据漂移；幂等可重复执行。
- 直辖市省市区联动中间层为「市辖区」（如 `北京市/市辖区/东城区`），数据源固有，暂按完整三级展示。

#### 4. 验证

- `ruff check` + `pytest -q`（259 passed）全绿；前端 `vue-tsc --noEmit` + read_lints 全绿。
- 数据复核：37 条三级任务 region 已改为 `type=region`（无 options），executor 已加 `autofill=current_user`。

---

### 2026-10-30 — 修复 C 端文件上传 403（无权限操作）

#### 1. 原因

C 端提交成果上传图片/附件调用通用接口 `/common/file/upload`，该接口声明运营端 RBAC 权限 `module_common:file:upload`；C 端小程序用户（OAuth 自动注册，默认角色）无此权限 → `403 无权限操作`。市场域 C 端接口统一只要求登录（`get_current_user`），上传却复用了运营端受权限保护的接口，属设计缺陷。

#### 2. 修复

- 市场域 C 端路由 `mini_controller.py` 新增 `POST /market/mini/upload`：复用 `FileService.upload_service`，`dependencies=[Security(get_current_user)]` 仅校验登录，不要求 RBAC 权限码。
- 前端 `MarketAPI.uploadFile` 改调 `/market/mini/upload?upload_type=file`。
- 运营端 `/common/file/upload` 保持不变（仍受 `module_common:file:upload` 权限保护）。

#### 3. 关键口径

- C 端接口一律「登录即可」（`get_current_user`），不挂运营端菜单权限码；需要上传/下载能力时在 C 端路由内提供专用入口，复用通用 FileService 而非直接暴露运营端受保护接口。
- 上传（写入）不敏感可放开到登录级，下载（读取）仍受权限保护。

#### 4. 验证

- `ruff check` + `pytest -q`（259 passed）全绿；前端 read_lints 零 error。

---

### 2026-10-30 — 运营工作台概览页重排：从 12 张等权卡片改为「待处理 / 业务流转 / 资料库」三段式

#### 1. 原因

原页面把 `GET /market/dashboard/overview` 的 12 个计数平铺成 12 张同尺寸 `FaStatsCard`（4 + 3 + 5），存在四个信息设计问题：

1. **没有层级**：待审核成果（要人干活）与二级模板总数（资料库存量）视觉权重完全相同；
2. **没有流向**：任务 → 成果 → 结算是一条真实业务链，页面却把 7 个状态计数拆散成互不相邻的卡片，看不出「哪一环积压」；
3. **颜色无意义**：每个卡片随机配一个彩色图标块（primary/success/warning/danger/info 轮流用），同一个「橙」既表示待审核也表示已结算任务、也表示机构数；
4. **不可行动 + 失败伪装**：数字点不进去；`catch` 里只弹一条 `ElMessage`，然后照常渲染一堆 0——把「接口挂了」显示成「业务归零」。

#### 2. 改法（只改前端，不动接口）

`views/module_market/dashboard/index.vue` 整体重写，零新增接口、零新增依赖：

- **① 待处理**：待审核成果 / 进行中任务 / 结算单三格，数字 + 一句「等运营做什么」+ 跳转（`/market/task/submission`、`/market/task/task`、`/market/payout/settlement`）。跳转按 `useAuth().hasAuth` 守卫，无权限时降级为纯数字（不展示点了会 403 的入口）。
- **② 业务流转**：任务 → 成果 → 结算三列，阶段之间有流向箭头（真实顺序，不是装饰）；任务/成果两列用 **100% 堆叠条**画状态分布（进行中/已完成/已结算/其他，待审核/已通过/已驳回/其他），占比按阶段总数算，「其他」= 总数 − 各状态之和（草稿/已发布/归档等未单列状态）。结算列为终点：应发金额 + 单数 + 口径说明「全部结算单应发合计，不区分状态」——这句正是旧版 description「结算应发合计（元）」说不清的地方。
- **③ 资料库**：项目/医药公司/机构/一级分类/二级模板降为一条可点目录（13px 标签 + 20px 数字），不再和业务指标争权重。
- **页头**：面包屑已标明页名，故不再重复 `<h2>工作台概览`；页面级只保留右对齐的「全库数据（不含已删除），更新于 HH:mm」+ 刷新。

#### 3. 顺手修掉的三个缺陷

- **失败态**：首屏失败改为错误块 + 重试（不再渲染 0）；已有数据时刷新失败则**保留旧数据** + `ElMessage` 提示，页面不被清空。
- **骨架**：`ElSkeleton` 三块高度对齐真实版式（98 / 226 / 74），避免加载完成的跳动。
- **缓存陈旧**：页面 `keep_alive=true`，切回标签不重挂载。新增 `onActivated` 判断：距上次加载超过 5 分钟才静默重拉，配合「更新于 HH:mm」让数字的新鲜度可核对。

#### 4. 视觉口径（对齐 `design-system/default/MASTER.md`）

- 颜色只承载**状态语义**：进行中/待审核 = `warning`、已完成 = `primary`、已结算/已通过 = `success`、已驳回 = `danger`、其余 = 中性灰；去掉了全部彩色图标块。
- 单处重笔 = 堆叠条 + 阶段箭头；其余保持无阴影、无渐变、无装饰图标（卡片描边 `--fa-card-border`，圆角 `calc(var(--custom-radius) + 4px)`）。
- 数字统一 `font-variant-numeric: tabular-nums`；**不使用 `FaCountTo` 数字滚动**——首页数字直接可读比动画更重要。
- 色块不是唯一信息载体：图例给出「状态名 + 数值 + 占比」，堆叠条带 `role="img"` + `aria-label`。
- 响应式：1180 / 900 / 760 三档，业务流转列在窄屏纵向堆叠（箭头与竖分割线同时隐藏）。

#### 5. 验证

- `npx vue-tsc --noEmit --skipLibCheck` → 0 错误；`eslint` / `stylelint` / `prettier --check` 该文件 → 全部通过；`npx vitest run` → 41 passed。
- Playwright 实测（用 `page.route` 注入 mock 数据绕过空库）：1440 / 1200 宽、真实种子数据、暗色、接口失败态、760 窄屏均符合预期。
- 本地库当前无成果/结算数据（见「重建本地开发库清理市场演示数据」），因此实机页面大多是 0——这是数据现状，不是排版问题；堆叠条在 0 数据下显示「暂无数据」而非空条。

---

### 2026-10-30 — 运营工作台首页增补「14 天提交趋势」+「待审核队列」

#### 1. 原因

上一轮重排只解决了「现在有多少」，回答不了两个运营真实问题：「这两天提交量在变好还是变差」「具体是哪几条在等我」。需要后端补明细数据。

#### 2. 后端：新增 `GET /market/dashboard/insights`

- `schema.py`：`SubmissionTrendPointSchema`（date + 待审/通过/驳回）、`PendingSubmissionRowSchema`（id/subject/task_name/period/created_at）、`DashboardInsightsSchema`。
- `service.py`：新增 `insights()`。
  - 趋势窗口 = 北京时间今天往前 13 天 00:00 转 UTC；只取窗口内 `(created_time, status)` 两列，用纯函数 `build_trend()` 按本地日历日分桶、缺失日补 0、草稿不入桶。
  - 队列一条 join：`submission → assignment → task` 内连接，`institution` 外连接（软删除过滤写在 ON 里，机构被删时退回 `subject_name`），`status=PENDING` 倒序取 8 条。
  - `created_at` 返回带 `+08:00` 的 ISO 串，前端不用去解析 `YYYY-MM-DD HH:mm:ss` 这种跨浏览器不可靠格式。
- `controller.py`：`/insights`，权限码与 `/overview` 相同。
- **不改 `overview`**：它是纯计数契约且有结构断言；也不复用 `/market/submissions` 列表接口拿队列——那会把 `form_data`（JSONB）整列带回。

#### 3. 前端

- `api/module_market/dashboard.ts`：`getInsights()` + 三个类型。
- `views/module_market/dashboard/index.vue`：
  - 待处理卡内新增队列块（8 行四列，整行 `RouterLink` 到 `?status=PENDING`）；无 `submission:query` 权限不渲染；窄屏用 `grid-template-areas` 换成「对象名 + 时间 / 任务名」两行。
  - 业务流转卡内新增趋势块：**自绘 CSS 堆叠柱**（14 列，绿/橙/红自底向上），柱高按峰值归一，头部「峰值 N 条 · 合计 M 条」+ 只标颜色的图例；空态保留 25/50/75% 网格线与基线 + 居中说明。
  - 取数改为 `refreshAll()` 并行；`insights` 失败非致命，两块各自内联重试，不清空已渲染的计数。
- `views/module_market/submission/index.vue`：读 `route.query.status` 作为 `searchForm` 初值 + `useTable` 的 `apiParams.status`（首次加载即带筛选，不多发请求），另加 `watch(route.query.status)` 覆盖 KeepAlive 缓存下换参数再点进来的情况。

#### 4. 为什么不直接用 `FaBarChart`

它的 `useChartComponent.checkEmpty` 在数据全 0 时执行 `chart.clear()` 并插入居中空态 div（丢掉坐标轴与网格），与本页「空态保留基线 + 网格」的约定冲突；默认渐变/网格样式也与 hairline 语言不符。自绘 40 行 CSS 即可，颜色直接吃 `--el-color-*`。

#### 5. 验证

- 后端：`ruff check` 通过；`pytest tests/test_market_dashboard.py` **10 passed**（新增：insights 结构/空库全 0/401、`build_trend` 跨日边界与补 0、队列 join 四个字段与今日桶、非 PENDING 不入队列）；全量 `pytest` **266 passed**。
- 前端：`vue-tsc` / `eslint` / `stylelint` / `prettier` 均通过，`vitest` 41 passed。
- Playwright 实测（mock 数据）：1440 / 1200 / 760、暗色、趋势全 0 空态、insights 500 失败态、空队列；并验证深链——点队列首行后 URL 为 `#/market/task/submission?status=PENDING` 且搜索栏状态显示「待审核」。
- 修一轮：网格线原用 `rgba(0,0,0,.08)` 在白底几乎不可见，改 `--default-border` 并按 25/50/75% 定位 + 基线；窄屏队列原 flex 写法把时间挤到第三行，改 `grid-template-areas`。

#### 6. 后续可做

- 不包含：结算金额趋势、时间范围切换、队列混排任务/结算单、点行直接打开该条审核弹窗（需审核页支持按 id 深链）。
- `submission/index.vue` 的 `<style scoped>` 里有 3 处 stylelint `order/properties-order` 遗留告警（`form-data-pre` 块，属存量），本次未动；下次跑全量 `pnpm lint` 会被 `--fix` 自动整理。

---

### 2026-11-01 — C 端提交成果字段缺失的根因修复（采集表对齐）+ 新增产品库模块

#### 1. 原因（三因叠加，不是单点 bug）

用户反馈 App「提交成果」页面字段比运营手上的 Excel 采集表少很多，且不是个例。排查结论：

1. **主因 · 种子模板数据从未对齐真实采集表**：`backend/sql/market_task_item.json` 的 `form_schema` 是早期占位结构。例：民营医疗管理「配送协调」只有 4 列（产品名称/批号/配送数量/配送时间），真实采集表有 8 列（+产品规格/生产企业/验收情况/配送商业）；所有采集表下方的「异常说明」种子完全没有；执行信息缺机构类型专属字段（基层：机构类型/上级管理主体；民营：单体／集团/所属集团；零售：连锁／单体/所属连锁总部；商业：商业公司名称）；库存盘点/价格核查/销售对账/竞品调研的列名整体错位。
2. **次因 · App 子表单元格不区分列类型**：`submission-form/index.vue` 的 `table` 分支对每列一律渲染 `wd-input`，`date`/`number`/`select`/`image` 列都拿不到对应控件。
3. **陷阱 · 只改种子 JSON 修不好已初始化的库**：`initialize.py` 的 `__init_data` 是「表已有数据则整体跳过」，不会覆盖既有记录，必须走一次性订正脚本。

#### 2. 改法

- 新增 `backend/app/modules/market/task/collection_schema.py`：用「机构类型专属执行信息 + 工作区列定义」拼出机构管理 5 类 26 个三级任务（`ITEM-0001`..`ITEM-0026`）的 `FormSchema`，导出 `ITEM_FORM_SCHEMAS`。它是**种子与存量订正的唯一生成源**，运行时不读它（运行时真相仍是库里 `config.form_schema`）。
- 新增 `backend/app/scripts/apply_collection_schema.py`：`--seed` 重写种子 JSON（26 条）、`--db` 就地订正库内记录（深拷贝后回写，JSONB 列 `mutable=False` 才认变更）、`--dry-run` 只打印；幂等。
- `FormSchemaColumn` 增加 `product_role`（name/spec/manufacturer）；App 子表按列类型渲染，三套选择器与上传收敛为统一的 `ValueTarget`（`rowIndex=null` 即单值字段）；Web 表单设计器补子列选项与产品库角色编辑。
- 新增产品库子模块 `market/product`：`market_product` 以 `(name, spec, manufacturer)` 判重；提交人不另设来源枚举，直接用审计字段 `created_id`/`created_by`（运营录入与 C 端提交都是具体用户）；C 端 `GET /market/mini/products/search` 可见集 = `approved` ∪（`pending` 且 `created_id` = 本人）；成果提交/驳回重提后把库里没有的产品自动入库为 `pending`（判重键已存在则跳过，单条失败用 savepoint 隔离，不影响成果落库）；运营端 `/market/products/*` 提供 CRUD + 批量审核，菜单「市场管理 → 产品库」。
- 关键命名取舍：竞品调研的行用 `competitor_*` 前缀而非产品三要素 key，避免竞品被当成自家产品检索并自动写进产品库；退役语义的旧 key 不复用（库存盘点 `stock_qty`=库存数量 → 新「实盘数量」用 `actual_qty`）。
- 范围之外（素材缺失或本轮未做）：市场档案信息调研 5 张、专项调研 7 模板×2（docx 问卷）、会议服务 3 模板（当前还没有三级任务）、市场宣传 2 模板；`ITEM-0027` 进销存数据收集 / `ITEM-0028` 流向数据收集 在素材里没有采集表，不臆造字段。

#### 3. 验证

- 后端：`uv run pytest` **314 passed**（新增 `test_market_collection_schema.py` 39 例锁定「种子 ≡ 生成源」，`test_market_product.py` 9 例覆盖判重/可见性/自动入库）；`uv run ruff check app tests` 通过。
- Web：`vue-tsc --noEmit` 通过，新增文件 `eslint`/`stylelint` 通过。
- App：`vue-tsc --noEmit` 通过，改动文件 `eslint` 0 error（4 条 warning 为存量）。
- **存量库必须手动订正一次**：`cd backend && PYTHONPATH=. uv run python -m app.scripts.apply_collection_schema --db --dry-run` 确认后去掉 `--dry-run` 再跑；并到「菜单管理」补「产品库」菜单（种子只在空表时导入）。
- 若某个库在本轮中间态建过 `market_product`（带已被移除的 `source` / `submitter_id` 两列），需要 `DROP TABLE market_product;` 后重启（或手动 `ALTER TABLE market_product DROP COLUMN source, DROP COLUMN submitter_id`）——两次模型定义都被 autogen 视为增量，且 `initialize.py` 的破坏性 DROP 拦截规则只认 `op.drop_*`，认不出 `batch_op.drop_column`，会把这类迁移放过去（该拦截正则的已知盲点，见踩坑 15）。

#### 4. 顺带记录（Hindsight 记忆纠偏时发现，本轮未修）

- 成果 `create` 不写 `status` → 落库即 `DRAFT`，而 dashboard 按 `status=PENDING` 统计「待审核成果」→ 该计数恒为 0。
- `AssignmentStatus` 的 `SUBMITTING`/`REVIEWED`/`SETTLED` 定义了却没有任何写入路径，结算也不回写分派状态。
- `market_submission` 没有任何唯一约束，「单月单对象只提交一次」只靠业务层，并发重提无 DB 兜底。

---

### 2026-11-01 — 发布项目后任务页为空 / 侧边栏目录出现完整树 / 运营录入产品不需要审核

#### 1. 现象与根因

- **发布项目后「任务」页没有任务**：项目发布只创建 `DRAFT` 任务实例（设计如此，需运营再发布），而任务页两处硬编码了 `exclude_status: "DRAFT"`——`useTable` 的初始 `apiParams` 和 `refreshWithFilters()`（搜索/点目录都会走它）。任务确实在库里（诊断时 57 条全部是 DRAFT），只是被列表过滤掉了，形成「必须先发布才能看到、但看不到就没法发布」的死锁。修复：两处都去掉 `exclude_status`，草稿默认可见，靠状态筛选显式过滤。
- **任务页左侧目录树总是完整一棵**：树来自 `/market/categories/tree`（主数据 6 分类 / 18 模板），与任务存在与否无关，空库时也显示全部。修复：新增 `GET /market/tasks/facets`（`group by category_id, template_id` 返回任务数），前端只渲染有任务的分类/模板并在节点上带任务数，任务增删后刷新，`onActivated` 覆盖「从项目页发布后切回」的场景。
- **运营录入的产品被当成待审对象**：产品落库本来就是 `approved`（免审），但行操作里「驳回」对非 `rejected` 的行都显示，看起来像需要审批。修复：只有 `audit_status === "pending"`（C 端自动入库）才显示「通过/驳回」。

#### 2. 验证

- API：不排除草稿 → 57 条；`exclude_status=DRAFT` → 0 条（正是用户看到的现象）；`/market/tasks/facets` → 5 条（分类 1 下的模板 1..5，含任务数）。
- Web：`vue-tsc --noEmit` 通过，改动文件 `eslint` 通过。

#### 3. 附带订正（我上一条记录写错了）

曾怀疑 `uv run pytest` 往开发库里写测试数据——**这是错的**：`tests/conftest.py` 早已把 `DATABASE_NAME` 固定为 `fastapiadmin_test`（`TEST_DB_NAME` 可覆盖），实测库列表里 `fastapiadmin` 与 `fastapiadmin_test` 是分开的两个库。开发库里那些 `test` / `demo` 项目是运营在界面上手动建的，不是测试产物。

---

### 2026-11-01 — 项目结束后其任务仍在列表/大厅；任务目录页默认只看已用

#### 1. 现象与根因

- **项目已关闭/已删除，任务还挂在任务列表里**：`TaskService.page` 只按任务自身字段过滤，完全没看所属项目的生命周期。实测：项目 `test` 状态 `CLOSED` 且 `is_deleted=true`，其 28 个任务仍出现在 `/market/tasks/list`。C 端大厅同理——项目都结束了任务还能被接单。
- **任务目录页一进就是完整 6 分类 / 18 模板 / 51 三级任务**：目录页读的是主数据树（`/market/categories/tree`），与「有没有项目在用」无关。

#### 2. 改法

- `TaskService._inactive_project_ids()`：取「已关闭（`ProjectStatus.CLOSED`）或已软删除」的项目 id；任务列表、目录统计、C 端大厅三处统一排除（`TaskQueryParam.include_closed_project` 默认 false，需要追溯时显式打开）。
- 新增 `GET /market/items/usage`（`CatalogUsageSchema {item_ids, template_ids}`）：返回被**未删除项目**引用的三级任务与叶子模板 id；任务目录页默认「只看已用目录」（开关可关，关掉才显示全量，新增目录时用）。

#### 3. 验证

- API：默认任务 `28` 条（只剩进行中的 demo 项目）；`include_closed_project=true` → `56` 条；`/market/items/usage` → 已用三级任务 28、叶子模板 0。
- 新增 `tests/test_market_task_project_visibility.py` 3 个用例：项目关闭后任务从列表/统计消失、显式参数仍可追溯、软删除项目同样隐藏、已发布任务所属项目关闭后不出现在大厅。
- `uv run pytest`（`fastapiadmin_test` 库）→ 全绿；`ruff check` 通过；Web `vue-tsc` / `eslint` 通过。

---

### 2026-11-01 — 定向分派即发布：草稿任务被派发后不再留在 DRAFT

#### 1. 原因

`AssignmentService.my_assignments` / `grouped_my_assignments` 只按 `user_id` 过滤，**不按任务状态过滤**；而项目发布只生成 `DRAFT` 任务。于是运营把草稿任务定向派发给某人后，这个人立刻能在「我的任务」看到并提交成果，任务状态却还是草稿——执行状态与任务状态脱节，结算/看板统计也会偏低。

#### 2. 改法

`batch_assign`（`source=assigned`）在把任务改成 `direct` 的同时，若任务仍是 `DRAFT` 就一并置为 `PUBLISHED` 并写 `publisher_id` / `published_at`。定向分派本身就是「指定了执行人 = 上线执行」的语义；不需要定向分派的任务仍由运营显式「发布」进大厅，两条路径最终都到 `PUBLISHED`。`claim`（大厅接单）不受影响。

#### 3. 验证

- 新增 `test_direct_assign_publishes_draft_task`：草稿任务派发后 `status=PUBLISHED`、`assign_mode=direct`，且被指派人能在 `/market/mini/assignments` 看到该分派；原有 `test_assign_open_task_switches_to_direct` 追加「已发布 + 有发布人与时间」断言。
- `uv run pytest`（`fastapiadmin_test` 库）→ **318 passed**；`ruff check` 通过。

---

### 2026-11-01 — 成果/分派状态机补全 + 同月提交去重 + C 端本地草稿

#### 1. 三个缺陷与定案

| 缺陷 | 原状 | 定案 |
|---|---|---|
| 成果提交后状态 | `create` 不写 `status`，落库即 `DRAFT`；dashboard 按 `PENDING` 统计「待审核」→ **恒为 0** | 提交即 `PENDING`；dashboard 待审核按 `PENDING` 统计并兼容历史 `DRAFT` |
| 分派状态机 | `SUBMITTING`/`REVIEWED`/`SETTLED` 定义了但从不写入，结算也不回写 | 补全：提交→`SUBMITTED`、审核通过→`REVIEWED`、归集结算→`SETTLED`；`SUBMITTING` 从未写入，删除 |
| 同月重复提交 | `market_submission` 无任何唯一约束，只靠业务层，并发能双提交 | 分派行 `SELECT … FOR UPDATE` + 按 `submit_rule.cadence` 查重（monthly/once 同月一份，unlimited 不限）；故意不加唯一约束（定额/会议任务需同月多份） |

顺带满足用户提出的「填一半刷新/关闭要保留内容」：**草稿只存本机**（`uni.setStorageSync('market-submission-draft:<assignmentId>')`，800ms 防抖，恢复时提示，提交成功清除），后端不存未提交表单——这样 `PENDING` 严格等于「待运营审核」。

#### 2. 关键实现点

- `SubmissionService.create`：先 `with_for_update()` 锁分派行，再 `_ensure_period_not_submitted()` 查重（排除 `REJECTED` 以允许改后重提），最后 `status="PENDING"` + 回写分派 `SUBMITTED`。
- `SubmissionService.review`：通过 → 成果 `APPROVED` 且分派 `REVIEWED`；驳回 → 成果 `REJECTED` 且分派回 `SUBMITTED`（等重提）。
- `SettlementService.settle`：生成结算单后把该分派置 `SETTLED`。
- `enums.AssignmentStatus` 删 `SUBMITTING`；`test_market_enums` 增断言防回潮。

#### 3. 验证

- 新增 `tests/test_market_submission_flow.py` 4 个用例：提交写 `PENDING` + 分派 `SUBMITTED`、同月重复提交被拒（换月可提交）、审核通过 `REVIEWED` + 结算 `SETTLED`、dashboard 待审核计数不再恒 0。
- `test_market_product` 的重复提交用例随之改为「第二次被拦下且产品只入库一次」。
- `uv run pytest`（`fastapiadmin_test`）→ **322 passed**；`ruff check` 通过；App `vue-tsc` 通过、`eslint` 0 error（4 条存量 warning）。

---

### 2026-11-01 — C 端图片/附件支持多份（最多 9），运营端成果详情加缩略图预览

#### 1. 需求与定案

现场照片、打卡照、陈列照经常不止一张；附件（签到表/票据）也可能多份。定案：

| 决策 | 取值 |
|---|---|
| `form_data` 值形态 | `image` / `file` 存 **URL 数组**（`["url1","url2"]`） |
| 兼容 | 历史单字符串读取时归一成数组，**不做数据迁移** |
| 上限 | 单字段最多 **9** 份（微信 `chooseImage` 单次上限，可多次追加） |
| 运营端 | 成果详情/审核弹窗加缩略图网格 + 点击大图预览、附件文件名链接、子表按表格渲染 |

#### 2. 改法

- **App**（`subPages/module_market/submission-form/index.vue`）：`asUrlList()` 统一归一；上传改为「追加 + 逐份删除」（`appendUrl` / `removeUrlAt`），多选 `count = 9 - 已有`、串行上传（并发会让 uploadingKey 互相覆盖）；单值字段与子表 image/file 列共用同一套逻辑；`isBlank` 增加空数组判定，必填图片不会被漏校验。
- **Web**（新增 `components/display/fa-form-data-viewer`）：不依赖 `form_schema`，按数据结构推断渲染——图片 URL（按扩展名识别）给 `ElImage` 缩略图 + `preview-src-list` 大图预览，非图片 URL 给文件名链接，对象数组按 `ElTable` 渲染子表，其余走文本；末尾 `ElCollapse` 保留原始 JSON。成果详情与审核弹窗两处 `<pre>{{ JSON }}</pre>` 替换为该组件。
- 顺带删掉两处失效的 `formattedFormData` / `formattedReviewFormData` computed 与 `.form-data-pre` 样式。

#### 3. 验证

- App：`npx vue-tsc --noEmit` 通过；`eslint` 0 error。
- Web：`npx vue-tsc --noEmit` 通过；`eslint` / `stylelint`（新组件与改动页面）通过。
- 后端无需改动（`form_data` 是 JSONB，且没有任何代码解析 image 字段）；`ruff check` 通过、`uv run pytest` 322 passed。

---

### 2026-11-01 — 成果审核页：采集数据渲染中文字段名 + 补齐机构/对象名称/区域/档案号

#### 1. 原因

运营在「任务审核 → 成果审核」弹窗里看到两处不可用：

1. **采集数据全是英文字段名**：`FaFormDataViewer` 的注释写着「不依赖 form_schema」，字段名/分节名直接拿 `form_data` 的 key 渲染，审核员看到的是 `region` / `executor` / `hospital_name` / `qty` / `batch_no`…，无从判断。前端当时只有一张硬编码的 `sectionNames`（9 个分节 code → 中文），**字段名和子表列名完全没有映射**，且该映射是第二份真相源，会和 `collection_schema.py` 漂移。
2. **机构 / 对象名称 / 档案号 / 区域四格永远为空**：
   - `SubmissionOutSchema` 没有 `institution` 字段（只有 `institution_id`），前端写的是 `institution.name`，永远渲染 `—`；
   - C 端提交只传 `{assignment_id, period, form_data}`，`subject_name` / `region` 两列**没有任何代码写入**；
   - `archive_no`（开发档案编号）在 model / schema / 前端都存在，但**全库没人赋值**，`numbering.py` 也没有对应前缀。

#### 2. 改法（后端回填真相源，前端只做渲染）

- **`task/schema.py`**：新增 `SubmissionInstitutionBriefSchema`（id/name/type/region）；`SubmissionOutSchema` 增 `institution` 与 `form_schema: list[FormSchemaSection]`，两者**只在详情类接口回填**（列表不加载，避免 N+1）。
- **`task/service.py`**：
  - `_submission_display_fields()`：从 `form_data` 推导对象名称（机构对象取 `hospital_name`/`org_name`，会议/个人对象取 `meeting_name`/`staff_name`/`patient_name`/`name`）与区域（`region` 字段）。
  - `create()`：落库时补齐 `subject_name` / `region`；`archive_no` 走 `next_code(NumberPrefix.ARCHIVE)` 生成 `ARC-0001` 序列。
  - `detail()`：预加载 `institution` + `assignment.task(.template/.item)`，回填 `institution` 与强类型 `form_schema`（三级任务优先、模板兜底）；并对存量行**只补空值地自愈回写** `subject_name`/`region`/`archive_no`，让列表页也能看到；schema 不合规时降级返回 `None` + warning，不让存量脏 schema 把详情打成 500。
  - `page()` / `my_submissions()`：补 `preload=["institution"]`。
- **`numbering.py`**：新增 `NumberPrefix.ARCHIVE = "ARC"`。
- **`FaFormDataViewer`**：`sectionNames` 之外新增 `schema` prop，分节名取 `section.name`、字段名取 `fields[key].label`、子表列按 `columns` 的中文 `label` **并按 schema 列序排列**（schema 里没声明的列按数据键名追加在后）；无 schema 时回退英文 key，保证组件不依赖调用方。
- **`views/module_market/submission/index.vue`**：删除硬编码的 `sectionNames` 常量，两处 viewer 改传 `form_schema`；`api/module_market/submission.ts` 补 `form_schema` 类型。

#### 3. 关键口径

- **`form_data` 的英文 key 到中文标签，只能由任务自带 `form_schema` 反查**（后端 Pydantic 是唯一真相源，见硬口径 4）。前端不要再维护任何「code → 中文」的静态映射表，否则与 `collection_schema.py` 必然漂移。
- **档案号 `ARC-NNNN`** = 一份成果一个号，提交时由计数器原子分配，C 端不填；与 `TK`（任务流水号）语义不同，勿混用。
- 存量成果的摘要三列采用**读详情时自愈回填**（只补空值、不覆盖已有值），不写迁移脚本；新数据在 `create` 阶段就已补齐。

#### 4. 验证

- 后端：`uv run ruff check` 通过；`uv run pytest` **325 passed**（新增 3 条：摘要字段落库、详情带 institution/form_schema 且每个 form_data 键都有中文标签、存量行自愈并同步到列表）。
- 前端：`vue-tsc --noEmit` 通过；`eslint` 0 error。
- 真实 dev 库核对：`GET /market/submissions/detail/1` 返回 `institution.name=xxsdsd`、`region=北京市/市辖区/东城区`、`archive_no=ARC-0001`，`form_schema` 三节的中文标签（医院名称/医院等级/产品名称/批号/配送数量…）齐全。

---

### 2026-11-01 — 任务审核列表重设计（项目/分类/模板/任务完整层级）+ 搜索栏重做

#### 1. 原因

运营看「任务审核 → 成果审核」列表时提两个问题：① 看不出这份成果属于哪个项目/分类/模板/任务，只能看到机构、对象类型、用户、区域、档案号；② 非机构对象（医务人员/患者/会议）行里「机构」「区域」天然为空，像数据缺失；③ 搜索栏的筛选项是「分派ID」——数据库自增 id，人工无法使用。

根因：成果表只存 `assignment_id`，项目/分类/模板/任务隔了两层外键，出参里根本没有这层信息；列表列是围绕「机构」这一种采集对象设计的。

定案（与用户确认）：列选**完整层级平铺**（项目/分类/模板/任务/任务编号各一列）；机构与对象名称合并为「采集对象」（对象名称对机构对象取机构名、对个人对象取受访人）；计价（单价×单位）本轮不加——因为结算只读**模板**级 unit/price，三级任务的价格覆盖尚未参与结算，现在展示会给审核员错误预期；搜索栏一并重做。

#### 2. 改法

- **出参（`task/schema.py`）**：新增 `SubmissionTaskContextSchema`（扁平：`task_no`/`name` + `project_id|name` + `category_id|name` + `template_id|name` + `item_id|name`），`SubmissionOutSchema` 增 `task`，列表与详情都回填。
- **服务层（`task/service.py`）**：
  - `_SUBMISSION_PRELOAD` 统一预加载（institution + assignment.task.project/item/template.category），`_task_context()` 升维、`_to_out()` 统一转出参、`_page_out()` 让列表与「我的成果」共用；
  - `_fill_summary_fields()` 把「区域/对象名称」的回填提到**出参层**（不只详情），存量行在列表也不再空白，详情再把差异落库；
  - `_SUBJECT_NAME_FIELDS` 补 `respondent`：医务人员/患者调研类采集表用「受访对象」存对象名（store_name 是门店，不是对象）；
  - `_apply_task_filter()` 把 `project_id`/`template_id`/`item_id` 改写为 `assignment_id IN (SELECT market_assignment.id JOIN market_task ...)` 子查询（这三个字段不是成果表列，必须先摘出查询字典，否则 `_build_conditions` 在模型上找不到列）；同时给了 `assignment_id` 时并进同一子查询。`archive_no` 由等值改模糊。
- **列表页（`views/module_market/submission/index.vue`）**：列改为 序号(左固定)/项目/分类/任务模板/任务/任务编号/采集对象/对象类型/区域/提交人/档案号/提交月份/状态/提交时间/操作(右固定)；`版本`、`AI 校验` 用 `visible: false` 默认隐藏（列设置可开）；搜索栏换成 档案号/项目/任务模板/任务/提交人/提交月份/状态，模板与任务联动（换模板清掉不再可选的已选任务），三级任务按 `has_next` 翻页取全（page_size 上限 100）。
- **弹窗**：详情/审核摘要同步换成任务上下文，并去掉重复的「机构 + 对象名称」两行（统一为「采集对象」）。

#### 3. 关键口径

- **成果列表的层级信息必须由后端升维**：成果表只有 `assignment_id`，前端拿不到项目/分类/模板/任务；同理筛选也只能在后端用子查询实现，不要让前端先取全量 id 再回传。
- **凡是 `SubmissionQueryParam` 里新增「非成果表列」的字段，必须在服务层先摘出去**（`_pop_task_filter`）——否则 `_build_conditions` 会 `getattr(model, key)` 直接 `AttributeError`。
- 「采集对象」是一列而不是两列：机构对象展示机构名、个人对象展示受访人（`respondent`），否则总有一种对象类型整列为空。

#### 4. 验证

- 后端：`uv run pytest` **327 passed**（新增：列表任务上下文 + 三层筛选/AND/模糊匹配、staff 调研对象名取 respondent）；`uv run ruff check` 通过。
- 真实接口逐项验证：`project_id=2`→[1]、`project_id=4`→[2]、`template_id=1`→[1]、`item_id=32`→[2]、`item_id=1&project_id=4`→[]、`archive_no=ARC-000`→[1,2]。
- 前端：`vue-tsc --noEmit` 通过；`eslint` 0 error。
- 浏览器实机未点验（Playwright profile 被占用），已用「改前/改后」HTML mockup 交付预期效果。

---

### 2026-11-01 — 发放封顶/津贴滚存落地 + 成果审核通过自动归集

#### 1. 原因

运营把成果审通过后，「结算管理」与「发放管理」两页始终为空。查证后的结论是三层缺口叠加，不是显示问题：

1. `SubmissionService.review` 只改 `market_submission.status` 与 `market_assignment.status`，**从不触发归集**；
2. `SettlementService.settle` 只有运营手点「归集结算」一个入口，且要求任务先被判定 `COMPLETED`，而审核通过并不推进任务状态；
3. `docs/02` §5 的发放算法（封顶 + 滚存）从未实现：`payout_limit` 只用于展示，`market_allowance` / `market_allowance_detail` **只有读路径、没有写路径**，两张表恒空。`specs/market/payout` 早已把它记为「已确认的缺口」。

#### 2. 改法

- **`settle` 改重算 + 参数化前置**：新增 `require_completed` 开关（审核自动归集传 `False`，运营手动归集仍要求任务 `COMPLETED`）；已存在的 `task+user+period` 结算单从「跳过」改成「更新 qty/payable + 同步明细」（`_sync_item`：有则更新、多条收敛为一条）。
- **`PayoutService.apply(user_id, period)`**：按「用户 × 周期」整体算 `pending = 当月应发合计 + 期初津贴`、`paid = min(pending, limit)`、`rollover = pending - paid`，写 `market_allowance.balance`、upsert `allowance_detail(amount=期末累计未发放)`，并把 `paid` 按结算单 id 顺序**贪心分摊**回 `paid_amount` + `pay_status=SCHEDULED`。
- **审核通过自动归集**：`review` 在 `approved=True` 落库后调 `settle(require_completed=False)`，出参由 `SubmissionOutSchema` 换成 `SubmissionReviewResultSchema{submission, settlement, warning}`；归集失败只写 `warning`、**不回滚审核**。
- **`GET /market/payout/results`**：按 用户×周期 聚合结算单应发，再补齐期初/额度/实发/期末，分组分页都在 SQL 侧。
- **前端**：审核「通过」前弹二次确认（说明会真的产生结算单），成功后弹归集结果并可跳结算单；发放管理页加「发放结果」页签（同页 `ElTabs`，不新增菜单）。
- 新增 `PayStatus` 枚举；`AllowanceStatus` docstring 从「被下月消费」改成「二期实际打款后写入」。

#### 3. 关键口径（下次改前先读）

- **封顶是「用户 × 周期」而不是「结算单 × 周期」**：`Σ payables` 必须是该用户该月**所有任务**的结算单之和，按单条结算单算封顶会让人多做多得、上限失效。
- **期初余额只取最近一条上期明细的 `amount`，不能求和多行**：明细存的是「该期期末累计未发放」（已把期初算进待发额），多行求和会把滚存重复计一次。
- **算期初时不看 `allowance_detail.status`**：重算某期时 status 可能已被改写，依赖「PENDING 才算」会在二次重算时把期初余额丢掉。
- **贪心分摊必然让额度耗尽后创建的单显示 0**——这是封顶的真实反映。不选按比例分摊是因为会有分币舍入残差（`Σ 行实发 ≠ 当月实发`），且新增一张结算单会改变所有历史行的值。
- **自动路径不看任务状态，手动路径仍看**：审核是业务真实终点；运营显式归集保留「任务已完成」前置是刻意的严谨性，不是遗留。

#### 4. 踩坑

- **测试库是 session 级共享**（`conftest` 只建一次），而发放口径依赖「该用户该期的全部结算单 + 上期账本」，早先的用例会污染后面的用例——第一版新增的 7 条发放测试全红，原因不是算法错而是脏数据。解法是加 `_reset_payout_state(user_id)` 用同步 `engine.begin()` 清掉该用户的结算/津贴/额度，比改断言值可靠。
- **`pnpm` 不在 PATH**：前端校验改用 `./node_modules/.bin/{vue-tsc,eslint,stylelint,vitest}` 直跑。
- `prettier --check` 对改动过的两个 `.vue` 不通过，但 `git show HEAD:` 取出改前版本同样不通过——仓库既有状态（`lint:prettier` 脚本本身是 `--write`），没有顺手格式化以免制造无关 diff。

#### 5. 验证

- 后端：`uv run pytest` **335 passed**（新增/改写 9 条：封顶全额、超限截断+滚存入账、同月两任务共享一次封顶且 `Σ paid_amount == 实发`、上期滚存计入下期待发、重复归集幂等、审核即 SETTLED、手动归集仍要求 COMPLETED、归集失败不回滚审核、驳回不产生结算单）；`uv run ruff check` 通过。
- 前端：`vue-tsc --noEmit --skipLibCheck` 通过；`eslint` / `stylelint` 0 error；`vitest` 41 passed。
- 浏览器实机未点验二次确认与「发放结果」页签。

---

### 2026-11-01 — 「审核完还是空的」收尾：历史补算脚本 + 用户摘要 + 两个误导性标签

#### 1. 现象与真相

功能上线后运营反馈「结算管理和发放管理还是空的」。查库后确认**不是代码没生效**（新路由 `/market/payout/results` 已 200），而是数据状态：

- `market_submission` 里 2 条 `APPROVED` 都产生在改动**之前**，自动归集不会回溯；`market_task` 全是 `PUBLISHED/DRAFT`，手动「归集结算」又被「仅已完成可归集」挡住——两头都堵。
- `market_payout_config` 0 行，「发放管理」默认停在「发放额度配置」页签，看起来当然还是空。

#### 2. 改法

- **新增 `app/scripts/backfill_settlement.py`**（幂等、缺省 dry-run、`--apply` 落库）：把所有 `APPROVED` 成果按 `(任务, 月份)` 重放归集，`require_completed=False`。已在 dev 库执行，得到 2 条结算单（2000 / 100，同属 user 3 / 2026-10），`发放结果` 显示 `应发 2100 / 实发 2100 / 滚存 0`。
- **C 端用户标识：后端带摘要**。新增 `apps/modules/market/member.py`：`MarketUserBriefSchema{id,name,username,mobile}` + `load_user_briefs(db, ids)` 批量查询；`SettlementOutSchema` 与 `PayoutResultOutSchema` 增 `user`，前端结算/发放结果展示「昵称 + 手机号」，拿不到才回退 `#id`。**不新增 `market_member` 表、也不给 `sys_user` 加 `user_no`**：手机号已是业务识别手段，编号层的收益（改名后追溯）不值这个成本。
- **修两个误导性标签**：结算单「已付金额」改「实发金额」、`SCHEDULED` 显示「待打款」（一期不打款，叫「已付」是错的）；「发放管理」默认页签改成「发放结果」（额度配置天然可为空，先看到数据才不会被当成页面坏了）。
- 端到端验了一次真实链路（C 端提交 → 审核通过 → 响应带回 `settlement{payable,paid,rollover}`），**验证数据已清理**（含它自动建的机构与产品、并把分派状态回退），只留补算产生的真实记录。

#### 3. 在真库里验证过什么

- `GET /market/settlements/list` → 2 条，带 `paid_amount` / `pay_status=SCHEDULED` / `user{普通用户,13800138002}`
- `GET /market/payout/results` → 1 条：`2026-10 应发 2100 / 期初 0 / 额度 20000 / 实发 2100 / 滚存 0`
- `uv run pytest` → 336 passed（新增 1 条锁用户摘要）；`vue-tsc` / `eslint` 通过

#### 4. 口径

- **升级后必须手动跑一次补算脚本**，否则历史已通过成果永远不会进结算与发放。这是刻意的：隐式写财务数据比多一条命令危险。

---

### 2026-11-01 — 新增 C 端成员档案 `market_member`：身份与权限分开

#### 1. 原因

运营问「以后新增用户，怎么知道是 C 端还是 B 端」，顺着查下去发现现状比「没有标识」严重：

- 只有一张 `sys_user`，运营与 C 端共用，靠 `sys_user_roles` 多对多挂角色；**代码里没有任何地方判定 C 端**。
- `/market/mini/*` 全部只校验 `get_current_user`（登录即可），没有角色校验。
- 微信小程序首次登录走 `auto_register_login_user`，默认角色是 `OAUTH_DEFAULT_ROLE_IDS = [2]`，而**角色 2 是「管理员」**（`data_scope=3` 全量数据）。也就是说每个微信注册的 C 端用户都被授了管理员权限，一旦登录 Web 端就是管理员菜单。

根因是**身份与权限混在一个概念里**：角色是多对多，用它推断「是不是 C 端」必然模棱两可。

#### 2. 改法

- **新增 `market_member`**（`user_id` 唯一 + `member_no`(U-NNNN) + `status`）：**存在档案 = 是 C 端**。market 域自建，不侵入基座 `sys_user`。
- **三条建档路径，全部幂等**：
  1. `/market/mini/*` 的认证依赖从 `get_current_user` 换成 `require_market_member`（15 处），首访 lazy ensure；
  2. 微信登录编排里 best-effort 补一手（**延迟 import**，基座不硬依赖定制域，失败不影响登录）；
  3. 运营端「成员管理」页手动纳入已有用户。
- **修提权漏洞**：`OAUTH_DEFAULT_ROLE_IDS` 默认值 `[2]` → `[3]`（普通用户），并加注释说明它是角色主键、部署时可用环境变量覆盖。
- **停用的成员直接拒绝 C 端接口**（含读），不会因再次访问自愈回启用。
- **编号**：`NumberPrefix.MEMBER = "U"`，复用 `numbering.next_code` 的原子计数器。
- **运营端**：`/market/members/{list,detail,create,update}` + 前端「市场管理 → 成员管理」页（纳入/启停）；结算单、发放结果、成员列表的出参统一带 `user{id,name,username,mobile}` 摘要。

#### 3. 上线步骤（重要，少一步页面就是空的）

1. 启动即自动生成迁移（本次为 `market_member` 建表），确认 `alembic_version` 已推进；
2. `PYTHONPATH=. uv run python -m app.scripts.backfill_member --apply` —— 按**行为证据**（接过单/提交过成果/有津贴结算记录）给存量 C 端用户建档；
3. `PYTHONPATH=. uv run python -m app.scripts.sync_member_menu --apply` —— 把「成员管理」菜单写进已有库（种子导入是「表有数据就整体跳过」，改 `sys_menu.json` 只对新库生效）；
4. 非超管角色还需在「角色管理」里勾选新菜单（超管无需授权）。

#### 4. 踩坑

- **`status_code=` 静态护栏**：`tests/test_error_code_single_source.py` 只白名单「以 `@Router.xxx(` 开头的那一行」，多行装饰器里换行写的 `status_code=201` 会被判违规。保持创建类接口的装饰器写成单行（与 payout 一致）。
- **`member.py` 撞名**：先把用户摘要写成 `market/member.py`，随后要建 `market/member/` 包放模型，二者不能共存——把摘要挪进 `member/brief.py`，由 `member/__init__.py` 重新导出，调用方无感。
- **测试库共享**：成员表同样受 session 级共享影响，用例里用 `_delete_member(user_id)` 从「未建档」开始，而不是假设空表。

#### 5. 验证

- `uv run pytest` **341 passed**（新增 5 条：首访建档、重复访问仍单条、停用被拒且不自愈、纳入幂等 + 列表带用户摘要、成员编号不重复）；`uv run ruff check` 通过。
- 真库（dev）核对：`GET /market/members/list` → `U-0001 / ACTIVE / 普通用户 / 13800138002`；菜单 `成员管理` 已写入（id 216–219）。
- 前端：`vue-tsc` 通过；`eslint` / `stylelint` 0 error；`vitest` 41 passed。浏览器实机点验未做（Playwright profile 被占用）。

---

### 2026-11-01 — 补齐市场管理菜单图标

#### 1. 现象

「市场管理」树里只有 4 个目录（类型 1）有图标，**12 个页面菜单（类型 2）全是 `icon: None`**，侧栏是一排空白。
对比其它模块（系统管理/监控管理）所有类型 2 菜单都带 `ri:*` 图标——所以这是市场域补功能时漏掉的，不是设计。

#### 2. 改法

- `sys_menu.json` 给 12 个类型 2 节点补 Remix Icon（`ri:` 前缀，项目自带 `@iconify-json/ri`，离线可用）：
  项目 `folder-chart-line` / 报告管理 `file-chart-line` / 医药公司 `building-line` / 任务 `list-check-2` /
  任务审核 `shield-check-line` / 任务目录 `list-unordered` / 结算管理 `calculator-line` /
  发放管理 `hand-coin-line` / 机构管理 `building-2-line` / 图片归集 `image-2-line` /
  产品库 `medicine-bottle-line` / 成员管理 `team-line`。
- 新增 `app/scripts/sync_menu_icons.py`：按「父路径/名称」匹配，**只覆盖 icon 一个字段**，不动运营手改过的排序/名称。
  原因同 `sync_member_menu.py`——种子导入是「表有数据就整体跳过」，改 `sys_menu.json` 只对新库生效。

#### 3. 口径

- **图标名必须先确认在随包图标集里**：`node_modules/@iconify-json/ri/icons.json` 是离线来源，
  写一个不存在的名字侧栏只会渲染空白，且不报错。补图标时先拿这份 JSON 校验。
- 每个类型 2 页面配**互不相同**的图标；同模块内重复会在侧栏里看不出层级。

#### 4. 验证

- `python -m app.scripts.sync_menu_icons --apply` → 12 条全部更新；
  递归查询 `sys_menu` 后市场管理树下 17 个 1/2 级节点图标全部非空。

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

20. **`@wot-ui/router` 的 `router.push({ name, query })` 会静默丢弃 query → 详情页加载失败**（2026-10-30）
   - 现象：小程序任务大厅/我的任务点卡片进详情页，详情页显示「加载失败」，后端日志没有任何详情请求（`/mini/tasks/{id}`、`/mini/assignments/{id}`）。逐层排查发现页面跳转成功、`onLoad` 也触发，但 `query` 为空——`@wot-ui/router` 的 `resolve` 在 `to.name` 分支误写 `const finalQuery = to.params || {}`（应为 `to.query`），把 query 当成 params 丢弃，跳转 URL 无参数。
   - 结论：凡需跨页传参的跳转，用 `router.push({ path: '/完整路径', query: {...} })`（走 `resolvePath` 分支，query 正确序列化到 URL），**不要用 `name`**。`name` 分支只适合无参跳转。同根因的还有工单详情（`tickets → ticket-detail`），已一并修复。

21. **「列存在、没人写」的字段在运营端永远是空的——`OutSchema` 漏一个嵌套对象就够**（2026-11-01）
   - 现象：成果审核弹窗里「机构 / 对象名称 / 档案号 / 区域」四格全空。逐个查证：`institution` 只有 `institution_id`、`SubmissionOutSchema` 没有 `institution` 字段（前端写 `institution.name` 永远取不到）；`subject_name` / `region` / `archive_no` 在 model、schema、前端都存在，但**全库没有任何代码写入**（C 端只提交 `form_data`，`archive_no` 连编号前缀都没定义）。同一弹窗里采集数据还全是英文字段名——前端当时只有硬编码的分节名映射，字段名/子表列名无映射。
   - 结论：① 排查「页面空」先分清**三件事**——出参 Schema 有没有这个字段、DB 里有没有值、有没有代码写过它；只补前端渲染是最常见的错误修法。② C 端只提交 `form_data` 时，运营端要展示的摘要列（对象名称/区域）应由**后端**从 `form_data` 推导落库，不要让前端拼；存量行用「读详情时只补空值自愈」代替迁移脚本。③ `form_data` 的英文 key → 中文标签**只能查任务自带的 `form_schema`**（`detail` 接口回填），禁止在前端维护第二份静态映射表（与硬口径 4 同源）。

22. **共享测试库上测「按用户 × 周期聚合」的口径，必须自己清表——否则红的是脏数据不是逻辑**（2026-11-01）
   - 现象：新写的 7 条发放算法测试首轮全红，失败信息看着像算法错（比如「应发 == 实发」不成立、结算单条数对不上）。实际原因是 `conftest` 的测试库只建一次（session 级共享），前面用例给同一个 `user` 账号留下了 2026-11 的结算单与津贴账本，而发放口径依赖「该用户该期的**全部**结算单之和 + 上期账本」——脏数据把每条断言都顶偏了。
   - 结论：凡测试依赖「某用户某周期的全量聚合」，开头必须先 `_reset_payout_state(user_id)`（同步 `engine.begin()` 直删 `market_settlement` / `market_settlement_item` / `market_allowance` / `market_allowance_detail` / `market_payout_config`）。不要靠改断言值迁就——那会把「跨任务共享封顶」这个真正被测的行为一起改掉。
