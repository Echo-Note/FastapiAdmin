"""任务管理域 Schema 定义。

输出 Schema 继承 ``BaseSchema``（基础字段）与 ``UserBySchema``（审计人），
输入 Schema 用 Pydantic ``Field`` 做入参校验；查询参数继承 ``BaseQueryParam`` 与
``UserByQueryParam``，配合 ``json_schema_extra={"q": ...}`` 控制操作符。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateStr, DateTimeStr

from ..config import TaskConfig, TaskItemConfig


class TaskCategoryOutSchema(BaseSchema, UserBySchema):
    """一级任务分类响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="分类编号")
    name: str = Field(description="分类名")
    sort: int = Field(default=0, description="排序(越小越靠前)")
    description: str | None = Field(default=None, description="分类描述")


class TaskCategoryCreateSchema(BaseModel):
    """创建一级任务分类"""

    name: str = Field(min_length=1, max_length=128, description="分类名")
    sort: int = Field(default=0, description="排序(越小越靠前)")
    description: str | None = Field(default=None, description="分类描述")


class TaskCategoryUpdateSchema(BaseModel):
    """更新一级任务分类"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="分类名")
    sort: int | None = Field(default=None, description="排序(越小越靠前)")
    description: str | None = Field(default=None, description="分类描述")


class TaskCategoryQueryParam(BaseQueryParam, UserByQueryParam):
    """一级任务分类查询参数"""

    code: str | None = Field(default=None, description="分类编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="分类名", json_schema_extra={"q": "like"})


class TaskTemplateOutSchema(BaseSchema, UserBySchema):
    """二级任务模板响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="模板编号")
    name: str = Field(description="模板名")
    category_id: int = Field(description="所属一级分类ID")
    category: TaskCategoryOutSchema | None = Field(default=None, description="所属一级分类")
    config: TaskConfig | None = Field(default=None, description="任务设计配置(TaskConfig 结构)")
    enabled: bool = Field(default=True, description="是否启用")
    items: list["TaskItemOutSchema"] = Field(default_factory=list, description="其下三级任务")


class TaskItemOutSchema(BaseSchema, UserBySchema):
    """三级任务响应模型"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="任务编号")
    name: str = Field(description="任务名")
    template_id: int = Field(description="所属二级模板ID")
    config: TaskItemConfig | None = Field(default=None, description="任务设计配置(TaskItemConfig 结构)")
    sort: int = Field(default=0, description="排序(越小越靠前)")
    enabled: bool = Field(default=True, description="是否启用")


class TaskItemCreateSchema(BaseModel):
    """创建三级任务"""

    name: str = Field(min_length=1, max_length=128, description="任务名")
    template_id: int = Field(gt=0, description="所属二级模板ID")
    config: TaskItemConfig = Field(description="任务设计配置(TaskItemConfig 结构)")
    sort: int = Field(default=0, description="排序(越小越靠前)")
    enabled: bool = Field(default=True, description="是否启用")


class TaskItemUpdateSchema(BaseModel):
    """更新三级任务"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="任务名")
    template_id: int | None = Field(default=None, gt=0, description="所属二级模板ID")
    config: TaskItemConfig | None = Field(default=None, description="任务设计配置(TaskItemConfig 结构)")
    sort: int | None = Field(default=None, description="排序(越小越靠前)")
    enabled: bool | None = Field(default=None, description="是否启用")


