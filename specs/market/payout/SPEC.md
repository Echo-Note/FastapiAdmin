---
id: market-payout
type: submodule-design
status: draft
title: market/payout —— 归集结算、发放封顶与津贴账户
parent: market-domain
---

# market/payout

## Responsibility

三件事，三张面孔，别混：

1. **归集结算**：把某任务下每个用户当月审核通过的成果汇总成结算单 + 明细，并在同一次计算里做发放封顶。
2. **发放额度配置**：每个用户每个月的发放上限（默认 20000）。
3. **发放结果与津贴账户**：按「用户 × 周期」展示应发 / 实发 / 滚存的核算结果，以及个人津贴账户与明细。

## Boundary

- 读 [market/task](../task/SPEC.md) 的任务与成果做归集，**不推进任务状态**（`settle` 只读任务是否已完成）。分派状态 `SETTLED` 是它唯一写回 task 域的东西。
- 单价来自任务的二级模板 `TaskConfig`（`unit` / `price`），本模块不维护价目表。
- 不发起支付、不打款、不接支付通道——支付是非目标。
- 权限码：`module_market:settlement:{query,run,confirm}`、`module_market:payout:{query,create,update,delete}`（「发放结果」查询复用 `payout:query`）。

## 归集结算

`SettlementService.settle(task_id, period, *, require_completed=True)`：

- **两个入口，一个实现**：运营手动点「归集结算」（`require_completed=True`）与**成果审核通过后自动触发**（`require_completed=False`，见下）。两处差别只有任务状态前置。
- **自动归集不看任务状态**：审核是业务真实终点，卡「任务已完成」只会让结算与发放数据一直空着；运营手动归集仍保留该前置，作为显式动作的严谨性。
- **归集粒度**：任务 × 用户 × 月份。对该任务下每条分派，统计 `assignment_id + status=APPROVED + period` 的成果数；0 条则不生成结算单。
- **金额**：`payable = 单价 × 通过数`，无上限。单价与单位**只读二级模板的配置**，不读三级任务的覆盖值——三级任务覆盖单价时结算仍按模板价（这是当前口径，改动前先确认是缺陷还是刻意）。
- **幂等靠重算，不靠跳过**：已存在同 `task_id + user_id + period` 的结算单时**更新** `qty` / `payable_amount` 并同步明细行，而不是跳过。「跳过」会让同一用户同月同一任务的第二份通过成果永远不计入，也会让审核结果变更后的金额永久停在旧值。
- **落库结构**：`market_settlement`（头：`qty` / `payable_amount` / `paid_amount` / `pay_status` / `status`）+ `market_settlement_item`（行：`category_name` / `template_name` / `unit` / `price` / `qty` / `amount`）。明细是**名称快照**，不是外键——模板改名不会回溯改历史结算单。一条结算单固定只有一行明细。
- 新建结算单直接落 `CALCULATED`；`confirm` 把 PENDING / CALCULATED 推到 CONFIRMED。

## 发放封顶与津贴滚存

按**「用户 × 周期」**整体计算，不是按单条结算单——封顶是人的月度上限，跨任务共享：

```
period_payable = Σ 该用户该 period 所有结算单 payable_amount
prev_balance   = allowance_detail 中 from_period < period 的最近一行的 amount（无则 0）
limit          = payout_config(user, period).payout_limit（缺行 / enabled=false → 20000）
pending        = period_payable + prev_balance
paid           = min(pending, limit)
balance_after  = pending - paid          # 期末累计未发放，滚入下月
```

由 `PayoutService.apply(user_id, period)` 在 `settle` 末尾对每个受影响用户调用一次，写入四处：

- `market_allowance.balance` = `balance_after`（一个用户一行）。
- `market_allowance_detail`：`from_period=period` 的一行 upsert，`amount = balance_after`。
- `market_settlement.paid_amount`：`paid` 按结算单 **id 顺序贪心分摊**，`pay_status = SCHEDULED`。
- 不写 `AllowanceStatus.PAID`——津贴明细 PAID 是二期实际打款才写的语义，一期写了会误导。

三条容易踩错的口径：

- **期初余额只取最近一条上期明细的 `amount`，不能求和多行**：明细存的是「该期期末累计未发放」，多行求和会把滚存重复计一次。
- **算期初时不看 `allowance_detail.status`**：重算某期时 status 可能已被改写，依赖它会让期初余额凭空丢失。
- **贪心分摊必然让额度耗尽后创建的单显示 0**：这是封顶的真实反映，不是缺数据。选贪心而不是按比例，是因为按比例会产生分币舍入残差（`Σ 行实发 ≠ 当月实发`），且新增一张结算单会改变所有历史行的值。

