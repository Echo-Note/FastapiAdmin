---
id: market-project
type: submodule-design
status: draft
title: market/project —— 医药公司、项目、项目任务单元与月度报告
parent: market-domain
---

# market/project

## Responsibility

维护对外交付侧的三件事：医药公司主数据、项目、以及项目与「任务单元」的关联；再按项目聚合出月度报告。项目是**对外**的交付与结算单元，任务是**对内**的执行单元。

## Boundary

- 任务单元是谁、怎么建任务，归 [market/task](../task/SPEC.md)。本模块只持有 `market_project_item` 这样的关联行，并在发布时调用 task 的 CRUD 生成任务实例。
- 项目**没有金额字段**：对外报价不在本系统内（见 [foxwork-goal](../../goal-and-requirements.md) 的非目标），结算金额全部来自任务单价 × 成果数量。
- 权限码：`module_market:{company,project,report}:{query,create,update,delete}`，另有 `project:publish`。

## 项目与任务单元

`market_project_item` 是项目 ↔ 任务单元的多对多关联，`item_id` 与 `template_id` **恰好一个非空**：

- 关联 `item_id` = 该模板有三级任务，关联其三级任务；
- 关联 `template_id` = 叶子模板（无三级任务），直接关联模板。

这个「恰好一个」由 `_sync_task_unit_links` 全量替换维持（改项目任务单元时先删后建，不做增量 diff）。

## 发布项目 = 批量生成任务实例

`ProjectService.publish` 做两件事，顺序不能反：

1. 遍历 `item_links`，按单元逐条生成 `market_task`（DRAFT、`assign_mode=open`、`period` 继承项目截止日期），名称按 `{项目}-{模板}[-{三级任务}]` 拼装。
2. 把项目状态推到 IN_PROGRESS。

**幂等靠逐条查重**：同 `project_id + item_id`（或 `project_id + template_id + item_id IS NULL`）已存在任务就跳过——所以重复发布不会产生重复任务实例，但也意味着改过任务单元的草稿项目重新发布会补建差额，而不是重建。

叶子模板关联在发布时会再校验一次是否为真叶子（防御历史脏数据）。

## 月度报告

`market_report` 按「项目 × 二级模板 × 月份」聚合：`summary` JSONB 存当月完成量/金额汇总，`attachment` 存报告附件路径，`template_id` 为空表示全项目汇总报告。

`ReportService.generate(project_id, template_id, period)` 是聚合入口；`create/update` 也开放，用于人工补录。报告状态 `DRAFT → GENERATED → SUBMITTED`，提交甲方是最后一步（无对外发送实现，`SUBMITTED` 是运营手工推进的状态）。

## 已知取舍

- 医药公司（`market_company`）是一张独立主数据表，无租户/账号概念——它只是项目的委托方标签，不参与权限。
- 项目没有「金额」也没有「进度百分比」，对外进度只能从任务与成果反推。
