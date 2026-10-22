from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr
from app.modules.market.task.schema import TaskOutSchema


class AssignmentOutSchema(BaseSchema, UserBySchema):
    """任务分派/接收响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_id: int = Field(description="任务ID")
    user_id: int = Field(description="C端用户ID")
    source: str = Field(description="来源(assigned 运营分派/claimed 大厅接单)")
    assign_amount: float = Field(description="本单接收金额(=单价×数量)")
    status: str = Field(description="分派状态")
    accepted_at: DateTimeStr | None = Field(default=None, description="接收时间")
    submitted_at: DateTimeStr | None = Field(default=None, description="首次提交时间")
    task: TaskOutSchema | None = Field(default=None, description="任务")


class AssignmentCreateSchema(BaseModel):
    """分派任务（支持批量：一个任务指派给多个 C 端用户）"""

    task_id: int = Field(gt=0, description="任务ID")
    user_ids: list[int] = Field(min_length=1, description="C端用户ID列表")


class AssignmentQueryParam(BaseQueryParam, UserByQueryParam):
    """任务分派查询参数"""

    task_id: int | None = Field(default=None, description="任务ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="C端用户ID", json_schema_extra={"q": "eq"})
    source: str | None = Field(default=None, description="来源", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="分派状态", json_schema_extra={"q": "eq"})