## 审核通过自动归集

`SubmissionService.review` 在 `approved=True` 落库成功后，按 `(assignment.task_id, submission.period)` 调 `settle(require_completed=False)`，并把结果包成 `SubmissionSettlementNoticeSchema{task_id, period, payable, paid, rollover, limit}` 随审核结果返回。

- **best-effort**：归集失败（模板配置损坏、模板缺失等）只记日志并把原因放进 `warning`，**不回滚审核**——审核已生效是事实，运营可稍后手动补跑。
- **响应结构是专用的**：`SubmissionReviewResultSchema{submission, settlement, warning}`，不给 `SubmissionOutSchema` 塞一个只在审核时出现的字段。
- **前端二次提醒**：结论为「通过」时先确认「通过后将立即归集结算」，归集成功后展示应发/实发/滚存并可跳结算单。这道确认是必须的——审核动作会真的产生金额。

## 对外接口

- `GET /market/settlements/list|detail/{id}`、`POST /settlements/settle`、`POST /settlements/confirm/{id}`
- `GET /market/payout/list|detail/{id}`、`POST|PUT|DELETE` 额度配置、`GET /payout/allowance`、`GET /payout/allowance/detail`
- `GET /market/payout/results`——按 `user_id` / `period` 筛选的发放结果分页，行 = 用户 × 周期，列出 应发 / 期初津贴 / 额度 / 实发 / 期末津贴。分组与分页在 SQL 侧完成。
- `GET /market/mini/payout?period=YYYY-MM`——C 端「我的收益」按月视图（见下节）。
- 结算单与发放结果的出参都带 `user: {id, name, username, mobile}`（见 [market 域](../SPEC.md) 的共享契约），前端展示「昵称 + 手机号」而不是 `#3`。

## C 端按月视图（我的收益）

`GET /market/mini/payout?period=YYYY-MM` 是 C 端「我的收益」页的唯一数据源，出参 `MyPayoutOutSchema`，
**整屏都是该周期的数**——页面顶部切月只改 `period`，不需要也不允许前端自己再筛一遍：

| 字段 | 口径 |
|---|---|
| `payable` / `paid` | 该期结算单 `payable_amount` / `paid_amount` 之和 |
| `payout_limit` | 该期额度配置；缺行/停用 → 20000 |
| `prev_balance` | 早于该期最近一条账本行的 `amount`（与归集时的 `prior_balance` 同口径） |
| `allowance_balance` | 该期账本快照 `amount`；**该期没有快照 = 还没归集结算，滚存没发生变化，等于 `prev_balance`** |
| `settlements` | 该期结算单，行内带任务来源（`task_no` / `task_name`）与计价快照（`category_name` / `template_name` / `unit` / `price` / `qty`），回答「这笔钱由哪个任务产生」 |

两条不能走回头路的口径：

- **读路径不重跑封顶公式**：`pending / paid / balance_after` 是归集时的写路径（`apply`），C 端读结算单与账本。两套算法并存必然出现「同屏实发 0、期末却按额度减过」这类自相矛盾——「该期未结算」不等于「滚存被清空」。
- **明细是结算单，不是津贴账本行**：账本行只记期末累计余额（一期一行），当明细既看不出收入来源、又会让切月前后出现「同一批行」。账本滚存由 hero 的期初/期末两个数字表达，`AllowanceDetailOutSchema` 只服务于运营端账本查询。

## 历史补算

自动归集只对**上线之后**的审核生效；上线前已经 `APPROVED` 的成果不会自己产生结算单，页面看起来就是空的（任务还可能停在 `PUBLISHED`，手动归集也会被完成前置拦住）。

处置是**手动一次性脚本**：`app/scripts/backfill_settlement.py`（幂等，缺省 dry-run，`--apply` 才写库）把库里所有 `APPROVED` 成果按 `(任务, 月份)` 重放归集，跳过任务完成前置。

不做成启动自动补、也不做成页面按钮：两者都等于隐式写财务数据，而这件事只需要在升级时被执行一次。

## 已知取舍

- **期末津贴优先取账本快照**：`allowance_detail` 里该期那行的 `amount` 就是当时的结论；只有缺快照时才按公式现算。这样运营事后改额度不会让历史实发跟着变。
- 结算单与明细都没有 `user_id` 之外的人员快照；用户改名会影响历史展示。
- 明细只保留「分类名 + 模板名」一行快照，业务扩展到「一单一任务多计价项」时需要改结构。
- 一期不打款：`paid_amount` 已写（受封顶后的实发），`pay_status` 停在 `SCHEDULED`；`SettlementStatus.PAID` 与 `AllowanceStatus.PAID` 仍无写入路径。
