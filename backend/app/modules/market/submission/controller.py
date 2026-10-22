from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import SubmissionOutSchema, SubmissionQueryParam, SubmissionReviewSchema
from .service import SubmissionService

SubmissionRouter = APIRouter(route_class=OperationLogRoute, prefix="/submissions", tags=["市场-成果审核"])


@SubmissionRouter.get("/list", summary="查询成果(审核列表)", response_model=ResponseSchema[PageResultSchema[SubmissionOutSchema]])
async def get_submission_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubmissionQueryParam, Query()],
) -> JSONResponse:
    result = await SubmissionService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询成果成功")


@SubmissionRouter.get("/detail/{id}", summary="查询成果详情", response_model=ResponseSchema[SubmissionOutSchema])
async def get_submission_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
) -> JSONResponse:
    result = await SubmissionService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取成果详情成功")


@SubmissionRouter.post("/review/{id}", summary="审核成果(通过/驳回)", response_model=ResponseSchema[SubmissionOutSchema])
async def review_submission_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:submission:review"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
    data: Annotated[SubmissionReviewSchema, Body(description="审核参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).review(id=id, data=data)
    return SuccessResponse(data=result, msg="审核成果成功")
