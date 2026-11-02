"""工单域 —— C 端（小程序）意见反馈路由。

C 端只做两件事：提交反馈、看自己反馈的处理状态与回复。认证使用 `get_current_user`，
不要求运营端 RBAC 权限码；数据面强制收敛到本人（`created_id`），运营侧仍在管理端
工单页（`/system/ticket/*`）处理与回复同一批记录。

为什么不复用 `/system/ticket/create`：那个接口要求 `module_system:ticket:create`
权限码，普通 C 端用户调用必然 403；而把权限码放开又会让 C 端能传 status/assigned_id。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import db_getter, get_current_user
from app.core.router_class import OperationLogRoute

from .schema import FeedbackCreateSchema, TicketOutSchema
from .service import TicketService

MiniTicketRouter = APIRouter(route_class=OperationLogRoute, prefix="/ticket/mini", tags=["工单-小程序意见反馈"])


@MiniTicketRouter.get("/feedback", summary="我的意见反馈列表", response_model=ResponseSchema[PageResultSchema[TicketOutSchema]])
async def mini_my_feedback_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    page: Annotated[PaginationQueryParam, Depends()],
) -> JSONResponse:
    """我的意见反馈列表（含处理状态与运营回复），只返回本人提交的记录。"""
    result = await TicketService(auth, db).my_page(page_no=page.page_no, page_size=page.page_size)
    return SuccessResponse(data=result, msg="获取我的反馈成功")


@MiniTicketRouter.post("/feedback", summary="提交意见反馈", response_model=ResponseSchema[TicketOutSchema])
async def mini_create_feedback_controller(
    auth: Annotated[AuthSchema, Security(get_current_user)],
    db: Annotated[AsyncSession, Depends(db_getter)],
    data: Annotated[FeedbackCreateSchema, Body(description="意见反馈参数")],
) -> JSONResponse:
    """提交意见反馈（复用 `sys_ticket`，标题由内容首行自动生成）。"""
    result = await TicketService(auth, db).my_create(data=data)
    return SuccessResponse(data=result, msg="提交反馈成功")
