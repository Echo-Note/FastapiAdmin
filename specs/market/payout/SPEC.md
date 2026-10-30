---
id: market-payout
type: submodule-design
status: draft
title: market/payout —— 归集结算、发放额度与津贴账户
parent: market-domain
---

# market/payout

## Responsibility

三件事，三张面孔，别混：

1. **归集结算**：把某任务下每个用户当月审核通过的成果汇总成结算单 + 明细。
2. **发放额度配置**：每个用户每个月的发放上限（默认 20000）。
3. **津贴账户**：个人未发放金额的累计账户与明细的查询展示。

## Boundary

- 读 [market/task](../task/SPEC.md) 的任务与成果做归集，不写它们的业务状态（`settle` 不推进任务状态，只要求任务处于 COMPLETED）。
- 单价来自任务的二级模板 `TaskConfig`（`unit` / `price`），本模块不维护价目表。
- 不发起支付、不动账户余额——支付是非目标。
- 权限码：`module_market:settlement:{query,run,confirm}`、`module_market:payout:{query,create,update,delete}`。

## 结算口径

`SettlementService.settle(task_id, period)`：

- **前置**：任务必须是 COMPLETED（运营先判定完成），否则拒算。
- **归集粒度**：任务 × 用户 × 月份。对该任务下每条分派，统计 `assignment_id + status=APPROVED + period` 的成果数；0 条则不生成结算单。
- **金额**：`payable = 单价 × 通过数`，无上限。单价与单位**只读二级模板的配置**，不读三级任务的覆盖值——若某三级任务覆盖了单价，结算仍按模板价。这是当前实现的真实口径，改动前先确认是缺陷还是刻意（未确认）。
- **幂等**：同 `task_id + user_id + period` 已有结算单则跳过，重复执行不会重复开单。
- **落库结构**：`market_settlement`（头：`qty` / `payable_amount` / `paid_amount` / `pay_status` / `status`）+ `market_settlement_item`（行：`category_name` / `template_name` / `unit` / `price` / `qty` / `amount`）。明细是**名称快照**，不是外键——模板改名不会回溯改历史结算单。
- 新建结算单直接落 `CALCULATED`；`confirm` 把 PENDING / CALCULATED 推到 CONFIRMED。

## 已知缺口（已确认，勿当成已实现）

**发放封顶与津贴滚存没有实现。** 缺的是这套规则：

```
① 当月应发 pending = 该月所有结算单 payable 之和
② 实发 paid    = min(pending, 该用户该月的 payout_limit)
③ 滚存 next    = max(0, pending - payout_limit)，累加进个人津贴账户，下月继续参与 ①②
```

代码现状：

- `settle` 只算到 ①②之前的 `payable`，`paid_amount` / `pay_status` 是预留空列。
- `payout_limit` **只被 `PayoutService.my_payout` 用于展示**，不参与任何计算。
- `market_allowance` / `market_allowance_detail` 只有读路径（`AllowanceService.detail/page/detail_page`、`my_payout`），**没有任何写入路径**——`AllowanceCRUD.create` 无调用方，两张表恒为空。
- 因此 C 端「我的收益/津贴」当前只能展示额度配置与空账户。`docs/02` §5 的发放算法是设计，不是现状。

## 已知取舍

- 结算单与明细都没有 `user_id` 之外的人员快照；用户改名会影响历史展示。
- 一个周期内重复调 `settle` 是安全的（幂等），但**改了成果审核结果后不会重算已有结算单**——需要先删结算单再重跑，界面未提供该入口。
