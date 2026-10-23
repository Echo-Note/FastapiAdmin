from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr
from app.modules.market.institution.schema import InstitutionOutSchema


class SubmissionOutSchema(BaseSchema, UserBySchema):
    """成果提交响应模型"""

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int = Field(description="归属任务实例ID")
    user_id: int = Field(description="提交人ID")
    subject_type: str = Field(description="采集对象类型(institution 机构/staff 医务人员·店员/patient 患者)")
    institution_id: int | None = Field(default=None, description="对象机构ID(仅 subject_type=institution 时非空)")
    institution: InstitutionOutSchema | None = Field(default=None, description="对象机构")
    subject_name: str | None = Field(default=None, description="对象名称/昵称(staff/patient 时必填)")
    region: str | None = Field(default=None, description="区域")
    archive_no: str | None = Field(default=None, description="开发档案编号")
    form_data: dict[str, Any] = Field(default_factory=dict, description="采集表单数据")
    status: str = Field(description="成果状态")
    version: int = Field(default=1, description="版本")
    reviewer_id: int | None = Field(default=None, description="审核人ID")
    review_comment: str | None = Field(default=None, description="审核意见")
    reviewed_at: DateTimeStr | None = Field(default=None, description="审核时间")
    ai_check_status: str | None = Field(default=None, description="AI检查状态(预留)")
    ai_check_result: dict[str, Any] | None = Field(default=None, description="AI检查结果(预留)")


class SubmissionCreateSchema(BaseModel):
    """提交成果（草稿或正式提交）"""

    assignment_id: int = Field(gt=0, description="归属任务实例ID")
    subject_type: Literal["institution", "staff", "patient"] = Field(default="institution", description="采集对象类型(institution 机构/staff 医务人员·店员/patient 患者)")
    institution_id: int | None = Field(default=None, gt=0, description="对象机构ID(仅 subject_type=institution 时必填)")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称/昵称(staff/patient 时必填)")
    region: str | None = Field(default=None, max_length=64, description="区域")
    archive_no: str | None = Field(default=None, max_length=64, description="开发档案编号")
    form_data: dict[str, Any] = Field(default_factory=dict, description="采集表单数据")
    status: str = Field(default="DRAFT", description="提交方式(DRAFT:存草稿 PENDING:正式提交)")

    @model_validator(mode="after")
    def validate_subject(self) -> "SubmissionCreateSchema":
        """校验采集对象：机构类必填 institution_id，个人类（staff/patient）必填 subject_name。"""
        if self.subject_type == "institution" and not self.institution_id:
            raise ValueError("采集对象为机构时，对象机构 institution_id 必填")
        if self.subject_type in {"staff", "patient"} and not (self.subject_name and self.subject_name.strip()):
            raise ValueError(f"采集对象为{self.subject_type}时，对象名称 subject_name 必填")
        return self


class SubmissionUpdateSchema(BaseModel):
    """修改成果（草稿编辑或驳回后重提）"""

    subject_type: Literal["institution", "staff", "patient"] | None = Field(default=None, description="采集对象类型")
    institution_id: int | None = Field(default=None, gt=0, description="对象机构ID")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称/昵称")
    region: str | None = Field(default=None, max_length=64, description="区域")
    archive_no: str | None = Field(default=None, max_length=64, description="开发档案编号")
    form_data: dict[str, Any] | None = Field(default=None, description="采集表单数据")


class SubmissionReviewSchema(BaseModel):
    """审核成果（通过 / 驳回）"""

    action: str = Field(description="审核动作(approve:通过 reject:驳回)")
    comment: str | None = Field(default=None, description="审核意见(驳回必填)")

    @model_validator(mode="after")
    def validate_action(self) -> "SubmissionReviewSchema":
        """校验审核动作与意见：驳回必须附意见。"""
        if self.action not in {"approve", "reject"}:
            raise ValueError("审核动作仅支持 approve(通过) 或 reject(驳回)")
        if self.action == "reject" and not (self.comment and self.comment.strip()):
            raise ValueError("驳回必须填写审核意见")
        return self


class SubmissionQueryParam(BaseQueryParam, UserByQueryParam):
    """成果查询参数"""

    assignment_id: int | None = Field(default=None, description="任务实例ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="提交人ID", json_schema_extra={"q": "eq"})
    institution_id: int | None = Field(default=None, description="对象机构ID", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="成果状态", json_schema_extra={"q": "eq"})
