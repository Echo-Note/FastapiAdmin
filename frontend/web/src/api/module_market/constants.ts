/**
 * market 域通用枚举标签映射（与后端 app/modules/market/enums.py 保持一致）。
 *
 * 供各实体页面的搜索下拉、表格状态列、详情展示复用，避免魔法字符串与重复映射。
 */

/** 任务状态机 */
export const TASK_STATUS_MAP: Record<string, { type: "primary" | "success" | "warning" | "info" | "danger"; text: string }> = {
  DRAFT: { type: "info", text: "草稿" },
  PUBLISHED: { type: "primary", text: "已发布" },
  IN_PROGRESS: { type: "warning", text: "进行中" },
  DEADLINE: { type: "danger", text: "已截止" },
  SETTLING: { type: "warning", text: "归集中" },
  SETTLED: { type: "success", text: "已结算" },
  ARCHIVED: { type: "info", text: "已归档" },
};

/** 分派/接收状态机 */
export const ASSIGNMENT_STATUS_MAP: Record<string, { type: "primary" | "success" | "warning" | "info" | "danger"; text: string }> = {
  PENDING: { type: "info", text: "待接收" },
  ACCEPTED: { type: "primary", text: "已接收" },
  SUBMITTING: { type: "warning", text: "进行中" },
  SUBMITTED: { type: "warning", text: "已提交" },
  REVIEWED: { type: "success", text: "已审核" },
  SETTLED: { type: "success", text: "已结算" },
};

/** 成果状态机 */
export const SUBMISSION_STATUS_MAP: Record<string, { type: "primary" | "success" | "warning" | "info" | "danger"; text: string }> = {
  DRAFT: { type: "info", text: "草稿" },
  PENDING: { type: "warning", text: "待审核" },
  APPROVED: { type: "success", text: "已通过" },
  REJECTED: { type: "danger", text: "已驳回" },
};

/** 结算单状态机 */
export const SETTLEMENT_STATUS_MAP: Record<string, { type: "primary" | "success" | "warning" | "info" | "danger"; text: string }> = {
  PENDING: { type: "info", text: "待结算" },
  CALCULATED: { type: "warning", text: "已计算" },
  CONFIRMED: { type: "primary", text: "已确认" },
  REPORTED: { type: "success", text: "已入报告" },
  PAID: { type: "success", text: "已支付" },
};

/** 报告状态机 */
export const REPORT_STATUS_MAP: Record<string, { type: "primary" | "success" | "info"; text: string }> = {
  DRAFT: { type: "info", text: "草稿" },
  GENERATED: { type: "primary", text: "已生成" },
  SUBMITTED: { type: "success", text: "已提交" },
};

/** 机构类型（tag 风格映射，供表格标签列与详情 tag 复用） */
export const INSTITUTION_TYPE_MAP: Record<string, { type: "primary" | "success" | "warning" | "info" | "danger"; text: string }> = {
  grade_hospital: { type: "primary", text: "等级医院" },
  primary_care: { type: "success", text: "基层医疗" },
  private_medical: { type: "warning", text: "民营医疗" },
  retail_pharmacy: { type: "info", text: "零售药店" },
  commercial: { type: "danger", text: "商业公司" },
};

/** 机构类型下拉选项 */
export const INSTITUTION_TYPE_OPTIONS: { label: string; value: string }[] = Object.entries(
  INSTITUTION_TYPE_MAP,
).map(([value, v]) => ({ value, label: v.text }));

/** 通用启用状态（company / institution 的 status 字段） */
export const ENABLE_STATUS_OPTIONS = [
  { label: "启用", value: 0 },
  { label: "停用", value: 1 },
] as const;

export const ENABLE_STATUS_MAP: Record<number, { type: "success" | "danger"; text: string }> = {
  0: { type: "success", text: "启用" },
  1: { type: "danger", text: "停用" },
};
