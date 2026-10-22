from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import ReportCreateSchema, ReportOutSchema, ReportQueryParam
from .service import ReportService

ReportRouter = APIRouter(route_class=OperationLogRoute, prefix="/reports", tags=["市场-报告"])


@ReportRouter.get("/list", summary="查询报告", response_model=ResponseSchema[PageResultSchema[ReportOutSchema]])
async def get_report_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ReportQueryParam, Query()],
) -> JSONResponse:
    result = await ReportService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询报告成功")


@ReportRouter.get("/detail/{id}", summary="查询报告详情", response_model=ResponseSchema[ReportOutSchema])
async def get_report_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="报告ID", ge=1)],
) -> JSONResponse:
    result = await ReportService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取报告详情成功")


@ReportRouter.post("/generate", status_code=status.HTTP_201_CREATED, summary="生成报告", response_model=ResponseSchema[ReportOutSchema])
async def generate_report_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:report:add"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ReportCreateSchema, Body(description="生成报告参数")],
) -> JSONResponse:
    result = await ReportService(auth, db).generate(data=data)
    return SuccessResponse(data=result, msg="生成报告成功")
