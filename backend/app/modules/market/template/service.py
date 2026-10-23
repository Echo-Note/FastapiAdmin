from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from .crud import TemplateCRUD
from .schema import TemplateCreateSchema, TemplateOutSchema, TemplateQueryParam, TemplateUpdateSchema


class TemplateService:
    """采集模板服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> TemplateOutSchema:
        """查询采集模板详情。"""
        template = await TemplateCRUD(self.auth, self.db).get_or_404(id=id)
        return TemplateOutSchema.model_validate(template)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: TemplateQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[TemplateOutSchema]:
        """分页查询采集模板。"""
        offset = (page_no - 1) * page_size
        return await TemplateCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=TemplateOutSchema,
        )

    async def create(self, data: TemplateCreateSchema) -> TemplateOutSchema:
        """创建采集模板。"""
        if await TemplateCRUD(self.auth, self.db).get(code=data.code):
            raise CustomException(msg="已存在相同编码的采集模板")
        template = await TemplateCRUD(self.auth, self.db).create(data=data)
        return TemplateOutSchema.model_validate(template)

    async def update(self, id: int, data: TemplateUpdateSchema) -> TemplateOutSchema:
        """更新采集模板。"""
        await TemplateCRUD(self.auth, self.db).get_or_404(id=id)
        if data.code and (exist := await TemplateCRUD(self.auth, self.db).get(code=data.code)) and exist.id != id:
            raise CustomException(msg="已存在相同编码的采集模板")
        await TemplateCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除采集模板。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await TemplateCRUD(self.auth, self.db).delete(ids=ids)
