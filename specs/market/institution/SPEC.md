---
id: market-institution
type: submodule-design
status: draft
title: market/institution —— 机构主数据与图片归集
parent: market-domain
---

# market/institution

## Responsibility

维护采集对象主体「机构」（等级医院/基层医疗/民营医疗/零售药店/商业公司），并归集 C 端提交成果时上传的机构图片。机构是成果提交里的 `subject_type=institution` 那一路的具体承载。

## Boundary

- 只被 [market/task](../task/SPEC.md) 引用（`market_submission.institution_id`、`market_institution_image.institution_id`），自己不引用任何 market 子模块。
- 头像/附件类文件走 `app/modules/common/file`，本模块只存 URL 字符串。
- 权限码：`module_market:institution:{query,create,update,delete}`。注意 `create` 当前只出现在**机构图片**接口上（`InstitutionImageRouter`），机构本身没有运营新建入口。

## 机构由 C 端归集产生

`InstitutionService.collect(name, type, level, region, address)` 是机构的唯一创建路径：

- 按 `name` 查重（不是唯一索引，是应用层查重），命中则复用，否则建一条 `status=0`（启用）的机构。
- 调用方是 C 端提交成果的链路，所以**机构表是「用出来的」而不是「录出来的」**：运营端只做查询、修正、停用/删除，没有「新建机构」按钮。
- 副作用：名称是唯一的去重键，重名机构会被合并成一条。

## 启用列表带 Redis 缓存

`enabled_list` 是 C 端选机构用的全量列表，走 Redis 缓存（键 `...:enabled`，TTL 取 `REDIS_DEFAULT_CACHE_TTL`，解析失败则回源）。`update` / `delete` 会主动删这个键——**任何绕过 service 直接改机构的脚本都必须自己失效缓存**，否则 C 端会继续选到已停用的机构。

## 图片归集

`market_institution_image` 与机构是 `cascade="all, delete-orphan"` 的一对多：删机构连带删图片记录（DB 层也是 ON DELETE CASCADE）。

- `submission_id` 可空，记录图片来自哪次成果提交，用于回溯；成果删除时置 NULL（SET NULL），不连带删图。
- `category` 存图片分类（门头照/内景照/打卡照等），是自由文本，没有枚举约束。
- `period` 存提交月份，用于按月归集查看。

## 已知取舍

- 机构字段里 `type` 存枚举值但**数据库层是 String**，没有 CHECK 约束；写入端靠 `InstitutionType` 约束，脚本/导入可绕过。
- 图片与成果的关系是弱引用（可空外键 + SET NULL），所以「这张图属于哪次提交」在成果删除后就断了。
