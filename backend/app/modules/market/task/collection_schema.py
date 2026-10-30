"""市场机构管理 5 类采集表的权威字段定义 —— ``form_schema`` 的生成源。

素材：``docs/materials/任务/玄狐&一心坦任务（示例）/1.市场机构管理/`` 下
等级医院管理 / 基层医疗管理 / 民营医疗管理 / 零售药店管理 / 商业公司管理
共 26 份 Excel 采集表。每份采集表 = 一个三级任务（``market_task_item``），
表结构统一为三段：

1. ``execution_info`` 执行信息：区域 + 该机构类型的专属字段 + 执行人（自动填充）+ 执行日期；
2. 工作区分节：多行子表（``type=table``）+ 表后的「异常说明」（部分工作区是「优势/劣势」或纯照片）；
3. ``management_verification`` 管理核实：机构门头照片。

**这不是运行时真相源**：运行时仍以库里 ``config.form_schema`` 为准。本模块只用于
(a) 生成 ``backend/sql/market_task_item.json`` 种子、(b) 订正已初始化库里的旧 schema，
两者都通过 ``app.scripts.apply_collection_schema`` 执行；测试断言种子与本模块逐字一致，
防止两份数据漂移。

字段名（``dict`` 的 key）一旦发布就代表已提交成果 ``form_data`` 的结构，改动等于打破旧数据，
因此退役语义的旧 key（如库存盘点的 ``stock_qty``=库存数量）不复用，新语义一律用新 key
（如 ``actual_qty``=实盘数量）。
"""

from app.modules.market.form_schema import FormSchema, FormSchemaColumn, FormSchemaField, FormSchemaOption, FormSchemaSection

# 三个固定分节的 code（与历史 form_data 的嵌套键保持一致，不可改）
EXECUTION_SECTION = "execution_info"
VERIFICATION_SECTION = "management_verification"

# 表后自由说明字段（「异常说明」）
EXCEPTION_FIELD = "exception_note"

# 产品库三要素的约定列名（产品库自动填充/自动入库按此识别，见 market/product/service.py）
PRODUCT_NAME_KEY = "product_name"
PRODUCT_SPEC_KEY = "product_spec"
PRODUCT_MANUFACTURER_KEY = "manufacturer"

# ---------------------------------------------------------------- 通用字段构造


def _options(*values: str) -> list[FormSchemaOption]:
    """把字符串列表转成 ``FormSchemaOption`` 列表（label 与 value 同值）。"""
    return [FormSchemaOption(label=v, value=v) for v in values]


def _region_field() -> FormSchemaField:
    return FormSchemaField(label="区域", type="region", required=True)


def _executor_field() -> FormSchemaField:
    return FormSchemaField(label="执行人", type="text", required=True, autofill="current_user")


def _exec_date_field() -> FormSchemaField:
    return FormSchemaField(label="执行日期", type="date", required=True)


def _exception_field() -> FormSchemaField:
    return FormSchemaField(label="异常说明", type="textarea", placeholder="无异常请填「无」")


# ---------------------------------------------------------------- 机构类型专属执行信息

# 机构类型 → 执行信息里「机构名称」及专属字段（顺序即渲染顺序）
_INSTITUTION_EXEC_FIELDS: dict[str, dict[str, FormSchemaField]] = {
    # 等级医院管理：医院名称 / 医院等级 / 医院性质
    "grade_hospital": {
        "hospital_name": FormSchemaField(label="医院名称", type="text", required=True),
        "hospital_level": FormSchemaField(
            label="医院等级",
            type="select",
            options=_options("三级甲等", "三级乙等", "二级甲等", "二级乙等", "一级", "未定级"),
        ),
        "hospital_nature": FormSchemaField(label="医院性质", type="select", options=_options("公立", "民营")),
    },
    # 基层医疗管理：医院名称 / 机构类型 / 上级管理主体
    "primary_care": {
        "hospital_name": FormSchemaField(label="医院名称", type="text", required=True),
        "org_type": FormSchemaField(label="机构类型", type="text", placeholder="如 事业单位/公益二类事业单位"),
        "supervisor": FormSchemaField(label="上级管理主体", type="text", placeholder="如 江北区卫生健康委员会"),
    },
    # 民营医疗管理：医院名称 / 单体·集团 / 所属集团
    "private_medical": {
        "hospital_name": FormSchemaField(label="医院名称", type="text", required=True),
        "entity_type": FormSchemaField(label="单体／集团", type="select", options=_options("单体", "集团")),
        "group_name": FormSchemaField(label="所属集团", type="text"),
    },
    # 零售药店管理：药店名称 / 连锁·单体 / 所属连锁总部
    "retail_pharmacy": {
        "org_name": FormSchemaField(label="药店名称", type="text", required=True),
        "chain_type": FormSchemaField(label="连锁／单体", type="select", options=_options("连锁", "单体")),
        "chain_headquarter": FormSchemaField(label="所属连锁总部", type="text"),
    },
    # 商业公司管理：商业公司名称
    "commercial": {
        "org_name": FormSchemaField(label="商业公司名称", type="text", required=True),
    },
}

