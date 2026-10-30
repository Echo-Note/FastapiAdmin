---
id: market-dashboard
type: submodule-design
status: active
title: market/dashboard —— 运营看板聚合
parent: market-domain
---

# market/dashboard

## Responsibility

给运营端首页提供两个只读聚合接口：

- `GET /market/dashboard/overview` —— 当前时刻的核心计数：任务（总数/进行中/已完成/已结算）、成果（总数/待审/通过/驳回）、结算（单数/应发金额合计）、项目/公司/机构/分类/模板数量。
- `GET /market/dashboard/insights` —— 判断「要不要现在动手」的明细：近 14 天成果提交量趋势（按待审/通过/驳回分桶，固定 14 点）+ 最新 8 条待审核成果队列（对象名/任务名/所属月份/提交时间）。

两者刻意分开：`overview` 是纯计数契约，被测试与前端基础版式依赖；明细将来继续长也只是 `insights` 变胖，不动既有形状。

## Boundary

- **没有自有表，没有 CRUD 层**：只有 controller / service / schema 三个文件。
- 只读。不拥有任何实体的状态，也不该被任何写流程调用。
- 两个接口共用权限码 `module_market:dashboard:query`。
- 跨子模块读取 task / project / institution / payout 的表，是全域唯一一个「谁的表都读」的模块——所以它是 market 子模块依赖图里的汇点，改动这里不会牵连别人，反过来别人加表时它需要跟着补计数。

## 实现约束

聚合查询**手写 `select()`**，不走 `CRUDBase`。因此必须自己加 `is_deleted.is_(False)` 过滤——见 [architecture](../../architecture.md) 的「事务与软删除」。漏加会把已删除记录算进统计。队列的 join 同理：`assignment` / `task` 也要过滤软删除，否则已删任务下的成果会挂在首页。

金额合计用 `coalesce(sum(...), 0)`，避免空表返回 `NULL` 而不是 0。

**趋势的「一天」以北京时间（`Asia/Shanghai`）切分**，数据库时间戳是 UTC。分桶在 Python 里做（`build_trend` 纯函数），不用 `date_trunc` / `AT TIME ZONE`：它们是 PG 专有而测试库是 SQLite，且「一天从 0 点切」写在代码里比埋在 SQL 里可读。窗口起点 = 本地今天往前 13 天的 00:00 转 UTC；`created_time` 若是 naive（SQLite 返回）必须按 UTC 解释再转本地，不能直接 `astimezone()`（那会误用服务器时区）。

**队列的对象名取 `institution.name` → `subject_name` → 「未填写对象」**，机构用 `outerjoin` 并在 ON 条件里过滤软删除：机构被删掉时队列行仍要保留，退回 `subject_name` 而不是整行消失。

## 已知取舍

- `overview` 一个接口打 10+ 条独立 count 查询，不是单条聚合 SQL；数据量小时无所谓，但它是首页接口，日后要优化就在这个文件里改。
- 统计口径是**全库**，不按操作人/部门收窄——dashboard 不做数据权限。
- 趋势只回答「提交量怎么变」，按**提交时间**分桶，与 `overview` 按当前状态计数互补；两者数值天然不一致（同一批成果在趋势里按提交日归属，在计数里按当前状态归属）。
- 队列固定 8 条、趋势固定 14 天，不做参数化：首页要的是一眼看完，不是可配置报表。
- 趋势自己算、队列自己 join，都不复用 `submission` 的列表接口——列表会把 `form_data`（JSONB 采集表单）整列带回来，首页不需要。

## 前端呈现约定（`views/module_market/dashboard/index.vue`）

- **三段式**：待处理（数字 + 待办队列）→ 业务流转（任务 → 成果 → 结算的阶段分布 + 14 天趋势）→ 资料库（存量计数）。新增指标时按「是否要人动手」判归属，不要平铺成等权卡片。
- 阶段分布条的「其他」由既有计数推导（总数 − 各状态之和，草稿/已发布/归档等未单列状态），因此后端补状态计数时前端自动细化。
- **金额口径必须外显**：`payable_amount` 是全部结算单应发合计、不区分结算状态，页面要写明，不靠 description 暗示。
- **失败与零值必须可区分**：请求失败走错误块 + 重试，禁止把失败渲染成 0；已有数据时刷新失败保留旧数据。`insights` 失败不影响 `overview` 已渲染的计数与分布条，两块各自内联「重试」。
- **趋势图自绘 CSS 堆叠柱**，不用 `FaBarChart`：后者数据全 0 时会 `chart.clear()` 只留居中空态文案（丢掉坐标轴与网格），与「空态保留基线 + 网格」的约定冲突；自绘还能直接吃 `--el-color-*`，暗色自动跟随。趋势空态必须显示网格线、基线与「近 14 天没有成果提交」。
- **队列行整行是链接**，指向 `/market/task/submission?status=PENDING`；审核页读 `route.query.status` 初始化筛选。无 `module_market:submission:query` 权限时不请求也不渲染队列块。
- 页面 `keep_alive=true`，切回标签不重挂载，故需在 `onActivated` 里按「距上次加载 > 5 分钟」补拉，并显示「更新于 HH:mm」。
