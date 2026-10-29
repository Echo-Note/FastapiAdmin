from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema

from ..base import MarketCRUDBase
from .model import InstitutionImageModel, InstitutionModel
from .schema import (
    InstitutionImageCreateSchema,
    InstitutionImageUpdateSchema,
    InstitutionUpdateSchema,
)


class InstitutionCRUD(MarketCRUDBase[InstitutionModel, dict[str, Any], InstitutionUpdateSchema]):
    """机构数据层（机构由 C 端提交成果归集产生，创建走 ``collect`` 传 dict，不暴露运营端 CreateSchema）。"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=InstitutionModel, auth=auth, db=db)


class InstitutionImageCRUD(MarketCRUDBase[InstitutionImageModel, InstitutionImageCreateSchema, InstitutionImageUpdateSchema]):
    """机构图片数据层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        super().__init__(model=InstitutionImageModel, auth=auth, db=db)
