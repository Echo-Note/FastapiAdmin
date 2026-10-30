"""C 端成员档案接口层（运营端）。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import MemberCreateSchema, MemberOutSchema, MemberQueryParam, MemberUpdateSchema
from .service import MemberService

MemberRouter = APIRouter(route_class=OperationLogRoute, prefix="/members", tags=["市场-成员"])


@MemberRouter.get("/list", summary="查询C端成员", response_model=ResponseSchema[PageResultSchema[MemberOutSchema]])
async def get_member_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:member:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[MemberQueryParam, Query()],
) -> JSONResponse:
    result = await MemberService(auth, db).page(
        page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by
    )
    return SuccessResponse(data=result, msg="查询C端成员成功")


@MemberRouter.get("/detail/{id}", summary="查询C端成员详情", response_model=ResponseSchema[MemberOutSchema])
async def get_member_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:member:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成员档案ID", ge=1)],
) -> JSONResponse:
    result = await MemberService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取C端成员详情成功")


@MemberRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="把已有用户纳入C端成员", response_model=ResponseSchema[MemberOutSchema])
async def create_member_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:member:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[MemberCreateSchema, Body(description="纳入C端成员参数")],
) -> JSONResponse:
    result = await MemberService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="纳入C端成员成功")


@MemberRouter.put("/update/{id}", summary="调整成员状态", response_model=ResponseSchema[MemberOutSchema])
async def update_member_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:member:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成员档案ID", ge=1)],
    data: Annotated[MemberUpdateSchema, Body(description="调整成员状态参数")],
) -> JSONResponse:
    result = await MemberService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="调整成员状态成功")
