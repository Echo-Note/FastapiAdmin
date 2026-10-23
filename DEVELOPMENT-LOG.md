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
