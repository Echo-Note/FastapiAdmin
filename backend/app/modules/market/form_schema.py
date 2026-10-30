"""动态表单结构（form_schema）的权威定义。

``form_schema`` 为有序分节列表：``list[FormSchemaSection]``。
每个分节携带稳定的英文 ``code``（逻辑标识）+ 中文 ``name``（展示名）+ 必填标记
``required`` + 其下字段 ``fields``（``dict[字段名, FormSchemaField]``）。
分节标识与展示名分离、字段名与字段定义分离，二者都由独立字段表达，不再用中文名直接充当结构 key。

字段形态对齐真实采集表：单值字段（text/textarea/number/date/select/radio/checkbox/image/file）
+ ``type=table`` 多行子表（``columns`` 子列，如「价格核查」的产品明细列），可同分节混排。
+ ``type=region`` 全国省市区三级联动选择（如「区域」字段），前端内置行政区划数据渲染级联选择。

后端 Pydantic 模型是 ``form_schema`` 结构的唯一定义源，前端 TS 类型只对齐、不做定义源。
``FormSchemaField`` 同时被 ``task`` 与 ``template`` 模块复用，故抽出到独立模块避免循环导入。
"""

from typing import Literal

from pydantic import BaseModel, Field


class FormSchemaOption(BaseModel):
    """采集字段选项（select/radio/checkbox 的可选项）。"""

    label: str = Field(description="选项显示名")
    value: str = Field(description="选项值")


class FormSchemaColumn(BaseModel):
    """多行子表（``type=table``）的子列定义。

    真实采集表（如「价格核查」）中，分节内既有多行明细列（产品名称/规格/挂网价…），
    也有表后的单字段（异常说明）。多行明细以 ``type=table`` 字段表达，其列由本模型定义；
    子列类型不允许再嵌套 ``table``，防止无限递归。
    """

    name: str = Field(min_length=1, max_length=64, description="子列唯一标识(如 product_name)")
    label: str = Field(min_length=1, max_length=128, description="子列显示名(如 产品名称)")
    type: Literal["text", "textarea", "number", "date", "select", "radio", "checkbox", "image", "file"] = Field(
        default="text", description="子列类型(不允许 table，防嵌套)"
    )
    required: bool = Field(default=False, description="该列是否必填")
    placeholder: str | None = Field(default=None, max_length=255, description="输入占位提示")
    options: list[FormSchemaOption] | None = Field(default=None, description="选项列表(仅 select/radio/checkbox 需要)")


class FormSchemaField(BaseModel):
    """采集字段定义（字段名由外层 ``dict`` 的 key 表达）。

    每个字段对应表单上的一个输入项：
    - 单值字段：text/textarea/number/date/select/radio/checkbox/image/file，
      图片用 image（如打卡照片、机构内/外部照片），文件附件用 file（如合同、入库单、宣传资料）。
    - ``type=table``：多行子表，``columns`` 携带子列定义，行数据为 ``list[dict[子列名, 值]]``。
    - ``autofill=current_user``：字段由后端按当前登录用户自动填充并只读（如「执行人」），
      前端不渲染输入框，提交时由后端注入当前用户身份，不参与用户填写。
    二级模板（TaskConfig）与三级任务（TaskItemConfig）共用本定义，字段名与字段定义分离，
    统一在分节 ``fields`` 中以 ``dict[字段名, FormSchemaField]`` 表达。
    """

    label: str = Field(min_length=1, max_length=128, description="字段显示名(如 医院名称)")
    type: Literal["text", "textarea", "number", "date", "select", "radio", "checkbox", "image", "file", "table", "region"] = Field(
        default="text", description="字段类型(table 为多行子表；region 为省市区三级联动选择)"
    )
    required: bool = Field(default=False, description="是否必填")
    autofill: Literal["current_user"] | None = Field(
        default=None, description="自动填充来源(current_user=自动填当前登录用户并只读)"
    )
    placeholder: str | None = Field(default=None, max_length=255, description="输入占位提示")
    options: list[FormSchemaOption] | None = Field(default=None, description="选项列表(仅 select/radio/checkbox 需要)")
    columns: list[FormSchemaColumn] | None = Field(default=None, description="子表列定义(仅 type=table 需要)")


class FormSchemaSection(BaseModel):
    """采集表单分节：稳定的英文 code + 中文展示名 + 其下字段。"""

    code: str = Field(min_length=1, max_length=64, description="分节唯一标识(如 execution_info)")
    name: str = Field(min_length=1, max_length=128, description="分节显示名(如 执行信息)")
    required: bool = Field(default=False, description="分节是否必填(标题展示「(必填)」标记)")
    fields: dict[str, FormSchemaField] = Field(default_factory=dict, description="分节下字段(字段名 → 字段定义)")


# 采集表单结构：有序分节列表
FormSchema = list[FormSchemaSection]
