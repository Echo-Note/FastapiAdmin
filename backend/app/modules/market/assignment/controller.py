from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import AssignmentCreateSchema, AssignmentOutSchema, AssignmentQueryParam
from .service import AssignmentService

AssignmentRouter = APIRouter(route_class=OperationLogRoute, prefix="/assignments", tags=["市场-任务分派"])


@AssignmentRouter.get("/list", summary="查询任务分派", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def get_assignment_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    result = await AssignmentService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询任务分派成功")


@AssignmentRouter.get("/detail/{id}", summary="查询任务分派详情", response_model=ResponseSchema[AssignmentOutSchema])
async def get_assignment_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取分派详情成功")


@AssignmentRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="分派任务", response_model=ResponseSchema[list[AssignmentOutSchema]])
async def create_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:assign"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[AssignmentCreateSchema, Body(description="分派参数")],
) -> JSONResponse:
    result = await AssignmentService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="分派任务成功")


@AssignmentRouter.delete("/delete", summary="撤销分派", response_model=ResponseSchema[None])
async def delete_assignment_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:assignment:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await AssignmentService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="撤销分派成功")
