"""任务管理域 Schema 定义。

输出 Schema 继承 ``BaseSchema``（基础字段）与 ``UserBySchema``（审计人），
输入 Schema 用 Pydantic ``Field`` 做入参校验；查询参数继承 ``BaseQueryParam`` 与
``UserByQueryParam``，配合 ``json_schema_extra={"q": ...}`` 控制操作符。
"""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateStr, DateTimeStr
from app.modules.market.form_schema import FormSchemaSection

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


class TaskProjectBriefSchema(BaseSchema):
    """任务所属项目摘要"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(description="项目名")
    code: str | None = Field(default=None, description="项目编号")


class TaskOutSchema(BaseSchema, UserBySchema):
    """任务实例响应模型（细化到三级任务粒度）"""

    model_config = ConfigDict(from_attributes=True)

    task_no: str = Field(description="任务编号")
    project_id: int = Field(description="所属项目ID")
    project: TaskProjectBriefSchema | None = Field(default=None, description="所属项目")
    template_id: int = Field(description="所属二级模板ID")
    template: TaskTemplateOutSchema | None = Field(default=None, description="所属二级模板(含分类)")
    item_id: int | None = Field(default=None, description="所属任务ID(叶子模板为空)")
    item: TaskItemOutSchema | None = Field(default=None, description="所属任务")
    name: str = Field(description="C端显示名")
    period: DateStr = Field(description="截止日期(继承项目截止日期)")
    assign_mode: str = Field(default="open", description="分配方式(direct 定向分派/open 公开大厅)")
    status: str = Field(default="DRAFT", description="任务状态")
    publisher_id: int | None = Field(default=None, description="发布人ID")
    published_at: DateTimeStr | None = Field(default=None, description="发布时间")
    assignment_count: int = Field(default=0, description="已分派/接收人数(列表聚合字段)")
    exec_standard: str | None = Field(default=None, description="执行标准(item.config 优先，回退 template.config)")
    executor_requirement: str | None = Field(default=None, description="执行要求(item.config 优先，回退 template.config)")


class MyAssignmentStatsOutSchema(BaseModel):
    """C 端「我的任务」待办计数（TabBar / 状态 Tab 角标）

    按分派状态分组计数，另附被驳回成果数——驳回不体现在分派状态上，
    但它是 C 端唯一必须立刻返工的事，角标必须把它算进去。
    """

    pending: int = Field(default=0, description="待接收数")
    accepted: int = Field(default=0, description="进行中数(已接收待提交)")
    submitted: int = Field(default=0, description="已提交数")
    reviewed: int = Field(default=0, description="已审核数")
    settled: int = Field(default=0, description="已结算数")
    rejected_submissions: int = Field(default=0, description="被驳回成果数(需修改重提)")


class MiniTaskGroupSchema(BaseModel):
    """C 端按项目分组的最小单元任务组。"""

    project_id: int = Field(description="项目ID")
    project_name: str = Field(description="项目名")
    period: DateStr | None = Field(default=None, description="项目截止日期")
    tasks: list[TaskOutSchema] = Field(default_factory=list, description="该项目下最小单元任务")


class MiniAssignmentGroupSchema(BaseModel):
    """C 端按项目分组的分派单组（我的任务）。

    与 ``MiniTaskGroupSchema`` 区别：元素为分派单（含 id/status/task），
    而非纯任务，供「我的任务」状态筛选、进度轨道与成果角标使用。
    """

    project_id: int = Field(description="项目ID")
    project_name: str = Field(description="项目名")
    period: DateStr | None = Field(default=None, description="项目截止日期")
    assignments: list["AssignmentOutSchema"] = Field(default_factory=list, description="该项目下分派单")


class TaskCreateSchema(BaseModel):
    """创建任务（名称由后端自动生成）。

    ``item_id`` / ``template_id`` 恰好一个非空：有三级任务的模板传 item_id，
    无三级任务的叶子模板（如会议服务）传 template_id。
    """

    project_id: int = Field(gt=0, description="所属项目ID")
    item_id: int | None = Field(default=None, gt=0, description="所属任务ID")
    template_id: int | None = Field(default=None, gt=0, description="所属叶子模板ID(无三级任务时)")
    period: DateStr = Field(description="截止日期(继承项目截止日期，如 2026-12-31)")
    assign_mode: Literal["direct", "open"] = Field(default="open", description="分配方式(direct 定向分派/open 公开大厅)")

    @model_validator(mode="after")
    def _check_unit(self) -> "TaskCreateSchema":
        """校验 item_id 与 template_id 恰好一个非空。"""
        if (self.item_id is None) == (self.template_id is None):
            raise ValueError("item_id 与 template_id 必须恰好提供一个")
        return self


class TaskUpdateSchema(BaseModel):
    """更新任务"""

    project_id: int | None = Field(default=None, gt=0, description="所属项目ID")
    item_id: int | None = Field(default=None, gt=0, description="所属任务ID")
    template_id: int | None = Field(default=None, gt=0, description="所属叶子模板ID(无三级任务时)")
    period: DateStr | None = Field(default=None, description="截止日期")
    assign_mode: Literal["direct", "open"] | None = Field(default=None, description="分配方式")

    @model_validator(mode="after")
    def _check_unit(self) -> "TaskUpdateSchema":
        """校验 item_id 与 template_id 不同时提供。"""
        if self.item_id is not None and self.template_id is not None:
            raise ValueError("item_id 与 template_id 不能同时提供")
        return self


class TaskQueryParam(BaseQueryParam, UserByQueryParam):
    """任务实例查询参数"""

    task_no: str | None = Field(default=None, description="任务编号", json_schema_extra={"q": "like"})
    name: str | None = Field(default=None, description="C端显示名", json_schema_extra={"q": "like"})
    project_id: int | None = Field(default=None, description="所属项目ID", json_schema_extra={"q": "eq"})
    template_id: int | None = Field(default=None, description="所属二级模板ID", json_schema_extra={"q": "eq"})
    item_id: int | None = Field(default=None, description="所属三级任务ID", json_schema_extra={"q": "eq"})
    category_id: int | None = Field(default=None, description="一级分类ID", json_schema_extra={"q": "eq"})
    exclude_status: str | None = Field(default=None, description="排除的任务状态(如 DRAFT)")
    include_closed_project: bool = Field(default=False, description="是否包含已关闭/已删除项目的任务(默认排除)")
    period: str | None = Field(default=None, description="周期", json_schema_extra={"q": "eq"})
    assign_mode: str | None = Field(default=None, description="分配方式", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="任务状态", json_schema_extra={"q": "eq"})


class CatalogUsageSchema(BaseModel):
    """任务目录的「已用」集合（任务目录页的「只看已用」过滤依据）。

    项目与任务单元的关系有两种指向：有三级任务的模板关联 ``item_id``，
    叶子模板（无三级任务）直接关联 ``template_id``，两者都要算作「已用」。
    """

    item_ids: list[int] = Field(default_factory=list, description="被项目引用的三级任务ID")
    template_ids: list[int] = Field(default_factory=list, description="被项目直接引用的叶子模板ID")


class TaskFacetSchema(BaseModel):
    """任务目录侧边栏的「已用目录」统计（只含有任务的分类/模板）。"""

    category_id: int = Field(description="一级分类ID")
    template_id: int = Field(description="二级模板ID")
    task_count: int = Field(description="该模板下的任务数")


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


class AssignmentBatchCreateSchema(BaseModel):
    """批量分配（多任务 × 多用户交叉创建分派，跳过已存在）"""

    task_ids: list[int] = Field(min_length=1, description="任务ID列表")
    user_ids: list[int] = Field(min_length=1, description="执行用户ID列表")


class TaskBatchPublishSchema(BaseModel):
    """批量发布任务参数（仅状态流转，不处理分派）"""

    ids: list[int] = Field(min_length=1, description="任务ID列表")


class TaskBatchPublishResultSchema(BaseModel):
    """批量发布结果"""

    published: int = Field(description="成功发布数量")
    failed: list[dict[str, Any]] = Field(default_factory=list, description="失败明细(含 id 与 msg)")


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


class SubmissionInstitutionBriefSchema(BaseModel):
    """成果所属机构摘要（审核页「机构」列/摘要用）"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="机构ID")
    name: str = Field(description="机构名称")
    type: str = Field(description="机构类型")
    region: str | None = Field(default=None, description="所在区域")