class TaskItemQueryParam(BaseQueryParam, UserByQueryParam):
    """三级任务查询参数"""

    code: str | None = Field(default=None, description="任务编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="任务名", json_schema_extra={"q": "like"})
    template_id: int | None = Field(default=None, description="二级模板ID", json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(default=None, description="是否启用", json_schema_extra={"q": "eq"})


class TaskItemTreeOutSchema(BaseSchema):
    """三级任务（任务目录树三级节点）"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="任务编号")
    name: str = Field(description="任务名")
    config: TaskItemConfig | None = Field(default=None, description="任务设计配置(TaskItemConfig 结构)")
    sort: int = Field(default=0, description="排序(越小越靠前)")
    enabled: bool = Field(default=True, description="是否启用")


class TaskTemplateTreeOutSchema(BaseSchema, UserBySchema):
    """二级任务模板（任务目录树子节点，含其下三级任务，不含 category 嵌套）"""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(description="模板编号")
    name: str = Field(description="模板名")
    category_id: int = Field(description="所属一级分类ID")
    category_name: str | None = Field(default=None, description="所属一级分类名称")
    config: TaskConfig | None = Field(default=None, description="任务设计配置(TaskConfig 结构)")
    enabled: bool = Field(default=True, description="是否启用")
    items: list[TaskItemTreeOutSchema] = Field(default_factory=list, description="其下三级任务")


class TaskCategoryTreeSchema(TaskCategoryOutSchema):
    """一级任务分类树（含其下二级模板，模板含三级任务）"""

    children: list[TaskTemplateTreeOutSchema] = Field(default_factory=list, description="其下二级模板")


class TaskTemplateCreateSchema(BaseModel):
    """创建二级任务模板"""

    name: str = Field(min_length=1, max_length=128, description="模板名")
    category_id: int = Field(gt=0, description="所属一级分类ID")
    config: TaskConfig = Field(description="任务设计配置(TaskConfig 结构)")
    enabled: bool = Field(default=True, description="是否启用")


class TaskTemplateUpdateSchema(BaseModel):
    """更新二级任务模板"""

    name: str | None = Field(default=None, min_length=1, max_length=128, description="模板名")
    category_id: int | None = Field(default=None, gt=0, description="所属一级分类ID")
    config: TaskConfig | None = Field(default=None, description="任务设计配置(TaskConfig 结构)")
    enabled: bool | None = Field(default=None, description="是否启用")


class TaskTemplateQueryParam(BaseQueryParam, UserByQueryParam):
    """二级任务模板查询参数"""

    code: str | None = Field(default=None, description="模板编码", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="模板名", json_schema_extra={"q": "like"})
    category_id: int | None = Field(default=None, description="一级分类ID", json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(default=None, description="是否启用", json_schema_extra={"q": "eq"})


class TaskOutSchema(BaseSchema, UserBySchema):
    """任务实例响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_no: str = Field(description="任务编号")
    project_id: int = Field(description="所属项目ID")
    template_id: int = Field(description="所属二级模板ID")
    template: TaskTemplateOutSchema | None = Field(default=None, description="所属二级模板(含分类)")
    name: str = Field(description="C端显示名")
    period: DateStr = Field(description="截止日期(继承项目截止日期)")
    assign_mode: str = Field(default="direct", description="分配方式(direct 定向分派/open 公开大厅)")
    status: str = Field(default="DRAFT", description="任务状态")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    published_at: DateTimeStr | None = Field(default=None, description="发布时间")


class TaskCreateSchema(BaseModel):
    """创建任务"""

    project_id: int = Field(gt=0, description="所属项目ID")
    template_id: int = Field(gt=0, description="所属二级模板ID")
    name: str = Field(min_length=1, max_length=256, description="C端显示名(如 一心坦-等级医院管理)")
    period: DateStr = Field(description="截止日期(继承项目截止日期，如 2026-12-31)")
    assign_mode: Literal["direct", "open"] = Field(default="direct", description="分配方式(direct 定向分派/open 公开大厅)")


class TaskUpdateSchema(BaseModel):
    """更新任务"""

    project_id: int | None = Field(default=None, gt=0, description="所属项目ID")
    template_id: int | None = Field(default=None, gt=0, description="所属二级模板ID")
    name: str | None = Field(default=None, min_length=1, max_length=256, description="C端显示名")
    period: DateStr | None = Field(default=None, description="截止日期")
    assign_mode: Literal["direct", "open"] | None = Field(default=None, description="分配方式")


class TaskQueryParam(BaseQueryParam, UserByQueryParam):
    """任务实例查询参数"""

    task_no: str | None = Field(default=None, description="任务编号", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="C端显示名", json_schema_extra={"q": "like"})
    project_id: int | None = Field(default=None, description="所属项目ID", json_schema_extra={"q": "eq"})
    template_id: int | None = Field(default=None, description="所属二级模板ID", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    assign_mode: str | None = Field(default=None, description="分配方式", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="任务状态", json_schema_extra={"q": "eq"})


class TaskStatusUpdateSchema(BaseModel):
    """任务状态流转"""

    status: Literal["PUBLISHED", "IN_PROGRESS", "COMPLETED", "SETTLED", "ARCHIVED"] = Field(description="目标状态")


class AssignmentOutSchema(BaseSchema, UserBySchema):
    """任务分配/接收响应模型"""

    model_config = ConfigDict(from_attributes=True)

    task_id: int = Field(description="任务ID")
    task: TaskOutSchema | None = Field(default=None, description="任务(含名称/周期/模板，供 C 端展示)")
    user_id: int = Field(description="执行用户ID")
    source: str = Field(default="assigned", description="来源(assigned 运营分派/claimed 大厅接单)")
    status: str = Field(default="PENDING", description="分配状态")
    accepted_at: DateTimeStr | None = Field(default=None, description="接收时间")
    submitted_at: DateTimeStr | None = Field(default=None, description="提交时间")


class AssignmentCreateSchema(BaseModel):
    """创建任务分配（批量：一个任务指派给多个 C 端用户）"""

    task_id: int = Field(gt=0, description="任务ID")
    user_ids: list[int] = Field(min_length=1, description="执行用户ID列表")
    source: Literal["assigned", "claimed"] = Field(default="assigned", description="来源(assigned 运营分派/claimed 大厅接单)")


class TaskPublishSchema(BaseModel):
    """发布任务参数（定向分派任务须指定分派人员）"""

    assignee_ids: list[int] | None = Field(default=None, description="定向分派人员ID列表(分配方式为 direct 时必填，open 时忽略)")


class AssignmentUpdateSchema(BaseModel):
    """更新任务分配"""

    source: Literal["assigned", "claimed"] | None = Field(default=None, description="来源")
    status: str | None = Field(default=None, max_length=32, description="分配状态")


class AssignmentQueryParam(BaseQueryParam, UserByQueryParam):
    """任务分配查询参数"""

    task_id: int | None = Field(default=None, description="任务ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="执行用户ID", json_schema_extra={"q": "eq"})
    source: str | None = Field(default=None, description="来源", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="分配状态", json_schema_extra={"q": "eq"})


class SubmissionOutSchema(BaseSchema, UserBySchema):
    """成果提交响应模型"""

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int = Field(description="分配ID")
    user_id: int = Field(description="提交用户ID")
    subject_type: str = Field(default="institution", description="采集对象类型(institution/staff/patient/meeting)")
    institution_id: int | None = Field(default=None, description="机构ID(对象为机构时)")
    subject_name: str | None = Field(default=None, description="对象名称(非机构对象时)")
    region: str | None = Field(default=None, description="所在区域")
    archive_no: str | None = Field(default=None, description="档案编号")
    period: str = Field(description="提交月份(如 2026-03)")
    form_data: dict = Field(description="采集表单数据")
    status: str = Field(default="DRAFT", description="成果状态")
    version: int = Field(default=1, description="版本号(驳回重提 +1)")
    reviewer_id: int | None = Field(default=None, description="审核人ID")
    review_comment: str | None = Field(default=None, description="审核意见")
    reviewed_at: DateTimeStr | None = Field(default=None, description="审核时间")
    ai_check_status: str | None = Field(default=None, description="AI 预检状态")
    ai_check_result: dict | None = Field(default=None, description="AI 预检结果")


class SubmissionCreateSchema(BaseModel):
    """创建成果提交"""

    assignment_id: int = Field(gt=0, description="分配ID")
    subject_type: Literal["institution", "staff", "patient", "meeting"] = Field(default="institution", description="采集对象类型")
    institution_id: int | None = Field(default=None, gt=0, description="机构ID(对象为机构时)")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称(非机构对象时)")
    region: str | None = Field(default=None, max_length=64, description="所在区域")
    archive_no: str | None = Field(default=None, max_length=64, description="档案编号")
    period: str = Field(min_length=1, max_length=16, description="提交月份(如 2026-03)")
    form_data: dict = Field(description="采集表单数据")


class SubmissionUpdateSchema(BaseModel):
    """更新成果提交(草稿/驳回重提)"""

    subject_type: Literal["institution", "staff", "patient", "meeting"] | None = Field(default=None, description="采集对象类型")
    institution_id: int | None = Field(default=None, gt=0, description="机构ID")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称")
    region: str | None = Field(default=None, max_length=64, description="所在区域")
    archive_no: str | None = Field(default=None, max_length=64, description="档案编号")
    period: str | None = Field(default=None, min_length=1, max_length=16, description="提交月份")
    form_data: dict | None = Field(default=None, description="采集表单数据")


class SubmissionQueryParam(BaseQueryParam, UserByQueryParam):
    """成果提交查询参数"""

    assignment_id: int | None = Field(default=None, description="分配ID", json_schema_extra={"q": "eq"})
    user_id: int | None = Field(default=None, description="提交用户ID", json_schema_extra={"q": "eq"})
    subject_type: str | None = Field(default=None, description="采集对象类型", json_schema_extra={"q": "eq"})
    institution_id: int | None = Field(default=None, description="机构ID", json_schema_extra={"q": "eq"})
    archive_no: str | None = Field(default=None, description="档案编号", json_schema_extra={"q": "eq"})
    period: str | None = Field(default=None, description="提交月份", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="成果状态", json_schema_extra={"q": "eq"})
    ai_check_status: str | None = Field(default=None, description="AI 预检状态", json_schema_extra={"q": "eq"})


class SubmissionReviewSchema(BaseModel):
    """成果审核"""

    approved: bool = Field(description="是否通过")
    review_comment: str | None = Field(default=None, description="审核意见(驳回时建议填写)")
