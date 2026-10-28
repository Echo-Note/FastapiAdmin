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
