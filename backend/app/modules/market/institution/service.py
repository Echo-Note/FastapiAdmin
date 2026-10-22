from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from .crud import InstitutionCRUD
from .schema import InstitutionCreateSchema, InstitutionOutSchema, InstitutionQueryParam, InstitutionUpdateSchema


class InstitutionService:
    """机构主数据服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> InstitutionOutSchema:
        """查询机构详情。"""
        institution = await InstitutionCRUD(self.auth, self.db).get_or_404(id=id)
        return InstitutionOutSchema.model_validate(institution)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: InstitutionQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[InstitutionOutSchema]:
        """分页查询机构。"""
        offset = (page_no - 1) * page_size
        page_result = await InstitutionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=InstitutionOutSchema,
        )
        return page_result

    async def create(self, data: InstitutionCreateSchema) -> InstitutionOutSchema:
        """创建机构。"""
        institution = await InstitutionCRUD(self.auth, self.db).create(data=data)
        return InstitutionOutSchema.model_validate(institution)

    async def update(self, id: int, data: InstitutionUpdateSchema) -> InstitutionOutSchema:
        """更新机构。"""
        await InstitutionCRUD(self.auth, self.db).get_or_404(id=id)
        await InstitutionCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除机构。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await InstitutionCRUD(self.auth, self.db).delete(ids=ids)