# 机构类型 → 管理核实分节里的门头照片字段
_INSTITUTION_DOOR_PHOTO: dict[str, tuple[str, str]] = {
    "grade_hospital": ("door_photo", "医院门头照片"),
    "primary_care": ("door_photo", "医院门头照片"),
    "private_medical": ("door_photo", "医院门头照片"),
    "retail_pharmacy": ("door_photo", "药店门头照片"),
    "commercial": ("door_photo", "商业公司门头照片"),
}

# ---------------------------------------------------------------- 工作区（多行子表）列定义

# 产品三要素列：产品名称/规格/生产企业，带 product_role 供 C 端检索填充产品库
_PRODUCT_COLUMNS: list[FormSchemaColumn] = [
    FormSchemaColumn(name=PRODUCT_NAME_KEY, label="产品名称", type="text", required=True, product_role="name"),
    FormSchemaColumn(name=PRODUCT_SPEC_KEY, label="产品规格", type="text", product_role="spec"),
    FormSchemaColumn(name=PRODUCT_MANUFACTURER_KEY, label="生产企业", type="text", product_role="manufacturer"),
]

_BATCH_COLUMN = FormSchemaColumn(name="batch_no", label="批号", type="text")

_ACCEPTANCE_COLUMN = FormSchemaColumn(
    name="acceptance", label="验收情况", type="select", options=_options("验收入库", "部分入库", "拒收")
)


def _product_columns(spec_label: str = "产品规格") -> list[FormSchemaColumn]:
    """产品三要素列；``spec_label`` 兼容素材里「规格」与「产品规格」两种写法。"""
    cols = [col.model_copy(deep=True) for col in _PRODUCT_COLUMNS]
    cols[1].label = spec_label
    return cols


class WorkareaSpec:
    """一个工作区（采集表里的「二、xxx（必填）」分节）的定义。"""

    def __init__(
        self,
        code: str,
        name: str,
        columns: list[FormSchemaColumn] | None = None,
        *,
        image: tuple[str, str] | None = None,
        trailing: dict[str, FormSchemaField] | None = None,
        has_exception: bool = True,
    ) -> None:
        self.code = code
        self.name = name
        self.columns = columns or []
        self.image = image
        self.trailing = trailing or {}
        self.has_exception = has_exception

    def build(self) -> FormSchemaSection:
        """构造该工作区分节：多行子表（或照片字段）+ 表后字段。"""
        fields: dict[str, FormSchemaField] = {}
        if self.image:
            field_name, label = self.image
            fields[field_name] = FormSchemaField(label=label, type="image", required=True)
        else:
            fields[self.code] = FormSchemaField(
                label=self.name,
                type="table",
                required=True,
                columns=[col.model_copy(deep=True) for col in self.columns],
            )
        fields.update({k: v.model_copy(deep=True) for k, v in self.trailing.items()})
        if self.has_exception:
            fields[EXCEPTION_FIELD] = _exception_field()
        return FormSchemaSection(code=self.code, name=self.name, required=True, fields=fields)


