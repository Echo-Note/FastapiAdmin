---
id: market-member
type: submodule-design
status: draft
title: market/member —— C 端成员档案与身份判定
parent: market-domain
---

# market/member

## Responsibility

回答一个问题：**这个 `sys_user` 是不是 C 端用户？** 同时给全域提供运营端列表要展示的用户摘要。

## Boundary

- 只存 `user_id`（`sys_user.id`）与 market 自己的成员编号/状态，不复制昵称手机号；摘要永远实时从
  `sys_user` 读（`load_user_briefs`）。
- 不授予任何权限、不参与 RBAC。角色是**权限**概念，本表是**身份**概念，两者不互相推断。
- 权限码：`module_market:member:{query,create,update}`。

## 存在档案 = 是 C 端

**唯一判据是 `market_member` 有没有这条记录**，不看角色、不看 `is_superuser`。

这条决定的背景（2026-11）：系统只有一张 `sys_user`，运营与 C 端共用；`/market/mini/*` 此前只校验
登录，而微信小程序首次登录自动注册的用户拿到的是**默认角色 `OAUTH_DEFAULT_ROLE_IDS = [2]`（管理员）**。
结果是「谁是 C 端」既查不到也校验不了，且每个微信注册用户都被授了管理员权限。

不用角色的理由：角色是多对多，一个运营可能兼有普通角色，用「拥有某角色」推断身份必然模棱两可；
而身份需要单值、可索引、能在一处判定。

## 建档

三条路径，都幂等（`user_id` 唯一约束 + 冲突后回查）：

1. **C 端接口首访自动建档**：`require_market_member` 依赖（`/market/mini/*` 全部路由用它替换了
   `get_current_user`）在认证时 lazy ensure——微信登录、手机号登录、直连接口全覆盖，不依赖客户端配合。
2. **微信登录后补一手**：`wx_mini_service` 登录编排里 best-effort 建档。登录是用户「成为 C 端成员」的
   语义时刻，运营应能立刻在成员管理页看到新用户。这里用**延迟 import**（`system` → `market` 单向钩子，
   失败不影响登录），因为基座不应该硬依赖定制域。
3. **运营手动纳入**：成员管理页把已有 `sys_user` 建档（已建档则幂等返回现有档案）。

存量用户靠 `app/scripts/backfill_member.py` 回填，判据是**行为证据**：曾经接过单、提交过成果或产生过
津贴/结算记录的用户视为 C 端（这是系统里唯一可靠的证据）。

## 状态

`ACTIVE` / `DISABLED`。停用后 `require_market_member` 直接拒绝所有 C 端接口（含读），
**不会因为再次访问而自愈回启用**；档案与历史数据保留，运营可随时恢复。

## 编号

`member_no` = `U-NNNN`，走 `numbering.next_code(NumberPrefix.MEMBER)` 的原子计数器，
与 `TK`（任务）、`ARC`（成果档案）同一套机制，前端不提供输入。

## 用户摘要（`brief.py`）

`MarketUserBriefSchema{id, name, username, mobile}` + `load_user_briefs(db, ids)` 批量查询。
结算单、发放结果、成员列表的出参都带 `user`，**前端不再自己拉全量用户表反查**——只存自增
`user_id` 时，重名或几个「普通用户」无法区分，手机号才是业务上真正的识别手段。

## 已知取舍

- 停用的语义是「拒绝 C 端接口」，不回收已签发的 JWT——用户在令牌过期前仍能通过其他接口自证身份，
  只是 market 域会挡住他。要做全局封禁应在 `sys_user.status` 上做。
- 成员档案没有实名/收款账户字段：二期打款需要时再加列（届时也不该复用 `sys_user`）。
- `is_superuser` 的运营账号如果去调 C 端接口，也会被自动建档成 C 端成员。当前运营不会走 C 端入口；
  若将来出现「运营兼跑单」的真实场景，需要显式拒绝超管建档。
