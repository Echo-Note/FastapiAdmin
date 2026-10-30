"""市场管理域 —— 状态与类型枚举。

统一定义任务、分派、成果、结算单、报告、限额各实体的状态机取值，
以及机构类型枚举，供模型与序列化器共享，避免魔法字符串分散在代码各处。

取值与设计文档《03-流程与状态流转.md》的状态机保持一致（大写字符串）。
"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """任务状态机：草稿 → 发布 → 进行中 → 已完成(运营判定) → 归集中 → 已结算 → 归档。"""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    ARCHIVED = "ARCHIVED"


class SubjectType(StrEnum):
    """采集对象类型（成果提交针对的对象）。"""

    INSTITUTION = "institution"  # 机构（医院/药店/商业公司）
    STAFF = "staff"  # 医务人员/店员
    PATIENT = "patient"  # 患者/非医务人员
    MEETING = "meeting"  # 会议


class PricingMode(StrEnum):
    """计价方式：固定单价 / 按票据实际结算。"""

    FIXED = "fixed"  # 固定单价（元/月/家、元/份、元/次）
    ACTUAL = "actual"  # 按票据实际结算（如会议服务）


class SubmitCadence(StrEnum):
    """提交节奏（周期内 C 端重复提交成果的节奏）。"""

    MONTHLY = "monthly"  # 每月提交（机构管理/调研/宣传）
    ONCE = "once"  # 单次提交
    UNLIMITED = "unlimited"  # 不限（会议服务）


class AssignmentStatus(StrEnum):
    """分派/接收状态机：待接收 → 已接收 → 进行中 → 已提交 → 已审核 → 已结算。"""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
    SETTLED = "SETTLED"


class SubmissionStatus(StrEnum):
    """成果状态机：草稿 → 待审核 → 通过 / 驳回（驳回可修改重提，版本 +1）。"""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SettlementStatus(StrEnum):
    """结算单状态机：待结算 → 已计算 → 已确认 → 已入报告 → 已支付（二期）。"""

    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    PAID = "PAID"


class ReportStatus(StrEnum):
    """报告状态机：草稿 → 已生成 → 已提交。"""

    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    SUBMITTED = "SUBMITTED"


class AllowanceStatus(StrEnum):
    """个人任务津贴明细状态：待发（未发放，滚入下月）→ 已发（被下月发放消费）。"""

    PENDING = "PENDING"
    PAID = "PAID"


class ProjectStatus(StrEnum):
    """项目状态机：草稿 → 进行中 → 已完成 → 已关闭。"""

    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class InstitutionType(StrEnum):
    """机构类型（采集/提交对象）。"""

    GRADE_HOSPITAL = "grade_hospital"  # 等级医院
    PRIMARY_CARE = "primary_care"  # 基层医疗
    PRIVATE_MEDICAL = "private_medical"  # 民营医疗
    RETAIL_PHARMACY = "retail_pharmacy"  # 零售药店
    COMMERCIAL = "commercial"  # 商业公司


class AssignMode(StrEnum):
    """任务分配方式：定向分派 / 公开大厅。"""

    DIRECT = "direct"  # 定向分派（运营指定用户）
    OPEN = "open"  # 公开大厅（用户自行接单）


class AssignmentSource(StrEnum):
    """任务实例来源：运营分派 / 大厅接单。"""

    ASSIGNED = "assigned"  # 运营定向分派生成
    CLAIMED = "claimed"  # 用户大厅接单生成


class ProductSource(StrEnum):
    """产品库记录来源：运营录入 / C 端提交自动入库。"""

    ADMIN = "admin"  # 运营在后台录入或修正
    USER = "user"  # C 端提交成果时自动入库


class ProductAuditStatus(StrEnum):
    """产品库审核状态机：待审核 → 通过 / 驳回（驳回不删除，保留追溯）。"""

    PENDING = "pending"  # 待审核（仅提交人自己可检索）
    APPROVED = "approved"  # 已通过（所有 C 端用户可检索）
    REJECTED = "rejected"  # 已驳回（不参与检索）
