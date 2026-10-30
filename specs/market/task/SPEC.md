---
id: market-task
type: submodule-design
status: draft
title: market/task —— 任务目录、发布、分派、成果提交与审核
parent: market-domain
---

# market/task

## Responsibility

任务目录三级（分类 → 模板 → 三级任务）的维护、任务实例的创建与发布、分派与接收、成果的提交与审核。C 端「任务大厅 / 我的任务 / 接单 / 提交成果」的能力全部由本模块的 Service 提供，由 `mini_controller.py` 暴露。

## Boundary

- 「任务单元是谁」由 [market/project](../project/SPEC.md) 决定（项目上挂哪些三级任务/叶子模板），本模块只管把这些单元变成可执行的 `market_task`。
- 「成果值多少钱」由 [market/payout](../payout/SPEC.md) 计算，本模块只提供审核通过的成果与任务单价配置。
- 机构实体归 [market/institution](../institution/SPEC.md)，本模块只存 `institution_id`。
- 权限码：`module_market:{task_category,task_template,task,assignment,submission}:{query,create,update,delete}`，另有 `task:publish`（单个/批量发布）与 `submission:review`（审核）。

## 三级目录是真相

一级分类 `market_task_category` → 二级模板 `market_task_template` → 三级任务 `market_task_item`，三级都靠 `config` JSONB 承载设计。

- **配置归属规则**：模板的 `TaskConfig` 承载计价单位/单价/计价方式/执行标准/执行人员要求/提交规则/是否需月报，以及（**仅当该模板没有三级任务时**）采集表单 `form_schema`。三级任务的 `TaskItemConfig` 承载自己的采集表单，并可覆盖单位/单价/执行标准/执行人员要求/单月频次上限。
- 有三级任务的模板不承载采集表单——否则 C 端会拿到一份没有字段可填的空表单。这条规则在两侧都强制：`ProjectService._ensure_template_exists` 在关联入口拦截，`TaskService._get_leaf_template` 在建任务入口拦截。
- **文档订正**：`docs/06-任务模块重新设计.md` 的 D2 声称「两级任务层级、共 22 个模板」，但代码与种子是三级（6 分类 / 18 模板 / 51 三级任务），且 `docs/06` D1 里的 `ExecMode` / `exec_modes` 在代码中不存在。本 spec 以三级为准。

## 任务实例

`market_task` 是执行的最小单元，细到三级任务粒度：

- `project_id` + `template_id` 必填，`item_id` 为空的含义是「这个模板是叶子模板，任务就挂在模板级」。
- `name` 由后端拼装：`{项目名}-{模板名}-{三级任务名}`，叶子模板为 `{项目名}-{模板名}`。C 端直接展示，不再二次拼装。
- `period` 继承项目截止日期；`assign_mode` 是 `direct` / `open`。
- **只有 DRAFT 可改可删**；状态只能单向推进。编号 `TK-NNN` 由 `numbering.next_code` 分配，不可修改。

## 发布与分派解耦

发布（`publish` / `batch_publish`）**只做状态流转** DRAFT → PUBLISHED 并写发布人/时间，不生成任何分派。分派是独立动作：运营定向分派（`batch_assign` / `batch_assign_multi`）会把任务分配方式改为 `direct`；大厅任务由 C 端 `claim` 自行生成分派。

## 大厅接单是幂等防重，不是占名额

`assignment.claim` 的语义要精确理解，这条曾经被误传：

- 接单为当前用户创建一条 `source=claimed`、`status=ACCEPTED` 的分派（大厅接单即视为已接收，不同于定向分派的 `PENDING` 待接收）。
- **幂等**：同一用户对同一任务已有 claimed 分派则直接返回那条，不重复创建。
- **不改任务的 `assign_mode`**：任务仍是公开大厅，其他用户仍能看到并接单；只对当前用户隐藏（大厅查询按「当前用户是否已领取」过滤）。
- Redis 上只有一次 `incr` 计数，**不是配额闸门**：任务没有名额字段，不存在超卖保护对象。

## 成果提交与审核

