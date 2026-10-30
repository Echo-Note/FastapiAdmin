---
id: foxwork-architecture
type: architecture-design
status: draft
title: FoxWork 系统架构与横切不变量
parent: foxwork-goal
---

# FoxWork 系统架构与横切不变量

> 以代码为准。`docs/02-系统设计文档.md` 描述的架构已整体失准（UUID 主键、`market_task_type`、`market_service_item`、`market_template` 均不存在），不要据它判断现状。

## 拓扑

```
frontend/web    Vue 3.5 + Vite 7 + Element Plus + Tailwind 4 + Pinia   （运营端，路由由后端菜单生成）
frontend/app    UniApp + Wot Design Uni + alova + UnoCSS              （C 端小程序/H5）
                        │  同一个后端：/api/v1
backend         FastAPI + SQLAlchemy 2.0 async + Pydantic 2 + Alembic
                        │
        PostgreSQL 18（业务库） + Redis 7（会话/权限缓存/调度 JobStore/大厅占位计数/机构列表缓存）
```

两端**不共享代码包**：web 用 axios + Tailwind + Element Plus，app 用 alova + UnoCSS + Wot Design Uni，约 49 个同名 DTO 类型各存一份副本。改 market 的 DTO 必须两端同改，且 app 端分页字段同样是 `items`。

## 后端模块地图

唯一注册点：`backend/app/api/v1/routers.py` 的 `DOMAIN_CONTROLLERS`（domain 前缀 → router 实例列表），全部 controller 在文件顶部硬 import。改这个 dict 后**必须重启**（动态发现只在启动时跑一次）。

| 前缀 | 域 | 职责 | 性质 |
|---|---|---|---|
| `/system` | system | 登录/JWT/微信登录、用户、角色、菜单、部门、岗位、字典、参数、公告、工单、客户端版本、日志 | 上游基座 |
| `/monitor` | monitor | 在线用户、服务器、缓存监控（含只读键空间浏览） | 上游基座 |
| `/task` | task | 定时任务调度 + 可视化工作流节点 + 多存储源浏览/传输/工作流 | 上游基座 |
| `/generator` | generator | 选表生成后端 + 前端代码 | 上游基座（含模板注入防护） |
| `/common` | common | 文件上传下载 | 上游基座 |
| `/ai` | ai | Agno 智能体对话 + 只读工具注册表 | 上游基座 |
| `/ops` | ops | SSH 主机/片段/终端会话/批量执行 | 上游基座 |
| `/dbconsole` | dbconsole | 外部库只读 SQL 控制台（SQL 守卫 + 敏感列脱敏） | 上游基座 |
| `/market` | market | **本项目定制主域**：任务、项目、结算、机构、看板 | 定制 |
| `/module_example` | plugin | 插件动态发现示例 | 上游基座 |

market 的边界与内部依赖见 [market-domain](market/SPEC.md)。market 只依赖 `app/core/*`、`app/common/*`、`app/modules/common/file`，不 import 其它业务域；`sys_user.id` 是唯一的外部外键引用。

> 未确认：README 宣称的 `ENABLED_MODULES` 模块裁剪在代码中**不存在**（`grep` 零命中），裁模块只能从 `DOMAIN_CONTROLLERS` 删 router；各域 `plugin.toml` 的 `optional = true` 无任何代码读取。

## 横切不变量

### 权限分两层，别混

- **功能权限**（能不能调这个接口）：权限码格式 `module_<domain>:<resource>:<action>`，`Security(AuthPermission([...]))` 任一命中即放行。登录时由 `role → menu.permission` 算一次写进 Redis 会话，之后每请求只读缓存**不重算**；`is_superuser` 或含 `*:*:*` 直接放行。新增接口的权限码必须与菜单管理里登记的一致，否则前端 `v-hasPerm` 与后端各说各话。
- **行级数据权限**（能看哪些行）：`CRUDBase._build_conditions` 自动追加 `Permission(...)._permission_condition()`，按 `role.data_scope` 取值（1 仅自己 / 2 本部门及以下 / 3 全部）。
- **market 域显式跳过第二层**：`MarketCRUDBase` 覆写 `_build_conditions` 去掉 `created_id` 过滤。因为 market 的业务归属是 `user_id/company_id/task_id` 这类业务字段，而运营代 C 端创建的行 `created_id` 是运营——照基座规则过滤会把 C 端的行全挡掉。**代价是 market 的越权防护全靠 Service 层显式按 `user_id` 过滤**：新增 C 端接口漏写这个条件就是横向越权。
- C 端 `/market/mini/*` 只用 `get_current_user`，不要求运营权限码。

