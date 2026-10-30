---
id: market-domain
type: module-design
status: draft
title: market 域 —— 职责、边界与子模块依赖
parent: foxwork-architecture
---

# market 域

## 职责

把医药市场服务的业务全流程收在一个域里：任务目录（分类/模板/三级任务）→ 项目与任务单元 → 任务实例与分派 → 成果提交与审核 → 归集结算与发放 → 月度报告；外加机构主数据与图片归集、运营看板。

域根目录同时占地四份**全域共享契约**，子模块只消费、不各自重定义：

| 文件 | 契约 |
|---|---|
| `enums.py` | 所有状态机与类型枚举的唯一取值来源 |
| `config.py` | 任务配置 JSONB 的 Pydantic 权威定义（`TaskConfig` / `TaskItemConfig` / `SubmitRule`） |
| `form_schema.py` | 动态采集表单的结构定义（`FormSchemaSection` → `FormSchemaField` / `FormSchemaColumn`） |
| `numbering.py` | 业务编号 `{PREFIX}-{NNN}` 的 PG 计数器表原子分配 + `sync_counter` 对齐种子 |

另有 `models.py` 作统一注册入口（解决 `TYPE_CHECKING` 下的循环外键，供脚本与测试一次性 import 全部模型）。

## 边界

- **只依赖** `app/core/*`、`app/common/*`、`app/modules/common/file`（图片上传）。不 import 其它业务域；`sys_user.id` 是唯一的外部外键引用。
- **子模块一律继承 `MarketCRUDBase`** 而不是 `CRUDBase`：它覆写 `_build_conditions`，跳过基座的 `created_id` 行级数据权限。理由与代价见 [architecture](../architecture.md) 的「权限分两层」——归属过滤必须由 Service 层显式写。
- 运营端接口挂 `module_market:<resource>:<action>` 权限码；C 端聚合入口 `mini_controller.py`（前缀 `/market/mini`）只校验登录，不要求运营权限码。
- 表名统一 `market_` 前缀；主键是 `Integer` 自增，`uuid` 是 `ModelMixin` 带来的独立列，**不是主键**（`docs/02` 说的 UUID 主键已不存在）。

## 子模块与依赖边

| 子模块 | 拥有的表 | 依赖（引用谁） |
|---|---|---|
| [market/task](task/SPEC.md) | `market_task_category` `market_task_template` `market_task_item` `market_task` `market_assignment` `market_submission` | project（`project_id`）、institution（`institution_id`） |
| [market/project](project/SPEC.md) | `market_company` `market_project` `market_project_item` `market_report` | task（`market_project_item` 指向三级任务或叶子模板） |
| [market/payout](payout/SPEC.md) | `market_settlement` `market_settlement_item` `market_payout_config` `market_allowance` `market_allowance_detail` | task（读任务与成果做归集） |
| [market/institution](institution/SPEC.md) | `market_institution` `market_institution_image` | 无（被 task 引用） |
| [market/dashboard](dashboard/SPEC.md) | 无自有表 | 全部（只读聚合） |

`task ↔ project` 是**双向边而非循环依赖**：任务带 `project_id`（任务侧按项目筛选），项目带 `market_project_item`（项目侧决定发布哪些任务单元）。两条边服务两条不同的聚合路径，对应「项目对外、任务对内」。

`mini_controller.py` 是 C 端接口的聚合路由（任务大厅、我的任务、接单、提交成果、我的收益、机构列表），它不是子模块：没有自有表，只做参数适配与权限降级，业务逻辑都在 task / payout / institution 的 Service 里。

## 状态机

取值定义在 `enums.py`，service 以 `.value` 字符串写入。状态流转都是**单向**的，由各 Service 自己校验顺序。

| 实体 | 状态链 |
|---|---|
| 项目 `ProjectStatus` | DRAFT → IN_PROGRESS → COMPLETED → CLOSED |
| 任务 `TaskStatus` | DRAFT → PUBLISHED → IN_PROGRESS → COMPLETED → SETTLED → ARCHIVED |
| 分派 `AssignmentStatus` | PENDING → ACCEPTED → SUBMITTING → SUBMITTED → REVIEWED → SETTLED |
| 成果 `SubmissionStatus` | DRAFT → PENDING → APPROVED / REJECTED（驳回可改，`version` +1） |
| 结算单 `SettlementStatus` | PENDING → CALCULATED → CONFIRMED → REPORTED → PAID |
| 报告 `ReportStatus` | DRAFT → GENERATED → SUBMITTED |
| 津贴明细 `AllowanceStatus` | PENDING → PAID |

三个**只有枚举值、没有写入路径**的状态要当心，不要以为业务已覆盖：

- `TaskStatus.SETTLING`：`TaskService.change_status` 允许的链是 PUBLISHED → IN_PROGRESS → COMPLETED → SETTLED → ARCHIVED，跳过 SETTLING；`SettlementService.settle` 只校验任务处于 COMPLETED，不推进任务状态。
- `SettlementStatus.PAID`：没有支付实现（支付是非目标）。
- `AllowanceStatus.PAID`：同上，津贴明细只被读。

## 已知取舍

- `market/task/service.py` 单文件承载 6 个 Service（分类/模板/三级任务/任务实例/分派/提交，900+ 行），是域内唯一的改动热点；拆它牵动全部 task 路由，改动前先确认要不要动结构。
- 编号计数器表 `market_number_counter` 的主键不是 `Integer` 而是 `prefix` 字符串——它是唯一一张不走 `ModelMixin` 的表。