WORKAREAS: dict[str, WorkareaSpec] = {
    "delivery_coordination": WorkareaSpec(
        "delivery_coordination",
        "配送协调",
        [
            *_product_columns(),
            _BATCH_COLUMN.model_copy(deep=True),
            FormSchemaColumn(name="qty", label="配送数量", type="number"),
            FormSchemaColumn(name="delivery_time", label="配送时间", type="date"),
            _ACCEPTANCE_COLUMN.model_copy(deep=True),
            FormSchemaColumn(name="distributor", label="配送商业", type="text"),
        ],
    ),
    "inventory_check": WorkareaSpec(
        "inventory_check",
        "库存盘点",
        [
            *_product_columns("规格"),
            _BATCH_COLUMN.model_copy(deep=True),
            FormSchemaColumn(name="expiry_date", label="有效期至", type="date"),
            FormSchemaColumn(name="actual_qty", label="实盘数量", type="number"),
            FormSchemaColumn(name="diff_qty", label="盘点差异", type="number"),
        ],
    ),
    "price_check": WorkareaSpec(
        "price_check",
        "价格核查",
        [
            *_product_columns("规格"),
            FormSchemaColumn(name="listed_price", label="挂网价", type="number"),
            FormSchemaColumn(name="purchase_price", label="采购价", type="number"),
            FormSchemaColumn(name="sale_price", label="销售价", type="number"),
        ],
    ),
    # 竞品调研：调研对象是**别人的产品**，故列名用 competitor_* 前缀，
    # 既不触发产品库自动填充，也不会把竞品写进产品库
    "competitor_research": WorkareaSpec(
        "competitor_research",
        "竞品调研",
        [
            FormSchemaColumn(name="competitor_name", label="产品名称", type="text", required=True),
            FormSchemaColumn(name="competitor_spec", label="规格", type="text"),
            FormSchemaColumn(name="competitor_manufacturer", label="生产企业", type="text"),
            FormSchemaColumn(name="brand", label="品牌", type="text"),
            FormSchemaColumn(name="price", label="价格", type="number"),
            FormSchemaColumn(name="sales_volume", label="销量", type="number"),
            FormSchemaColumn(name="department", label="科室", type="text"),
        ],
        trailing={
            "advantage": FormSchemaField(label="优势", type="textarea"),
            "disadvantage": FormSchemaField(label="劣势", type="textarea"),
        },
        has_exception=False,
    ),
    "sales_reconciliation": WorkareaSpec(
        "sales_reconciliation",
        "销售对账",
        [
            *_product_columns(),
            _BATCH_COLUMN.model_copy(deep=True),
            FormSchemaColumn(name="sales_qty", label="销售数量", type="number"),
            FormSchemaColumn(name="return_qty", label="退损数量", type="number"),
        ],
    ),
    "bidding_procurement": WorkareaSpec(
        "bidding_procurement",
        "招标采购",
        [
            *_product_columns(),
            FormSchemaColumn(name="bid_batch", label="招标批次", type="text"),
            FormSchemaColumn(name="bid_entity", label="招标主体", type="text"),
            FormSchemaColumn(name="bid_progress", label="项目进度", type="text"),
        ],
    ),
    # 陈列优化：素材里本工作区只有一个「陈列照片」，不是多行子表
    "display_optimization": WorkareaSpec(
        "display_optimization",
        "陈列优化",
        image=("display_photo", "陈列照片"),
    ),
}

# 商业公司管理的配送协调：末列是「终端机构」而不是「配送商业」
_COMMERCIAL_DELIVERY = WorkareaSpec(
    "delivery_coordination",
    "配送协调",
    [
        *_product_columns(),
        _BATCH_COLUMN.model_copy(deep=True),
        FormSchemaColumn(name="qty", label="配送数量", type="number"),
        FormSchemaColumn(name="delivery_time", label="配送时间", type="date"),
        _ACCEPTANCE_COLUMN.model_copy(deep=True),
        FormSchemaColumn(name="terminal_org", label="终端机构", type="text"),
    ],
)

# ---------------------------------------------------------------- 三级任务 → (机构类型, 工作区)

