"""市场管理域 —— 微信小程序端聚合路由。

统一挂载小程序端接口：任务大厅、我的任务、接收任务、提交成果、我的成果、我的额度、机构列表。
认证使用 get_current_user（登录用户），不要求运营端 RBAC 权限码。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import db_getter, get_current_user
from app.core.router_class import OperationLogRoute

from .assignment.schema import AssignmentOutSchema, AssignmentQueryParam
from .assignment.service import AssignmentService
from .institution.schema import InstitutionOutSchema, InstitutionQueryParam
from .institution.service import InstitutionService
from .quota.service import QuotaService
from .submission.schema import SubmissionCreateSchema, SubmissionOutSchema, SubmissionQueryParam, SubmissionUpdateSchema
from .submission.service import SubmissionService

MiniRouter = APIRouter(route_class=OperationLogRoute, prefix="/mini", tags=["市场-小程序"])


@MiniRouter.get("/tasks", summary="任务大厅(待接收任务)", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def mini_task_hall_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """任务大厅：分派给当前用户、待接收的任务。"""
    search = AssignmentQueryParam(status="PENDING")
    result = await AssignmentService(auth, db).my_assignments(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取任务大厅成功")


@MiniRouter.get("/assignments", summary="我的任务", response_model=ResponseSchema[PageResultSchema[AssignmentOutSchema]])
async def mini_my_assignments_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AssignmentQueryParam, Query()],
) -> JSONResponse:
    result = await AssignmentService(auth, db).my_assignments(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=result, msg="获取我的任务成功")


@MiniRouter.post("/assignments/{id}/accept", summary="接收任务", response_model=ResponseSchema[AssignmentOutSchema])
async def mini_accept_assignment_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    id: Annotated[int, Path(description="分派ID", ge=1)],
) -> JSONResponse:
    result = await AssignmentService(auth, db).accept(id=id)
    return SuccessResponse(data=result, msg="接收任务成功")


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


@MiniRouter.get("/quota", summary="我的额度/收益", response_model=ResponseSchema[dict])
async def mini_my_quota_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    period: Annotated[str, Query(description="周期(如 2026-10)")],
) -> JSONResponse:
    result = await QuotaService(auth, db).my_quota(user_id=auth.user.id, period=period)
    return SuccessResponse(data=result, msg="获取我的额度成功")


@MiniRouter.get("/institutions", summary="机构列表(提交成果选择)", response_model=ResponseSchema[PageResultSchema[InstitutionOutSchema]])
async def mini_institution_list_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """机构列表：供 C 端（小程序）用户提交成果时选择对象机构。

    复用运营端 InstitutionService 分页查询，仅返回启用机构（status=0）；
    认证使用 get_current_user（登录用户），不要求运营端 RBAC 权限码。
    """
    search = InstitutionQueryParam(status=0)
    result = await InstitutionService(auth, db).page(page_no=page.page_no, page_size=page.page_size, search=search, order_by=page.order_by)
    return SuccessResponse(data=result, msg="获取机构列表成功")
