"""项目（对外）与项目-任务归集的接口层。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute

from .schema import (
    ProjectAddTaskSchema,
    ProjectCreateSchema,
    ProjectOutSchema,
    ProjectQueryParam,
    ProjectStatusUpdateSchema,
    ProjectUpdateSchema,
)
from .service import ProjectService

ProjectRouter = APIRouter(route_class=OperationLogRoute, prefix="/projects", tags=["市场-项目"])


@ProjectRouter.get("/list", summary="查询项目", response_model=ResponseSchema[PageResultSchema[ProjectOutSchema]])
async def get_project_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[ProjectQueryParam, Query()],
) -> JSONResponse:
    result = await ProjectService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="查询项目成功")


@ProjectRouter.get("/detail/{id}", summary="查询项目详情", response_model=ResponseSchema[ProjectOutSchema])
async def get_project_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
) -> JSONResponse:
    result = await ProjectService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取项目详情成功")


@ProjectRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建项目", response_model=ResponseSchema[ProjectOutSchema])
async def create_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:create"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[ProjectCreateSchema, Body(description="创建项目参数")],
) -> JSONResponse:
    result = await ProjectService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="创建项目成功")


@ProjectRouter.put("/update/{id}", summary="修改项目", response_model=ResponseSchema[ProjectOutSchema])
async def update_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    data: Annotated[ProjectUpdateSchema, Body(description="修改项目参数")],
) -> JSONResponse:
    result = await ProjectService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改项目成功")


@ProjectRouter.delete("/delete", summary="删除项目", response_model=ResponseSchema[None])
async def delete_project_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:delete"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    ids: Annotated[list[int], Body(description="ID列表")],
) -> JSONResponse:
    await ProjectService(auth, db).delete(ids=ids)
    return SuccessResponse(msg="删除项目成功")


@ProjectRouter.post("/tasks/{id}", summary="任务归集到项目", response_model=ResponseSchema[ProjectOutSchema])
async def add_project_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    data: Annotated[ProjectAddTaskSchema, Body(description="任务ID")],
) -> JSONResponse:
    result = await ProjectService(auth, db).add_task(id=id, data=data)
    return SuccessResponse(data=result, msg="任务归集到项目成功")


@ProjectRouter.delete("/tasks/{id}/{task_id}", summary="从项目移除任务归集", response_model=ResponseSchema[ProjectOutSchema])
async def remove_project_task_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    task_id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await ProjectService(auth, db).remove_task(id=id, task_id=task_id)
    return SuccessResponse(data=result, msg="移除任务归集成功")


@ProjectRouter.post("/status/{id}", summary="项目状态流转", response_model=ResponseSchema[ProjectOutSchema])
async def change_project_status_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_market:project:update"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="项目ID", ge=1)],
    data: Annotated[ProjectStatusUpdateSchema, Body(description="目标状态")],
) -> JSONResponse:
    result = await ProjectService(auth, db).change_status(id=id, data=data)
    return SuccessResponse(data=result, msg="项目状态流转成功")
