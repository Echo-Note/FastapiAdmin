from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import QuotaConfigCreateSchema, QuotaConfigOutSchema, QuotaQueryParam
from .service import QuotaService

QuotaRouter = APIRouter(route_class=OperationLogRoute, prefix="/quota", tags=["市场-限额"])


@QuotaRouter.get("/list", summary="查询限额配置", response_model=ResponseSchema[PageResultSchema[QuotaConfigOutSchema]])
async def get_quota_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:quota:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[QuotaQueryParam, Query()],
) -> JSONResponse:
    result = await QuotaService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询限额配置成功")


@QuotaRouter.post("/save", summary="配置限额(创建或更新)", response_model=ResponseSchema[QuotaConfigOutSchema])
async def save_quota_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:quota:edit"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[QuotaConfigCreateSchema, Body(description="限额配置参数")],
) -> JSONResponse:
    result = await QuotaService(auth, db).save_config(data=data)
    return SuccessResponse(data=result, msg="配置限额成功")


@QuotaRouter.get("/usage", summary="查询限额使用情况", response_model=ResponseSchema[dict])
async def get_quota_usage_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:quota:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    user_id: Annotated[int, Query(description="C端用户ID", ge=1)],
    period: Annotated[str, Query(description="周期(如 2026-10)")],
) -> JSONResponse:
    result = await QuotaService(auth, db).my_quota(user_id=user_id, period=period)
    return SuccessResponse(data=result, msg="查询限额使用情况成功")
