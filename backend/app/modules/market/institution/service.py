import json
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.config.setting import settings
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.redis_crud import RedisCURD
from app.utils.common_util import search_to_dict

from ..enums import InstitutionType
from .crud import InstitutionCRUD, InstitutionImageCRUD
from .schema import (
    InstitutionImageCreateSchema,
    InstitutionImageOutSchema,
    InstitutionImageQueryParam,
    InstitutionImageUpdateSchema,
    InstitutionOutSchema,
    InstitutionQueryParam,
    InstitutionUpdateSchema,
)

# 机构名称字段候选（采集表单 form_data 中跨分节按字段名匹配，兼容商务类 hospital_name / 档案调研类 org_name）
_INSTITUTION_NAME_FIELDS: tuple[str, ...] = ("hospital_name", "org_name", "institution_name")

# 二级模板名 → 机构类型映射（机构类型由 C 端执行的任务模板权威决定）
_TEMPLATE_INSTITUTION_TYPE_MAP: dict[str, str] = {
    "等级医疗管理": InstitutionType.GRADE_HOSPITAL.value,
    "基层医疗管理": InstitutionType.PRIMARY_CARE.value,
    "民营医疗管理": InstitutionType.PRIVATE_MEDICAL.value,
    "零售药店管理": InstitutionType.RETAIL_PHARMACY.value,
    "商业公司管理": InstitutionType.COMMERCIAL.value,
    "市场档案信息调研": InstitutionType.COMMERCIAL.value,
}


def extract_institution_info(form_data: dict[str, Any]) -> dict[str, str] | None:
    """从采集表单 ``form_data`` 提取机构信息（名称/区域/等级）。

    ``form_data`` 为按分节 code 嵌套的结构 ``{分节code: {字段名: 值}}``，
    跨分节按字段名匹配机构名称、区域、等级，机构名称缺失则返回 None（不归集）。

    :param form_data: 提交的采集表单数据
    :return: 含 name/region/level 的字典；无机构名称时返回 None
    """
    name: str | None = None
    region: str | None = None
    level: str | None = None
    for section in form_data.values():
        if not isinstance(section, dict):
            continue
        for field_name, value in section.items():
            if not value:
                continue
            if name is None and field_name in _INSTITUTION_NAME_FIELDS:
                name = str(value).strip()
            elif region is None and field_name == "region":
                region = str(value).strip()
            elif level is None and field_name in ("hospital_level", "level"):
                level = str(value).strip()
    if not name:
        return None
    return {"name": name, "region": region or "", "level": level or ""}


def map_institution_type(template_name: str) -> str | None:
    """按二级模板名映射机构类型，未命中返回 None（该模板采集对象非机构主数据）。

    :param template_name: 二级任务模板名
    :return: 机构类型枚举值；未命中返回 None
    """
    return _TEMPLATE_INSTITUTION_TYPE_MAP.get(template_name)


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

    async def collect(
        self,
        name: str,
        institution_type: str,
        level: str | None = None,
        region: str | None = None,
        address: str | None = None,
    ) -> int:
        """按名称归集机构（C 端提交成果时调用），返回机构 ID。

        机构主数据由 C 端提交成果归集产生：按名称查重，找到则复用，找不到则创建。
        运营端不提供手动创建机构的入口（仅查询/修正/停用删除）。

        :param name: 机构名称
        :param institution_type: 机构类型（见 ``InstitutionType``）
        :param level: 机构等级（可选）
        :param region: 所在区域（可选）
        :param address: 详细地址（可选）
        :return: 机构 ID
        """
        existing = await InstitutionCRUD(self.auth, self.db).get(name=name)
        if existing:
            return existing.id
        institution = await InstitutionCRUD(self.auth, self.db).create(
            data={
                "name": name,
                "type": institution_type,
                "level": level or None,
                "region": region or None,
                "address": address or None,
                "status": 0,
            }
        )
        return institution.id

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
