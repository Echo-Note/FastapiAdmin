from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import SettlementOutSchema, SettlementQueryParam
from .service import SettlementService

SettlementRouter = APIRouter(route_class=OperationLogRoute, prefix="/settlements", tags=["市场-结算"])


@SettlementRouter.get("/list", summary="查询结算单", response_model=ResponseSchema[PageResultSchema[SettlementOutSchema]])
async def get_settlement_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SettlementQueryParam, Query()],
) -> JSONResponse:
    result = await SettlementService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询结算单成功")


@SettlementRouter.get("/detail/{id}", summary="查询结算单详情", response_model=ResponseSchema[SettlementOutSchema])
async def get_settlement_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:settlement:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="结算单ID", ge=1)],
) -> JSONResponse:
    result = await SettlementService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取结算单详情成功")
