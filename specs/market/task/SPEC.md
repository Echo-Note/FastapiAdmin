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
- 审核通过后分派推进到 `REVIEWED`，结算完成后才到 `SETTLED`（由 payout 侧驱动）。

## 已知取舍

- 6 个 Service 同处一个 900+ 行的 `service.py`。改任一处都要通读全文件，是域内最高风险点。
- 大厅可见性（`_hall_visibility_search`）与「我的任务」分组（`grouped_my_assignments`）是两套不同的查询口径，改一个容易忘记另一个。
