"""任务设计配置（JSONB 宿主）的权威定义。

二级任务模板（TaskTemplateModel.config，用 ``TaskConfig``）承载「计价 + 执行标准 + 提交规则」；
仅无三级任务的叶子模板另承载「采集字段（form_schema，有序分节列表）」。
三级任务（TaskItemModel.config，用 ``TaskItemConfig``）承载
「任务自包含的完整采集分节（form_schema，有序分节列表）+ 可覆盖的单位/单价/执行标准/执行人员要求/频次上限」。

采集分节（如「执行信息」「管理核实」）是任务自身字段，不是模板「通用节点」：
凡有三级任务的模板不承载 form_schema，表单结构完全由三级任务自包含。

``TaskConfig`` 引用 ``FormSchemaSection`` / ``FormSchemaField``（见 ``form_schema.py``）。
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.market.form_schema import FormSchemaSection


class SubmitRule(BaseModel):
    """提交规则：控制周期内 C 端用户重复提交成果的节奏与去重。"""

    cadence: Literal["monthly", "once", "unlimited"] = Field(default="monthly", description="提交节奏(monthly 每月/once 单次/unlimited 不限)")
    max_per_day: int | None = Field(default=None, ge=1, description="单日上限(如 单人/单日 ≤2 家)")
    dedup: str | None = Field(default=None, max_length=255, description="去重约束(如 单月/单家 ≤1 次)")


class TaskConfig(BaseModel):
    """二级任务设计配置（JSONB 宿主）。"""

    subject_type: Literal["institution", "staff", "patient", "meeting"] = Field(description="采集对象类型")
    unit: str = Field(min_length=1, max_length=32, description="计价单位(元/月/家、元/家/次、元/份、元/次)")
    pricing_mode: Literal["fixed", "actual"] = Field(default="fixed", description="计价方式(fixed 固定单价/actual 按票据)")
    price: Decimal | None = Field(default=None, ge=0, description="固定单价(pricing_mode=fixed 时必填)")
    exec_standard: str | None = Field(default=None, description="执行标准(多行)")
    executor_requirement: str | None = Field(default=None, max_length=128, description="默认执行人员要求(如 临床协调员)")
    submit_rule: SubmitRule = Field(default_factory=SubmitRule, description="提交规则")
    form_schema: list[FormSchemaSection] = Field(default_factory=list, description="采集字段(有序分节列表，仅无三级任务的叶子模板使用)")
    report_required: bool = Field(default=True, description="是否需月度报告")


class TaskItemConfig(BaseModel):
    """三级任务设计配置（JSONB 宿主）。

    任务承载「专属采集字段（form_schema，有序分节列表）」及可覆盖模板级的计价/执行口径。
    采集字段与二级模板（``TaskConfig.form_schema``）同构，均为 ``list[FormSchemaSection]``：
    每个分节含稳定英文 ``code`` + 中文 ``name`` + 其下字段，字段支持单值形态与
    ``type=table`` 多行子表（多行明细列），支持在添加/编辑/详情展示时按分节分别添加与展示。
    """

    form_schema: list[FormSchemaSection] = Field(default_factory=list, description="任务采集字段(有序分节列表)")
    unit: str | None = Field(default=None, max_length=32, description="计价单位(覆盖模板级)")
    price: Decimal | None = Field(default=None, ge=0, description="单价(覆盖模板级)")
    exec_standard: str | None = Field(default=None, description="执行标准(覆盖模板级)")
    executor_requirement: str | None = Field(default=None, max_length=128, description="执行人员要求(覆盖模板级)")
    max_per_month: int | None = Field(default=None, ge=1, description="单月频次上限(覆盖模板级)")


__all__ = ["TaskConfig", "TaskItemConfig", "SubmitRule"]