class SubmissionTaskContextSchema(BaseModel):
    """成果归属的任务上下文（项目 / 分类 / 模板 / 任务）。

    审核列表要把「这份成果是哪个项目下、哪个模板、哪个任务」一眼看重，而成果表只存
    ``assignment_id``，所以由服务层从 ``assignment.task`` 升维后**扁平**回填（避免多层嵌套）。
    """

    id: int = Field(description="任务实例ID")
    task_no: str = Field(description="任务编号(如 TK-0056)")
    name: str = Field(description="任务显示名(项目-模板-任务)")
    project_id: int = Field(description="所属项目ID")
    project_name: str = Field(description="所属项目名")
    category_id: int = Field(description="一级分类ID")
    category_name: str = Field(description="一级分类名")
    template_id: int = Field(description="二级模板ID")
    template_name: str = Field(description="二级模板名")
    item_id: int | None = Field(default=None, description="三级任务ID(叶子模板为空)")
    item_name: str | None = Field(default=None, description="三级任务名(叶子模板为空)")


class SubmissionOutSchema(BaseSchema, UserBySchema):
    """成果提交响应模型

    ``task`` / ``institution`` 在列表与详情都回填（审核需要任务上下文与采集对象）；
    ``form_schema`` 只在**详情类**接口回填（列表不需要字段标签，不做无谓开销）：
    - ``task``：项目/分类/模板/任务的扁平上下文，成果表只有 ``assignment_id``；
    - ``institution``：仅有 ``institution_id`` 时前端无法反查机构名称；
    - ``form_schema``：该任务自带的采集表单结构，是 ``form_data`` 英文 key → 中文标签的
      唯一映射源（后端 Pydantic 为权威定义，前端不重复维护字段名）。
    """

    model_config = ConfigDict(from_attributes=True)

    assignment_id: int = Field(description="分配ID")
    task: SubmissionTaskContextSchema | None = Field(default=None, description="任务上下文(项目/分类/模板/任务)")
    user_id: int = Field(description="提交用户ID")
    subject_type: str = Field(default="institution", description="采集对象类型(institution/staff/patient/meeting)")
    institution_id: int | None = Field(default=None, description="机构ID(对象为机构时)")
    institution: SubmissionInstitutionBriefSchema | None = Field(default=None, description="所属机构摘要(对象为机构时)")
    subject_name: str | None = Field(default=None, description="对象名称(机构对象=机构名称，个人对象=受访人)")
    region: str | None = Field(default=None, description="所在区域")
    archive_no: str | None = Field(default=None, description="档案编号(提交时自动生成 ARC-NNNN)")
    period: str = Field(description="提交月份(如 2026-03)")
    form_data: dict[str, Any] = Field(description="采集表单数据")
    form_schema: list[FormSchemaSection] | None = Field(
        default=None, description="采集表单结构(详情接口回填，供前端把字段名渲染成中文标签)"
    )
    status: str = Field(default="DRAFT", description="成果状态")
    version: int = Field(default=1, description="版本号(驳回重提 +1)")
    reviewer_id: int | None = Field(default=None, description="审核人ID")
    review_comment: str | None = Field(default=None, description="审核意见")
    reviewed_at: DateTimeStr | None = Field(default=None, description="审核时间")
    ai_check_status: str | None = Field(default=None, description="AI 预检状态")
    ai_check_result: dict[str, Any] | None = Field(default=None, description="AI 预检结果")


