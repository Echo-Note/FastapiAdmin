import { request } from "@utils";

const API_PATH = "/market/quota";

const QuotaAPI = {
  listQuota(query?: QuotaPageQuery) {
    return request<ApiResponse<PageResult<QuotaConfigTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  /** 创建或更新限额配置（按 user_id + period upsert） */
  saveQuota(body: { user_id: number; period: string; quota_amount: number; enabled: boolean }) {
    return request<ApiResponse<QuotaConfigTable>>({
      url: `${API_PATH}/save`,
      method: "post",
      data: body,
    });
  },

  usageQuota(query: { user_id: number; period: string }) {
    return request<ApiResponse<QuotaUsageDetail>>({
      url: `${API_PATH}/usage`,
      method: "get",
      params: query,
    });
  },
};

export default QuotaAPI;

export interface QuotaPageQuery extends PageQuery {
  user_id?: number;
  period?: string;
}

export interface QuotaConfigTable extends BaseType {
  user_id?: number;
  period?: string;
  quota_amount?: number;
  enabled?: boolean;
}

export interface QuotaUsageDetail {
  user_id?: number;
  period?: string;
  quota_amount?: number | null;
  received_amount?: number;
  payable_amount?: number;
  over_amount?: number;
  carryover_items?: {
    id?: number;
    from_period?: string;
    to_period?: string;
    amount?: number;
    status?: string;
  }[];
}
