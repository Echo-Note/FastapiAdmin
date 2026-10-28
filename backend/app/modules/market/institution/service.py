import json

from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.config.setting import settings
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.redis_crud import RedisCURD
from app.utils.common_util import search_to_dict

from .crud import InstitutionCRUD, InstitutionImageCRUD
from .schema import (
    InstitutionCreateSchema,
    InstitutionImageCreateSchema,
    InstitutionImageOutSchema,
    InstitutionImageQueryParam,
    InstitutionImageUpdateSchema,
    InstitutionOutSchema,
    InstitutionQueryParam,
    InstitutionUpdateSchema,
)


class InstitutionService:
    """机构主数据服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    @staticmethod
    def _cache_key() -> str:
        """机构启用列表缓存键。"""
        return f"{RedisInitKeyConfig.MARKET_INSTITUTION_LIST.key}:enabled"

    async def enabled_list(self, redis: Redis) -> list[InstitutionOutSchema]:
        """启用机构全量列表（带 Redis 缓存），供 C 端提交成果选择机构。"""
        cache_key = self._cache_key()
        cached = await RedisCURD(redis).get(cache_key)
        if cached:
            try:
                return [InstitutionOutSchema.model_validate(item) for item in json.loads(cached)]
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning("机构缓存解析失败，回源数据库: %s", cache_key)
        objs = await InstitutionCRUD(self.auth, self.db).get_list(search={"status": 0})
        items = [InstitutionOutSchema.model_validate(obj) for obj in objs]
        payload = json.dumps([item.model_dump(mode="json") for item in items], ensure_ascii=False)
        await RedisCURD(redis).set(cache_key, payload, expire=settings.REDIS_DEFAULT_CACHE_TTL)
        return items

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

    async def create(self, redis: Redis, data: InstitutionCreateSchema) -> InstitutionOutSchema:
        """创建机构。"""
        institution = await InstitutionCRUD(self.auth, self.db).create(data=data)
        await RedisCURD(redis).delete(self._cache_key())
        return InstitutionOutSchema.model_validate(institution)

    async def update(self, redis: Redis, id: int, data: InstitutionUpdateSchema) -> InstitutionOutSchema:
        """更新机构。"""
        await InstitutionCRUD(self.auth, self.db).get_or_404(id=id)
        await InstitutionCRUD(self.auth, self.db).update(id=id, data=data)
        await RedisCURD(redis).delete(self._cache_key())
        return await self.detail(id=id)

    async def delete(self, redis: Redis, ids: list[int]) -> None:
        """删除机构。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await InstitutionCRUD(self.auth, self.db).delete(ids=ids)
        await RedisCURD(redis).delete(self._cache_key())


class InstitutionImageService:
    """机构图片归集服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> InstitutionImageOutSchema:
        """查询机构图片详情。"""
        image = await InstitutionImageCRUD(self.auth, self.db).get_or_404(id=id, preload=["institution"])
        return InstitutionImageOutSchema.model_validate(image)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: InstitutionImageQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[InstitutionImageOutSchema]:
        """分页查询机构图片。"""
        offset = (page_no - 1) * page_size
        page_result = await InstitutionImageCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search_to_dict(search),
            out_schema=InstitutionImageOutSchema,
            preload=["institution"],
        )
        return page_result

    async def create(self, data: InstitutionImageCreateSchema) -> InstitutionImageOutSchema:
        """创建机构图片。"""
        image = await InstitutionImageCRUD(self.auth, self.db).create(data=data)
        return InstitutionImageOutSchema.model_validate(image)

    async def update(self, id: int, data: InstitutionImageUpdateSchema) -> InstitutionImageOutSchema:
        """更新机构图片。"""
        await InstitutionImageCRUD(self.auth, self.db).get_or_404(id=id)
        await InstitutionImageCRUD(self.auth, self.db).update(id=id, data=data)
        return await self.detail(id=id)

    async def delete(self, ids: list[int]) -> None:
        """删除机构图片。"""
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await InstitutionImageCRUD(self.auth, self.db).delete(ids=ids)

    async def list_by_institution(
        self,
        institution_id: int,
        page_no: int,
        page_size: int,
    ) -> PageResultSchema[InstitutionImageOutSchema]:
        """按机构归集查看图片（供机构管理页）。"""
        offset = (page_no - 1) * page_size
        page_result = await InstitutionImageCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search={"institution_id": institution_id},
            out_schema=InstitutionImageOutSchema,
            preload=["institution"],
        )
        return page_result