class SubmissionCreateSchema(BaseModel):
    """创建成果提交"""

    assignment_id: int = Field(gt=0, description="分配ID")
    subject_type: Literal["institution", "staff", "patient", "meeting"] = Field(default="institution", description="采集对象类型")
    institution_id: int | None = Field(default=None, gt=0, description="机构ID(对象为机构时)")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称(非机构对象时；机构对象由后端取机构名称)")
    region: str | None = Field(default=None, max_length=64, description="所在区域(缺省由后端从 form_data 提取)")
    archive_no: str | None = Field(
        default=None, max_length=64, description="档案编号(留空由后端自动生成 ARC-NNNN)"
    )
    period: str = Field(min_length=1, max_length=16, description="提交月份(如 2026-03)")
    form_data: dict[str, Any] = Field(description="采集表单数据")


class SubmissionUpdateSchema(BaseModel):
    """更新成果提交(草稿/驳回重提)"""

    subject_type: Literal["institution", "staff", "patient", "meeting"] | None = Field(default=None, description="采集对象类型")
    institution_id: int | None = Field(default=None, gt=0, description="机构ID")
    subject_name: str | None = Field(default=None, max_length=128, description="对象名称")
    region: str | None = Field(default=None, max_length=64, description="所在区域")
    archive_no: str | None = Field(default=None, max_length=64, description="档案编号")
    period: str | None = Field(default=None, min_length=1, max_length=16, description="提交月份")
    form_data: dict[str, Any] | None = Field(default=None, description="采集表单数据")


