"""market 域 CRUD 基类。

通过继承 ``CRUDBase`` 并覆写 ``_build_conditions``，跳过基座的 created_id 数据范围过滤。
market 域的业务归属是业务字段(user_id/company_id/task_id)，而非审计字段 created_id，
数据权限由 Service 层显式控制 —— C 端按 user_id，运营端按 RBAC 权限码。
"""

from typing import Any

from sqlalchemy import false
from sqlalchemy.sql.elements import ColumnElement

from app.core.base_crud import CRUDBase
from app.core.base_model import ModelMixin


class MarketCRUDBase[ModelType: ModelMixin, CreateSchemaType, UpdateSchemaType](CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """market 域 CRUD 基类。"""

    async def _build_conditions(self, include_deleted: bool = False, **kwargs: Any) -> list[ColumnElement]:
        """构造 WHERE 条件：与基座一致，但跳过 created_id 数据范围过滤。

        其余逻辑（软删除过滤、kwargs 动态条件）保持与基座 ``CRUDBase._build_conditions`` 相同。
        """
        conditions: list[ColumnElement] = []

        # 自动排除已删除记录（除非调用方明确要查询已删除数据）
        if hasattr(self.model, "is_deleted") and not include_deleted:
            conditions.append(getattr(self.model, "is_deleted") == false())

        # 业务条件：值类型决定比较方式（tuple → _resolve_condition，其他 → 等值）
        for key, value in kwargs.items():
            if value is None or value == "":
                continue
            attr = getattr(self.model, key)
            if isinstance(value, tuple):
                conditions.extend(self._resolve_condition(attr, value))
            else:
                conditions.append(attr == value)

        return conditions
