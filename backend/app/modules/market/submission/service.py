from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from ..assignment.crud import AssignmentCRUD
from ..enums import AssignmentStatus, SubmissionStatus, TaskKind
from ..institution.crud import InstitutionCRUD
from .crud import SubmissionCRUD
from .schema import (
    SubmissionCreateSchema,
    SubmissionOutSchema,
    SubmissionQueryParam,
    SubmissionReviewSchema,
    SubmissionUpdateSchema,
)

# institution 为 UserBySchema（含 created_by/updated_by），必须嵌套预加载其审计关系，
# 否则 detail() 序列化时会在异步环境下触发懒加载 MissingGreenlet
_SUBMISSION_PRELOAD = ["institution", "institution.created_by", "institution.updated_by"]


def _validate_form(form_schema: list[dict[str, Any]], form_data: dict[str, Any]) -> None:
    """规则校验：按任务模板字段定义检查必填完整性。

    一期仅做「必填字段非空」校验；字段格式/数值范围可在此基础上扩展。
    """
    for field in form_schema:
        if not field.get("required"):
            continue
        name = field.get("name")
        if not name:
            continue
        value = form_data.get(name)
        if value is None or value == "":
            raise CustomException(msg=f"必填字段「{field.get('label') or name}」缺失")


class SubmissionService:
    """成果提交与审核服务"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def detail(self, id: int) -> SubmissionOutSchema:
        """查询成果详情。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id, preload=_SUBMISSION_PRELOAD)
        return SubmissionOutSchema.model_validate(submission)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: SubmissionQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[SubmissionOutSchema]:
        """分页查询成果（运营审核列表）。"""
        offset = (page_no - 1) * page_size
        return await SubmissionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=search_to_dict(search),
            out_schema=SubmissionOutSchema,
            preload=_SUBMISSION_PRELOAD,
        )

    async def create(self, data: SubmissionCreateSchema) -> SubmissionOutSchema:
        """提交成果（草稿或正式提交）。

        分类提交约束：
        - 周期性任务：单用户单月仅一次正式提交；
        - 定额任务：单用户单月可重复提交，不限次（名额限量已在接单环节占用）。
        """
        assignment = await AssignmentCRUD(self.auth, self.db).get_or_404(
            id=data.assignment_id, msg="任务实例不存在", preload=["task", "task.task_type"]
        )
        if assignment.user_id != self.auth.user.id:
            raise CustomException(msg="无权向该任务提交成果")
        if assignment.status not in {AssignmentStatus.ACCEPTED.value, AssignmentStatus.SUBMITTING.value, AssignmentStatus.SUBMITTED.value}:
            raise CustomException(msg="任务尚未接收或已结束，无法提交成果")
        await InstitutionCRUD(self.auth, self.db).get_or_404(id=data.institution_id, msg="机构不存在")

        task = assignment.task
        period = task.period

        # 正式提交时执行规则校验与分类提交约束；草稿不校验
        if data.status == SubmissionStatus.PENDING.value:
            _validate_form(task.task_type.form_schema, data.form_data)
            if task.task_kind == TaskKind.PERIODIC.value:
                # 周期任务：单用户单月仅一次正式提交
                existed = await SubmissionCRUD(self.auth, self.db).get_list(
                    search={"assignment_id": assignment.id, "period": period}
                )
                if any(s.status != SubmissionStatus.DRAFT.value for s in existed):
                    raise CustomException(msg="本月已提交，周期性任务单月仅可提交一次")
            # 定额任务：单用户单月可重复提交，不限次（名额限量已在接单环节占用）

        submission = await SubmissionCRUD(self.auth, self.db).create(
            data={**data.model_dump(), "user_id": self.auth.user.id, "period": period}
        )

        # 驱动分派状态流转：草稿 → 进行中，正式提交 → 已提交
        if data.status == SubmissionStatus.PENDING.value:
            await AssignmentCRUD(self.auth, self.db).update(
                id=assignment.id,
                data={"status": AssignmentStatus.SUBMITTED.value, "submitted_at": datetime.now(UTC)},
            )
        elif assignment.status == AssignmentStatus.ACCEPTED.value:
            await AssignmentCRUD(self.auth, self.db).update(id=assignment.id, data={"status": AssignmentStatus.SUBMITTING.value})

        return await self.detail(id=submission.id)

    async def update(self, id: int, data: SubmissionUpdateSchema) -> SubmissionOutSchema:
        """修改成果（草稿编辑或驳回后重提）。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id, preload=_SUBMISSION_PRELOAD)
        if submission.user_id != self.auth.user.id:
            raise CustomException(msg="无权修改该成果")
        if submission.status not in {SubmissionStatus.DRAFT.value, SubmissionStatus.REJECTED.value}:
            raise CustomException(msg="仅草稿或已驳回的成果可修改")

        new_data: dict[str, Any] = data.model_dump(exclude_unset=True, exclude_none=True)
        # 驳回重提：版本 +1，重新进入待审核
        if submission.status == SubmissionStatus.REJECTED.value:
            new_data["version"] = submission.version + 1
            new_data["status"] = SubmissionStatus.PENDING.value

        await SubmissionCRUD(self.auth, self.db).update(id=id, data=new_data)
        return await self.detail(id=id)

    async def review(self, id: int, data: SubmissionReviewSchema) -> SubmissionOutSchema:
        """审核成果：通过 / 驳回。"""
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id)
        if submission.status != SubmissionStatus.PENDING.value:
            raise CustomException(msg="该成果不在待审核状态")

        update_data: dict[str, Any] = {
            "reviewer_id": self.auth.user.id,
            "reviewed_at": datetime.now(UTC),
        }
        if data.action == "approve":
            update_data["status"] = SubmissionStatus.APPROVED.value
        else:
            update_data["status"] = SubmissionStatus.REJECTED.value
            update_data["review_comment"] = data.comment

        await SubmissionCRUD(self.auth, self.db).update(id=id, data=update_data)
        return await self.detail(id=id)

    async def my_detail(self, id: int) -> SubmissionOutSchema:
        """我的成果详情（C 端）：只允许看自己的成果，越权按「不存在」处理。

        驳回后修改重提要回填原表单，C 端需要一个不带 RBAC 权限码的详情入口。
        """
        submission = await SubmissionCRUD(self.auth, self.db).get_or_404(id=id, msg="成果不存在", preload=_SUBMISSION_PRELOAD)
        if submission.user_id != self.auth.user.id:
            raise CustomException(msg="成果不存在")
        return SubmissionOutSchema.model_validate(submission)

    async def my_submissions(
        self,
        page_no: int,
        page_size: int,
        search: SubmissionQueryParam | None = None,
    ) -> PageResultSchema[SubmissionOutSchema]:
        """我的成果列表（小程序端）。"""
        cond = search_to_dict(search) or {}
        cond["user_id"] = self.auth.user.id
        offset = (page_no - 1) * page_size
        return await SubmissionCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=[{"id": "desc"}],
            search=cond,
            out_schema=SubmissionOutSchema,
            preload=_SUBMISSION_PRELOAD,
        )