- 一次提交 = 一个采集对象 × 一份采集表单，`period` 存月份字符串（如 `2026-03`）用于按月归集。
- 采集数据存 `form_data` JSONB，结构由任务自带的 `form_schema` 决定；`ai_check_status` / `ai_check_result` 是为 AI 预检预留的列，当前没有写入路径。
- 审核（`review`）走向 APPROVED / REJECTED，记审核人/意见/时间；驳回后用户修改重提，`version` +1。
- 审核通过后分派回写为 `SUBMITTED`（`review` 里写 `SUBMITTED` + `submitted_at`）。`SUBMITTING` / `REVIEWED` / `SETTLED` 三个枚举值虽然定义了，但**当前没有任何写入路径**，结算也不回写分派（2026-11 核对，本条已按代码订正）。
- 提交后的成果状态是 `DRAFT`（`create` 不传 `status`，走模型默认），没有「提交即 `PENDING`」这一步；`review` 接受 `DRAFT` 与 `PENDING` 两种入参。
- 「单月单对象只提交一次」目前**没有数据库唯一约束兜底**（`market_submission` 上没有 `UniqueConstraint`），只有业务层校验；并发重提不受阻。

## 运营端任务列表与侧边栏目录

- **任务列表默认包含草稿**。项目发布只创建 `DRAFT` 任务实例，需要运营再逐条/批量「发布」；列表页曾经硬编码 `exclude_status=DRAFT`（初始参数与刷新条件各一处），导致「发布项目后任务页是空的」——现已去掉，靠状态筛选显式过滤。
- **侧边栏目录只显示确实有任务的（分类, 模板）**。树节点来自 `TaskCategoryService.tree()`（完整主数据 6 分类 / 18 模板），与任务是否存在无关，空库时会显示一整棵没有任务对应的目录；`GET /market/tasks/facets` 返回 `[{category_id, template_id, task_count}]`，前端据此裁剪节点并显示任务数，任务增删后刷新（页面 `keep_alive`，用 `onActivated` 覆盖从项目页发布后切回的场景）。
- 「任务目录」菜单页（`/market/task-catalog`）仍是三级目录的主数据维护页，**故意**展示完整目录——它是配置来源，不跟随任务清空。

## 采集表单与真实采集表对齐

- `form_schema` 的字段来源是运营手上的真实 Excel 采集表（`docs/materials/任务/...`），不是开发臆造的结构；机构管理 5 类共 26 个三级任务（`ITEM-0001`..`ITEM-0026`）的字段定义收敛在 `backend/app/modules/market/task/collection_schema.py` 的 `ITEM_FORM_SCHEMAS`。
- 该模块**只是种子与存量订正的生成源**，运行时真相仍是库里 `config.form_schema`。订正入口 `app/scripts/apply_collection_schema.py`（`--seed` / `--db` / `--dry-run`，幂等，`--db` 深拷贝后回写因为 JSONB 列 `mutable=False`）。
- 分节顺序与采集表一致：`execution_info`（区域 + 机构类型专属字段 + 执行人自动填充 + 执行日期）→ 工作区分节（`type=table` 多行子表 + 表后 `exception_note` 异常说明）→ `management_verification`（门头照片）。
- **字段 key 是已提交成果 `form_data` 的结构契约**：退役语义的旧 key 不复用（库存盘点 `stock_qty`=库存数量，新的「实盘数量」用 `actual_qty`）。
- 竞品调研的行刻意用 `competitor_name` / `competitor_spec` / `competitor_manufacturer`，不复用产品三要素 key —— 否则竞品会被 C 端当成自家产品检索、并被自动写进产品库（见 [market/product](../product/SPEC.md)）。
- 产品三要素列（`product_name` / `product_spec` / `manufacturer`）带 `product_role`（`name` / `spec` / `manufacturer`），C 端据此触发产品库联想与回填。
- 素材里没有采集表的三级任务（`ITEM-0027` 进销存数据收集、`ITEM-0028` 流向数据收集）不做臆造，保持原样。App 侧子表单元格按列类型渲染（`date` / `number` / `select` / `image` / `file` 各用对应控件），不再一律文本输入。

## 已知取舍

- 6 个 Service 同处一个 900+ 行的 `service.py`。改任一处都要通读全文件，是域内最高风险点。
- 大厅可见性（`_hall_visibility_search`）与「我的任务」分组（`grouped_my_assignments`）是两套不同的查询口径，改一个容易忘记另一个。
