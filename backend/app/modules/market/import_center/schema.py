"""成果导入 —— 请求/响应模型。"""

from pydantic import BaseModel, Field


class ImportResultSchema(BaseModel):
    """成果导入结果统计。

    按实体维度汇总本轮导入的新增数量，errors 记录被跳过的行级错误（不阻断整体导入）。
    """

    company_created: int = Field(default=0, description="新增医药公司数")
    user_created: int = Field(default=0, description="新增 C 端用户数")
    task_created: int = Field(default=0, description="新增任务数")
    assignment_created: int = Field(default=0, description="新增分派数")
    settlement_created: int = Field(default=0, description="新增结算单数")
    report_created: int = Field(default=0, description="新增报告数")
    report_attachment_linked: int = Field(default=0, description="已关联报告附件数")
    errors: list[str] = Field(default_factory=list, description="跳过/错误信息列表")
    warnings: list[str] = Field(default_factory=list, description="需人工确认的告警信息列表（如同名冲突）")
