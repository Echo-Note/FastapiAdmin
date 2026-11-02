---
id: market-product
type: submodule-design
status: active
title: market/product —— 产品库与成果提交的自动填充/自动入库
parent: market-domain
---

# market/product

## 职责

维护产品主数据（产品名称 / 产品规格 / 生产企业三要素），让 C 端提交成果时按产品名称检索并自动回填其余两要素，免去每月重复手写；并把 C 端提交里库里没有的产品自动入库为待审记录，由运营审核后放行。

## Boundary

- 「表单里哪些列是产品三要素」由 [market/task](../task/SPEC.md) 的 `form_schema` 决定（`FormSchemaColumn.product_role`）；本模块只消费 schema，不定义字段。
- 「成果什么时候产生」由 task 的 `SubmissionService` 决定；本模块只提供 `ingest_from_form_data` 钩子，不插手成果状态机。
- 只依赖 `app/core/*` 与 `app/utils/*`（`sys_user.id` 是唯一外部外键引用）。
- 权限码：`module_market:product:{query,create,update,delete,audit}`（运营端）；C 端检索走 `/market/mini/products/search`，只校验登录。

## 判重键就是三要素

`market_product` 上的 `UniqueConstraint(name, spec, manufacturer)`（`uq_market_product_name_spec_manufacturer`）是全模块的核心不变量：

- 三者全等 = 同一个产品；同名不同厂商、同厂商不同规格都是各自独立的记录。
- 因此 C 端检索命中多条是**正常且预期**的，必须让用户选择，而不是替用户拍板。
- `spec` / `manufacturer` 用空串而非 NULL 兜底，否则唯一约束在 PG 下对 NULL 不生效（NULL 彼此不冲突）。
- 运营端录入/改名撞键时先给出可读文案（`_ensure_not_duplicated`），唯一约束是最终兜底。

## 来源与审核

**「谁产生的这条记录」用审计字段表达**：`created_id` / `created_by`（`UserMixin` 自动填充，`UserBySchema` 自动透出）。不设 `source` 之类的来源枚举——运营录入与 C 端提交都是具体的人，硬编码两档字符串既丢失身份，又会在接入导入、外部主数据等新来源时立刻失效。

审核状态机 `audit_status`：`pending` / `approved` / `rejected`（`ProductAuditStatus`）。

| 场景 | audit_status | 谁能检索到 |
|---|---|---|
| 运营新增/修正 | `approved`（录入即生效） | 所有人 |
| C 端提交自动入库 | `pending` | 仅提交人（`created_id`）自己 |
| 运营通过 | `approved` | 所有人 |
| 运营驳回 | `rejected` | 无人（记录保留可追溯） |

可见性规则落在 `ProductService.search` 一条 SQL 里：`approved` **或**（`pending` 且 `created_id = 当前用户`）。`rejected` 永不出现在任何检索结果里。

驳回必须填写审核意见（`ProductAuditSchema` 的模型校验，422），避免提交人不知道为什么被拒。

**审核动作只对 `pending` 记录开放**：运营录入的产品落库即 `approved`（`reviewer_id` 记为录入人），运营端列表里不显示「通过/驳回」；只有 C 端自动入库的待审记录才出现这两个动作，避免把「运营录入」也误当成需要审批的对象。

## 自动入库

- 挂接点：`SubmissionService.create`（新提交）与 `update`（驳回重提）在成果落库后调用 `ProductService.ingest_from_form_data(form_data, form_schema)`。
- 列名解析：优先用 `form_schema` 里的 `product_role`（`resolve_product_columns`），老数据没有该标记时回退约定列名 `product_name` / `product_spec` / `manufacturer`。
- 行提取：`iter_submitted_products` 递归遍历 `form_data`（分节 dict → 子表 list[dict]），取「产品名称非空」的行，同一次提交内三元组去重；**名称有值但规格与生产企业都为空的组合跳过**——没有可回填的内容，入库只会污染候选列表（只缺其中一项照常入库）。
- 幂等：判重键已存在则跳过——**包括已 `rejected` 的**，不让同一份脏数据每次提交都重生一条待审记录。
- 失败隔离：每条入库包在 `begin_nested()` savepoint 内，碰撞唯一约束只跳过该条，绝不会因为产品入库失败而回滚成果本身。
- 产品待审不影响成果审核：两条流程互不阻塞。

## 接口

运营端 `ProductRouter`（前缀 `/products`，挂在 `routers.py` 的 `/market`）：

| 方法 | 路径 | 权限码 |
|---|---|---|
| GET | `/market/products/list` | `module_market:product:query` |
| GET | `/market/products/detail/{id}` | `module_market:product:query` |
| POST | `/market/products/create` | `module_market:product:create` |
| PUT | `/market/products/update/{id}` | `module_market:product:update` |
| DELETE | `/market/products/delete` | `module_market:product:delete` |
| PUT | `/market/products/audit`（批量，`approved` 决定通过/驳回） | `module_market:product:audit` |

C 端：`GET /market/mini/products/search?keyword=&limit=`（默认 20，上限 50），返回仅 `id` / `name` / `spec` / `manufacturer` / `display_name`，不暴露审核字段。

## 前端

- 运营端：`views/module_market/product/index.vue` + `api/module_market/product.ts`，菜单「市场管理 → 产品库」（`/market/product`，`MarketProduct`）。审核是单条与批量共用同一弹窗，行操作按状态收敛（已通过不给「通过」、已驳回不给「驳回」）。
- C 端：`subPages/module_market/submission-form/index.vue` 里 `product_role=name` 的列停顿 500ms 或失焦后检索：**有匹配就弹半屏候选列表（命中 1 条也弹）**，行内另给「查产品库」强制列候选；未命中保留手填。
  - **自动回填**：仅当候选名称与输入完全相等且唯一时自动回填名称/规格/生产企业，模糊命中只列候选、由用户手动选，避免把正在输入的片段改写掉。
  - **选中回填**：名称归一为候选全名，规格/生产企业按候选写入同行；候选缺其中任一项时只回填名称（空值不覆盖用户已填内容），行内提示「信息不完整」并高亮，不再谎报「已填充规格与生产企业」。
  - **关闭语义**：用户取消候选后，同一行同一关键词的失焦检索不再重弹；重新输入或点「查产品库」恢复；关闭/选中会作废在途检索，避免旧响应把弹窗重新打开。

## 已知取舍

- **不做** Excel 批量导入导出、产品合并/去重建议、外部药监主数据对接、把产品库回写进已提交的 `form_data`。
- 存量环境不会自动获得「产品库」菜单：`initialize.py` 的种子导入只在表为空时执行，已初始化的库需在「菜单管理」补一次（或直接插入 `sys_menu`）。
- 产品与项目/厂商没有关联字段：一期只做三要素字典，避免过早引入厂商主数据。
- 判重键撞上了软删除的记录时仍会报「产品已存在」——与基座其它 `unique=True` 的 `code` 列表行为一致。
- 产品名称联想**不做**行内下拉浮层，沿用半屏候选列表（与「查产品库」同一个 `wd-popup`）。
- 历史遗留的「名称-only」待审记录不清理、不合并：检索仍可能返回这类候选，选中后只回填名称并提示信息不完整。
