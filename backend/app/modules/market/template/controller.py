from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import TemplateCreateSchema, TemplateOutSchema, TemplateQueryParam, TemplateUpdateSchema
from .service import TemplateService

TemplateRouter = APIRouter(route_class=OperationLogRoute, prefix="/templates", tags=["市场-采集模板"])


@TemplateRouter.get("/list", summary="查询采集模板", response_model=ResponseSchema[PageResultSchema[TemplateOutSchema]])
async def get_template_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[TemplateQueryParam, Query()],
) -> JSONResponse:
    result = await TemplateService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询采集模板成功")


@TemplateRouter.get("/detail/{id}", summary="查询采集模板详情", response_model=ResponseSchema[TemplateOutSchema])
async def get_template_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:template:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="采集模板ID", ge=1)],
) -> JSONResponse:
    result = await TemplateService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="查询采集模板详情成功")


@TemplateRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建采集模板", response_model=ResponseSchema[TemplateOutSchema])
async def create_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:template:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[TemplateCreateSchema, Body(description="创建采集模板参数")],
) -> JSONResponse:
    result = await TemplateService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建采集模板成功")


@TemplateRouter.put("/update/{id}", summary="修改采集模板", response_model=ResponseSchema[TemplateOutSchema])
async def update_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:template:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="采集模板ID", ge=1)],
    data: Annotated[TemplateUpdateSchema, Body(description="修改采集模板参数")],
) -> JSONResponse:
    result = await TemplateService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改采集模板成功")


@TemplateRouter.delete("/delete", summary="删除采集模板", response_model=ResponseSchema[None])
async def delete_template_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:template:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await TemplateService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除采集模板成功")