### 事务与软删除

- CRUD 层**只 flush 不 commit**，事务边界在 HTTP 层：`db_getter` 在依赖退出时 `session.begin()` 提交/回滚。Service 不要自己 commit。
- 软删除是 `is_deleted` 布尔列，不是 SQLAlchemy 内置能力。只有走 `CRUDBase._build_conditions` 的查询才自动带 `is_deleted = false`；**手写 `select()` 必须自己加**（`market/dashboard/service.py` 是照着写的范例）。

### 迁移与种子

- **迁移文件不入库**：`app/alembic/versions/` 只有 `__init__.py`。空库靠 `create_all` 自举 + `stamp head`；非空库启动时 `upgrade head`；dev 启动自动 `autogenerate`，若 upgrade 段含 `drop_column/drop_table/drop_constraint` 之类危险操作会**拒绝自动应用**，要求人工 `main.py revision` 审查。因此**不要手写迁移文件**——会撞 Multiple heads。
- **种子数据幂等但不重导**：`backend/sql/*.json` 按表导入，表非空即整表 skip。market 三张目录表 seed 后会调 `sync_counter` 对齐编号计数器。种子改过之后已初始化的库不会重导，要用 `app/scripts/reseed_market.py`。

### 数据库方言

生产是 PG 18。`numbering.next_code` 直接依赖 PG 的 `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` 做原子自增，**SQLite/MySQL 下会失败**（尽管 setting 声称支持三方言）。JSON 列统一走 `JSONType`（PG 落 JSONB，其它方言降级 JSON）。

### 审计

所有 controller 都挂 `OperationLogRoute`，对写方法（POST/PUT/PATCH/DELETE/HEAD/OPTIONS；GET 不记）自动落 `sys_operation_log`，敏感键递归脱敏；响应体只对 `application/json` 记录，流式/SSE 响应记为空。

### 前端动态路由与 KeepAlive

- 业务路由**不在** `routes.ts`：后端菜单表 → `guards.ts` → `MenuProcessor` → `RouteRegistry.addRoute`。新增页面必须在后端菜单管理里登记 `route_name / route_path / component_path / keep_alive`，`component_path` 形如 `module_market/company/index`。
- **目录级路由不能挂组件**（`component_path` 留空），靠 RouterView 深度跳级直达叶子。给目录挂组件会让页面重复挂载、接口重复请求；`__tests__/route-invariants.spec.ts` 把这条固化为断言。
- **全局只有一层 KeepAlive**（`layouts/fa-page-content`），缓存 key 是叶子 `route.path`，include/exclude 按**组件 name** 匹配。所以每个页面 SFC 必须写 `defineOptions({ name })` 且全局唯一，否则缓存静默失效、不报错。不要给 KeepAlive 加 `v-if` 或 `:max`。
- 组件与 hooks 构建期自动导入（`unplugin-auto-import` / `unplugin-vue-components`）：页面里直接写 `useTable(...)`、`<FaTable>`，不写 import。

### 响应与分页契约

统一 `ResponseSchema[T]` 包裹。分页入参 `page_no / page_size`（+ `order_by` 走 JSON 字符串），返回 `PageResultSchema{page_no, page_size, total, has_next, items}`。**列表字段是 `items` 不是 `list`**——app 端因此另建了 `useMarketListPage`。

### CRUD 页面范式

`useTable`（列表状态 + 分页 + 缓存）+ `useTableColumns`（列配置持久化）+ `useCrudDialog` / `useCrudForm`（表单三态）+ `FaSearchBar` / `FaTable` / `FaDialog`。不要手写 ElTable/ElDialog。

两个易漏点：`useTable` 必须传 `columnsFactory` 才会展开 `columns/columnChecks`（否则模板里静默 `undefined`）；增删改后用语义化刷新 `refreshCreate / refreshUpdate / refreshRemove`，不要自己 `getData()`。
