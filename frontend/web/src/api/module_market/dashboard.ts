import { request } from "@utils";

const API_PATH = "/market/dashboard";

const DashboardAPI = {
  /** 运营工作台概览统计 */
  getOverview() {
    return request<ApiResponse<DashboardOverview>>({
      url: `${API_PATH}/overview`,
      method: "get",
    });
  },
  /** 运营工作台明细：近 14 天成果提交趋势 + 待审核队列 */
  getInsights() {
    return request<ApiResponse<DashboardInsights>>({
      url: `${API_PATH}/insights`,
      method: "get",
    });
  },
};

export default DashboardAPI;

/** 任务统计 */
export interface TaskStat {
  total: number;
  in_progress: number;
  completed: number;
  settled: number;
}

/** 成果统计 */
export interface SubmissionStat {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

/** 结算统计 */
export interface SettlementStat {
  total: number;
  payable_amount: number;
}

/** 运营工作台概览 */
export interface DashboardOverview {
  task: TaskStat;
  submission: SubmissionStat;
  settlement: SettlementStat;
  project_count: number;
  company_count: number;
  institution_count: number;
  category_count: number;
  template_count: number;
}

/** 成果提交量趋势点（一天一桶，日期为北京时间日历日） */
export interface SubmissionTrendPoint {
  /** 2026-10-17 */
  date: string;
  pending: number;
  approved: number;
  rejected: number;
}

/** 待审核成果队列行（首页只拿判断所需的四个字段） */
export interface PendingSubmissionRow {
  id: number;
  /** 采集对象：机构名 → 对象名 → 未填写对象 */
  subject: string;
  task_name: string;
  period: string;
  /** ISO8601，带 +08:00 */
  created_at: string;
}

/** 运营工作台明细 */
export interface DashboardInsights {
  /** 固定 14 点，由旧到新 */
  submission_trend: SubmissionTrendPoint[];
  /** 最新待审核成果，最多 8 条 */
  pending_submissions: PendingSubmissionRow[];
}
