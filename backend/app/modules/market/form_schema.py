"""动态表单结构（form_schema）的权威定义。

后端 Pydantic 模型是 ``form_schema`` 结构的唯一定义源，前端 TS 类型只对齐、不做定义源。
``FormSchemaField`` 同时被 ``task`` 与 ``template`` 模块复用，故抽出到独立模块避免循环导入。
"""

from typing import Literal

from pydantic import BaseModel, Field


class FormSchemaOption(BaseModel):
    """采集字段选项（select/radio/checkbox 的可选项）。"""

    label: str = Field(description="选项显示名")
    value: str = Field(description="选项值")


class FormSchemaField(BaseModel):
    """采集字段定义（驱动小程序端「提交成果」动态表单）。

    每个字段对应表单上的一个输入项，支持三种承载形态：
    - 键值对字段  name + label + type（text/textarea/number/date/select/radio/checkbox/image/file）
    - 分节标题    type=section，仅作分组标题（name 可为空）
    - 多行子表    type=table，columns 为子列定义（如配送协调/进销存/票款往来明细）
    图片用 image（如打卡照片、机构内/外部照片），文件附件用 file（如合同、入库单、宣传资料）。
    """

    name: str | None = Field(default=None, max_length=64, description="字段唯一标识(建议英文/拼音，如 hospital_name；type=section 时可为空)")
    label: str = Field(min_length=1, max_length=128, description="字段显示名(如 医院名称；type=section 时为分节标题)")
    type: Literal["text", "textarea", "number", "date", "select", "radio", "checkbox", "image", "file", "table", "section"] = Field(default="text", description="字段类型")
    section: str | None = Field(default=None, max_length=128, description="所属分节标题(如 一、执行信息)")
    required: bool = Field(default=False, description="是否必填")
    placeholder: str | None = Field(default=None, max_length=255, description="输入占位提示")
    options: list[FormSchemaOption] | None = Field(default=None, description="选项列表(仅 select/radio/checkbox 需要)")
    columns: list["FormSchemaField"] | None = Field(default=None, description="多行子表列定义(仅 type=table 需要)")


# 自引用模型：columns 引用自身，需显式重建以解析前向引用
FormSchemaField.model_rebuild()