class SubmissionQueryParam(BaseQueryParam, UserByQueryParam):
    """成果提交查询参数

    ``project_id`` / ``template_id`` / ``item_id`` 不是成果表列，而是任务层级：服务层会把它们
    转成 ``assignment_id IN (SELECT id FROM market_assignment JOIN market_task ...)`` 子查询，
    因此**必须先从查询字典里摘出去**，否则 ``_build_conditions`` 会在模型上找不到对应列。
    """

    assignment_id: int | None = Field(default=None, description="分配ID", json_schema_extra={"q": "eq"})
    project_id: int | None = Field(default=None, description="项目ID(按任务所属项目过滤)")
    template_id: int | None = Field(default=None, description="任务模板ID(按任务所属模板过滤)")
    item_id: int | None = Field(default=None, description="任务ID(三级任务，按任务过滤)")
    user_id: int | None = Field(default=None, description="提交用户ID", json_schema_extra={"q": "eq"})
    subject_type: str | None = Field(default=None, description="采集对象类型", json_schema_extra={"q": "eq"})
    institution_id: int | None = Field(default=None, description="机构ID", json_schema_extra={"q": "eq"})
    archive_no: str | None = Field(default=None, description="档案编号", json_schema_extra={"q": "like"})
    period: str | None = Field(default=None, description="提交月份", json_schema_extra={"q": "eq"})
    status: str | None = Field(default=None, description="成果状态", json_schema_extra={"q": "eq"})
    ai_check_status: str | None = Field(default=None, description="AI 预检状态", json_schema_extra={"q": "eq"})


class SubmissionReviewSchema(BaseModel):
    """成果审核"""

    approved: bool = Field(description="是否通过")
    review_comment: str | None = Field(default=None, description="审核意见(驳回时建议填写)")


class SubmissionSettlementNoticeSchema(BaseModel):
    """审核通过触发的自动归集结果（只带前端提示需要的几个数）。

    ``payable`` 是**本任务本用户**该月的应发；``paid`` / ``rollover`` / ``limit`` 是
    **该用户当月整体**的实发、期末津贴与额度（发放封顶按「用户 × 周期」算，不是按单任务）。
    """

    task_id: int = Field(description="任务ID")
    period: str = Field(description="归集月份(如 2026-03)")
    payable: Decimal = Field(description="本任务本用户当月应发")
    paid: Decimal = Field(description="该用户当月实发(受额度封顶)")
    rollover: Decimal = Field(description="该用户当月期末津贴(滚入下月)")
    limit: Decimal = Field(description="该用户当月发放额度")


class SubmissionReviewResultSchema(BaseModel):
    """成果审核结果：审核后的成果 + 自动归集结果。

    归集是 best-effort：审核已经生效是事实，归集失败不回滚审核结果，而是把原因放在
    ``warning`` 里让前端原样提示运营（可稍后手动补跑归集）。
    """

    submission: SubmissionOutSchema = Field(description="审核后的成果")
    settlement: SubmissionSettlementNoticeSchema | None = Field(default=None, description="自动归集结果(驳回时为空)")
    warning: str | None = Field(default=None, description="审核已生效但归集失败的提示(成功时为空)")
