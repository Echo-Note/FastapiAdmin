from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from .crud import CompanyCRUD
from .schema import CompanyCreateSchema, CompanyOutSchema, CompanyQueryParam, CompanyUpdateSchema


class CompanyService:
    """医药公司主数据服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> CompanyOutSchema:
        """查询医药公司详情。"""
        company = await CompanyCRUD(self.auth, self.db).get_or_404(id=id)
        return CompanyOutSchema.model_validate(company)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CompanyQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CompanyOutSchema]:
        """分页查询医药公司。"""
        offset = (page_no - 1) * page_size
        page_result = await CompanyCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=CompanyOutSchema,
        )
        return page_result

    async def create(self, data: CompanyCreateSchema) -> CompanyOutSchema:
        """创建医药公司。"""
        if await CompanyCRUD(self.auth, self.db).get(name=data.name):
            raise CustomException(msg="已存在相同名称的医药公司")
        if data.code and await CompanyCRUD(self.auth, self.db).get(code=data.code):
            raise CustomException(msg="已存在相同编码的医药公司")
        company = await CompanyCRUD(self.auth, self.db).create(data=data)
        return CompanyOutSchema.model_validate(company)

    async def update(self, id: int, data: CompanyUpdateSchema) -> CompanyOutSchema:
        """更新医药公司。"""
        await CompanyCRUD(self.auth, self.db).get_or_404(id=id)
        if data.name and (exist := await CompanyCRUD(self.auth, self.db).get(name=data.name)) and exist.id != id:
            raise CustomException(msg="已存在相同名称的医药公司")
        if data.code and (exist := await CompanyCRUD(self.auth, self.db).get(code=data.code)) and exist.id != id:
            raise CustomException(msg="已存在相同编码的医药公司")
        await CompanyCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除医药公司。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await CompanyCRUD(self.auth, self.db).delete(ids=ids)
