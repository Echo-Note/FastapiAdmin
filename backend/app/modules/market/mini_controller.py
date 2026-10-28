"""市场管理域 —— 微信小程序端聚合路由。

统一挂载小程序端接口：任务大厅、任务单详情、我的任务、分派单详情、接收任务、大厅接单、
提交成果、我的成果、我的发放/津贴、机构列表。
认证使用 ``get_current_user``（登录用户），不要求运营端 RBAC 权限码。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security
from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import db_getter, get_current_user, redis_getter
from app.core.router_class import OperationLogRoute

from .institution.schema import InstitutionOutSchema
from .institution.service import InstitutionService
from .payout.service import PayoutService
from .task.schema import (
    AssignmentOutSchema,
    AssignmentQueryParam,
    SubmissionCreateSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionUpdateSchema,
    TaskOutSchema,
)
from .task.service import AssignmentService, SubmissionService, TaskService

MiniRouter = APIRouter(route_class=OperationLogRoute, prefix="/mini", tags=["市场-小程序"])


@MiniRouter.get("/tasks", summary="任务大厅(公开接单任务)", response_model=ResponseSchema[PageResultSchema[TaskOutSchema]])
async def mini_task_hall_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """任务大厅：公开接单任务列表（定向分派任务走「我的任务」）。"""
    result = await TaskService(auth, db).hall_tasks(redis=redis, page_no=page.page_no, page_size=page.page_size)
    return SuccessResponse(data=result, msg="获取任务大厅成功")


@MiniRouter.get("/tasks/{id}", summary="任务单详情", response_model=ResponseSchema[TaskOutSchema])
async def mini_task_detail_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    """任务单详情：小程序任务详情页现取模板与单价。"""
    result = await TaskService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取任务详情成功")


@MiniRouter.get("/assignments", summary="我的任务", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def mini_my_assignments_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    result = await AssignmentService(auth, db).my_assignments(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取我的任务成功")


@MiniRouter.get("/assignments/{id}", summary="分派单详情", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_assignment_detail_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    """分派单详情：小程序提交成果页现取模板。"""
    result = await AssignmentService(auth, db).detail(id=id)
    return SuccessResponse(data=result, msg="获取分派详情成功")


@MiniRouter.post("/assignments/{id}/accept", summary="接收任务", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_accept_assignment_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).accept(id=id)
    return SuccessResponse(data=result, msg="接收任务成功")


@MiniRouter.post("/tasks/{id}/claim", summary="大厅接单", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_claim_task_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    id: Annotated[int, Path(description="任务ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).claim(task_id=id, redis=redis)
    return SuccessResponse(data=result, msg="接单成功")


@MiniRouter.post("/submissions", summary="提交成果", response_model=ResponseSchema[SubmissionOutSchema])
async def mini_create_submission_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[SubmissionCreateSchema, Body(description="提交成果参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).create(data=data)
    return SuccessResponse(data=result, msg="提交成果成功")


@MiniRouter.put("/submissions/{id}", summary="修改成果(草稿/驳回重提)", response_model=ResponseSchema[SubmissionOutSchema])
async def mini_update_submission_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="成果ID", ge=1)],
    data: Annotated[SubmissionUpdateSchema, Body(description="修改成果参数")],
) -> JSONResponse:
    result = await SubmissionService(auth, db).update(id=id, data=data)
    return SuccessResponse(data=result, msg="修改成果成功")


@MiniRouter.get("/submissions", summary="我的成果", response_model=ResponseSchema[PageResultSchema[SubmissionOutSchema]])
async def mini_my_submissions_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[SubmissionQueryParam, Query()],
) -> JSONResponse:
    result = await SubmissionService(auth, db).my_submissions(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取我的成果成功")


@MiniRouter.get("/payout", summary="我的发放/津贴", response_model=ResponseSchema[dict])
async def mini_my_payout_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    period: Annotated[str, Query(description="周期(如 2026-03)")],
) -> JSONResponse:
    result = await PayoutService(auth, db).my_payout(user_id=auth.user.id, period=period)
    return SuccessResponse(data=result, msg="获取我的发放信息成功")


@MiniRouter.get("/institutions", summary="机构列表(提交成果选择)", response_model=ResponseSchema[PageResultSchema[InstitutionOutSchema]])
async def mini_institution_list_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    redis: Annotated[Redis, Depends(redis_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """机构列表：供 C 端（小程序）用户提交成果时选择对象机构。

    从 Redis 缓存读取启用机构全量列表后内存分页；认证使用 get_current_user。
    """
    items = await InstitutionService(auth, db).enabled_list(redis=redis)
    total = len(items)
    start = (page.page_no - 1) * page.page_size
    page_items = items[start : start + page.page_size]
    result = PageResultSchema(
        page_no=page.page_no,
        page_size=page.page_size,
        total=total,
        has_next=start + page.page_size < total,
        items=page_items,
    )
    return SuccessResponse(data=result, msg="获取机构列表成功")