ITEM_DEFINITIONS: dict[str, tuple[str, str]] = {
    # 等级医院管理
    "ITEM-0001": ("grade_hospital", "delivery_coordination"),
    "ITEM-0002": ("grade_hospital", "inventory_check"),
    "ITEM-0003": ("grade_hospital", "price_check"),
    "ITEM-0004": ("grade_hospital", "competitor_research"),
    "ITEM-0005": ("grade_hospital", "sales_reconciliation"),
    # 基层医疗管理
    "ITEM-0006": ("primary_care", "delivery_coordination"),
    "ITEM-0007": ("primary_care", "inventory_check"),
    "ITEM-0008": ("primary_care", "price_check"),
    "ITEM-0009": ("primary_care", "competitor_research"),
    "ITEM-0010": ("primary_care", "sales_reconciliation"),
    # 民营医疗管理
    "ITEM-0011": ("private_medical", "delivery_coordination"),
    "ITEM-0012": ("private_medical", "inventory_check"),
    "ITEM-0013": ("private_medical", "price_check"),
    "ITEM-0014": ("private_medical", "competitor_research"),
    "ITEM-0015": ("private_medical", "sales_reconciliation"),
    # 零售药店管理
    "ITEM-0016": ("retail_pharmacy", "display_optimization"),
    "ITEM-0017": ("retail_pharmacy", "delivery_coordination"),
    "ITEM-0018": ("retail_pharmacy", "inventory_check"),
    "ITEM-0019": ("retail_pharmacy", "price_check"),
    "ITEM-0020": ("retail_pharmacy", "competitor_research"),
    "ITEM-0021": ("retail_pharmacy", "sales_reconciliation"),
    # 商业公司管理（进销存数据收集 / 流向数据收集在素材里没有采集表，不在此列）
    "ITEM-0022": ("commercial", "bidding_procurement"),
    "ITEM-0023": ("commercial", "delivery_coordination"),
    "ITEM-0024": ("commercial", "inventory_check"),
    "ITEM-0025": ("commercial", "price_check"),
    "ITEM-0026": ("commercial", "competitor_research"),
}

# 素材缺失采集表、本轮不对齐的三级任务（保持库里原样）
UNALIGNED_ITEM_CODES: tuple[str, ...] = ("ITEM-0027", "ITEM-0028")


def _workarea_for(institution: str, workarea: str) -> WorkareaSpec:
    """按机构类型取工作区定义（仅商业公司的配送协调有专属列）。"""
    if institution == "commercial" and workarea == "delivery_coordination":
        return _COMMERCIAL_DELIVERY
    return WORKAREAS[workarea]


def build_form_schema(item_code: str) -> FormSchema | None:
    """按三级任务编号构造完整 ``form_schema``（执行信息 → 工作区 → 管理核实）。

    :param item_code: 三级任务编号（如 ``ITEM-0011``）
    :return: 三段式采集表单结构；该编号不在对齐范围内时返回 None
    """
    definition = ITEM_DEFINITIONS.get(item_code)
    if definition is None:
        return None
    institution, workarea = definition

    execution_fields: dict[str, FormSchemaField] = {"region": _region_field()}
    execution_fields.update({k: v.model_copy(deep=True) for k, v in _INSTITUTION_EXEC_FIELDS[institution].items()})
    execution_fields["executor"] = _executor_field()
    execution_fields["exec_date"] = _exec_date_field()

    photo_name, photo_label = _INSTITUTION_DOOR_PHOTO[institution]

    return [
        FormSchemaSection(code=EXECUTION_SECTION, name="执行信息", required=True, fields=execution_fields),
        _workarea_for(institution, workarea).build(),
        FormSchemaSection(
            code=VERIFICATION_SECTION,
            name="管理核实",
            required=True,
            fields={photo_name: FormSchemaField(label=photo_label, type="image", required=True)},
        ),
    ]


# 三级任务编号 → form_schema（供种子生成与存量订正统一取用）
ITEM_FORM_SCHEMAS: dict[str, FormSchema] = {
    code: schema for code in ITEM_DEFINITIONS if (schema := build_form_schema(code)) is not None
}

__all__ = [
    "EXCEPTION_FIELD",
    "EXECUTION_SECTION",
    "ITEM_DEFINITIONS",
    "ITEM_FORM_SCHEMAS",
    "PRODUCT_MANUFACTURER_KEY",
    "PRODUCT_NAME_KEY",
    "PRODUCT_SPEC_KEY",
    "UNALIGNED_ITEM_CODES",
    "VERIFICATION_SECTION",
    "WORKAREAS",
    "build_form_schema",
]
