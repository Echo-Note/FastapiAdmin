"""产品库服务。

三类调用方：

- 运营端（``module_market:product:*`` 权限码）：维护产品、审核 C 端自动入库的记录；
- C 端检索（``/market/mini/products/search``）：按产品名称模糊匹配，可见集受审核状态约束；
- 成果提交钩子（``SubmissionService.create/update``）：把提交数据里库里没有的产品自动入库为待审。

可见性规则是本模块的核心不变量：
``approved`` 对所有人可见；``pending`` 只对提交人自己可见（同人下月不必重录）；
``rejected`` 对任何人都不可见。「提交人」取审计字段 ``created_id``（真实用户），
不另设来源枚举——运营录入与 C 端提交都是具体的人。
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.common_util import search_to_dict

from ..enums import ProductAuditStatus
from ..task.collection_schema import PRODUCT_MANUFACTURER_KEY, PRODUCT_NAME_KEY, PRODUCT_SPEC_KEY
from .crud import ProductCRUD
from .model import ProductModel
from .schema import (
    ProductAuditSchema,
    ProductCreateSchema,
    ProductOutSchema,
    ProductQueryParam,
    ProductSearchItemSchema,
    ProductUpdateSchema,
)

# 产品三要素的约定列名 → 角色（form_schema 未声明 product_role 时的兜底）
DEFAULT_PRODUCT_COLUMNS: dict[str, str] = {
    "name": PRODUCT_NAME_KEY,
    "spec": PRODUCT_SPEC_KEY,
    "manufacturer": PRODUCT_MANUFACTURER_KEY,
}


def resolve_product_columns(form_schema: list[dict[str, Any]] | None) -> dict[str, str]:
    """从 ``form_schema`` 解析「角色 → 列名」映射，缺失的角色回退到约定列名。

    产品的三要素列由 ``FormSchemaColumn.product_role`` 显式标记（name/spec/manufacturer）；
    老数据没有该标记时按约定列名 ``product_name/product_spec/manufacturer`` 识别。

    :param form_schema: 三级任务的 ``config.form_schema``（分节列表，可为空）
    :return: 角色 → 列名，键恒为 name/spec/manufacturer
    """
    columns = dict(DEFAULT_PRODUCT_COLUMNS)
    for section in form_schema or []:
        fields = (section or {}).get("fields") or {}
        for field in fields.values():
            for column in (field or {}).get("columns") or []:
                role = (column or {}).get("product_role")
                if role in columns and column.get("name"):
                    columns[role] = column["name"]
    return columns


def iter_submitted_products(
    form_data: dict[str, Any] | None, columns: dict[str, str] | None = None
) -> list[tuple[str, str, str]]:
    """从成果 ``form_data`` 递归提取产品三要素（名称/规格/生产企业）。

    ``form_data`` 是按分节嵌套的字典，多行子表的值是 ``list[dict]``；本函数遍历所有行，
    取出产品名称为非空的三元组（已 strip）。非产品的行（如竞品调研的 ``competitor_*`` 列、
    会议活动的单值字段）不会命中。

    :param form_data: 提交的采集表单数据
    :param columns: 角色 → 列名映射，默认取 ``DEFAULT_PRODUCT_COLUMNS``
    :return: 去重后的 (名称, 规格, 生产企业) 列表
    """
    mapping = columns or DEFAULT_PRODUCT_COLUMNS
    name_key = mapping["name"]
    spec_key = mapping["spec"]
    manufacturer_key = mapping["manufacturer"]

    found: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            raw_name = node.get(name_key)
            if isinstance(raw_name, str) and raw_name.strip():
                triple = (
                    raw_name.strip(),
                    str(node.get(spec_key) or "").strip(),
                    str(node.get(manufacturer_key) or "").strip(),
                )
                if triple not in seen:
                    seen.add(triple)
                    found.append(triple)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(form_data)
    return found


class ProductService:
    """产品库服务（运营端维护 + 审核 + C 端检索 + 成果自动入库）。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    # ------------------------------------------------------------------ 运营端

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ProductQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ProductOutSchema]:
        """分页查询产品库（运营端）。"""
        offset = (page_no - 1) * page_size
        return await ProductCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=ProductOutSchema,
        )

    async def detail(self, id: int) -> ProductOutSchema:
        """产品详情。"""
        product = await ProductCRUD(self.auth, self.db).get_or_404(id=id, msg="产品不存在")
        return ProductOutSchema.model_validate(product)

    async def create(self, data: ProductCreateSchema) -> ProductOutSchema:
        """运营录入产品：录入即生效（直接 ``approved``），不受审核流程约束。"""
        await self._ensure_not_duplicated(data.name, data.spec, data.manufacturer)
        product = await ProductCRUD(self.auth, self.db).create(
            data={
                "name": data.name,
                "spec": data.spec,
                "manufacturer": data.manufacturer,
                "audit_status": ProductAuditStatus.APPROVED.value,
                "reviewer_id": self.auth.user.id,
                "reviewed_at": datetime.now(UTC),
            }
        )
        return ProductOutSchema.model_validate(product)

    async def update(self, id: int, data: ProductUpdateSchema) -> ProductOutSchema:
        """修改产品（改名/规格/企业等于改动判重键，重复会撞唯一约束）。"""
        product = await ProductCRUD(self.auth, self.db).get_or_404(id=id, msg="产品不存在")
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        if update_data:
            await self._ensure_not_duplicated(
                str(update_data.get("name", product.name)),
                str(update_data.get("spec", product.spec)),
                str(update_data.get("manufacturer", product.manufacturer)),
                exclude_id=id,
            )
            await ProductCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除产品（软删除，保留审计追溯）。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await ProductCRUD(self.auth, self.db).delete(ids=ids)

    async def audit(self, data: ProductAuditSchema) -> int:
        """批量审核产品：通过/驳回都写审核人、意见与时间，返回实际变更条数。

        :param data: 审核入参（ids + approved + review_comment）
        :return: 实际被改动状态的记录数
        """
        target = ProductAuditStatus.APPROVED.value if data.approved else ProductAuditStatus.REJECTED.value
        comment = (data.review_comment or "").strip() or None
        changed = 0
        for product_id in data.ids:
            product = await ProductCRUD(self.auth, self.db).get(id=product_id)
            if product is None or product.audit_status == target:
                continue
            await ProductCRUD(self.auth, self.db).update(
                id=product_id,
                data={
                    "audit_status": target,
                    "reviewer_id": self.auth.user.id,
                    "review_comment": comment,
                    "reviewed_at": datetime.now(UTC),
                },
            )
            changed += 1
        return changed

    # ------------------------------------------------------------------ C 端

    async def search(self, keyword: str, limit: int = 20) -> list[ProductSearchItemSchema]:
        """C 端按名称模糊检索产品，返回可见集内按名称排序的候选列表。

        可见集：``approved`` 或（``pending`` 且提交人是当前用户）；``rejected`` 永不可见。

        :param keyword: 产品名称关键词（空串返回前 N 条通用候选）
        :param limit: 返回条数上限
        :return: 产品候选列表（仅供回填三要素，不暴露审核字段）
        """
        conditions = [
            ProductModel.is_deleted.is_(False),
            or_(
                ProductModel.audit_status == ProductAuditStatus.APPROVED.value,
                and_(
                    ProductModel.audit_status == ProductAuditStatus.PENDING.value,
                    ProductModel.created_id == self.auth.user.id,
                ),
            ),
        ]
        if keyword.strip():
            conditions.append(ProductModel.name.ilike(f"%{keyword.strip()}%"))
        stmt = (
            select(ProductModel)
            .where(*conditions)
            .order_by(ProductModel.name.asc(), ProductModel.spec.asc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            ProductSearchItemSchema(
                id=row.id,
                name=row.name,
                spec=row.spec,
                manufacturer=row.manufacturer,
                display_name=row.display_name,
            )
            for row in rows
        ]

    async def ingest_from_form_data(self, form_data: dict[str, Any] | None, form_schema: Any = None) -> int:
        """把成果里库里没有的产品自动入库为待审记录，返回新建条数。

        已存在同一判重键（名称+规格+生产企业）则跳过——包括已 ``rejected`` 的，
        不让同一份脏数据在每次提交时反复重生。产品入库失败不阻断成果提交，只记日志。

        :param form_data: 成果提交数据
        :param form_schema: 该三级任务的 ``form_schema``（用于识别 ``product_role`` 列）
        :return: 新建的产品条数
        """
        columns = resolve_product_columns(form_schema)
        created = 0
        for name, spec, manufacturer in iter_submitted_products(form_data, columns):
            if await ProductCRUD(self.auth, self.db).get(name=name, spec=spec, manufacturer=manufacturer):
                continue
            try:
                # 单条失败只回滚该条（savepoint），不影响成果本身的落库
                async with self.db.begin_nested():
                    await ProductCRUD(self.auth, self.db).create(
                        data={
                            "name": name,
                            "spec": spec,
                            "manufacturer": manufacturer,
                            "audit_status": ProductAuditStatus.PENDING.value,
                        }
                    )
                created += 1
            except IntegrityError:
                logger.debug("产品库自动入库跳过（判重键已存在）: %s / %s / %s", name, spec, manufacturer)
        return created

    # ------------------------------------------------------------------ 内部

    async def _ensure_not_duplicated(self, name: str, spec: str, manufacturer: str, exclude_id: int | None = None) -> None:
        """判重键冲突检查（唯一约束是最终兜底，这里给出可读的错误文案）。"""
        existing = await ProductCRUD(self.auth, self.db).get(name=name, spec=spec, manufacturer=manufacturer)
        if existing is not None and existing.id != exclude_id:
            raise CustomException(msg=f"产品已存在：{name} / {spec or '—'} / {manufacturer or '—'}")
