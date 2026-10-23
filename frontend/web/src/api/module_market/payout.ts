import { request } from "@utils";

const API_PATH = "/market/payout";

const PayoutAPI = {
  listPayout(query?: PayoutPageQuery) {
    return request<ApiResponse<PageResult<PayoutConfigTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  /** 创建或更新每月发放额度（按 user_id + period upsert） */
  savePayout(body: { user_id: number; period: string; payout_limit: number; enabled?: boolean }) {
    return request<ApiResponse<PayoutConfigTable>>({
      url: `${API_PATH}/save`,
      method: "post",
      data: body,
    });
  },

  /** 查询某用户某周期发放情况（发放额度 + 津贴余额 + 津贴明细） */
  usagePayout(query: { user_id: number; period: string }) {
    return request<ApiResponse<PayoutUsageDetail>>({
      url: `${API_PATH}/usage`,
      method: "get",
      params: query,
    });
  },
};

export default PayoutAPI;

export interface PayoutPageQuery extends PageQuery {
  user_id?: number;
  period?: string;
}

export interface PayoutConfigTable extends BaseType {
  user_id?: number;
  period?: string;
  payout_limit?: number;
  enabled?: boolean;
}

export interface PayoutUsageDetail {
  user_id?: number;
  period?: string;
  payout_limit?: number;
  allowance_balance?: number;
  allowance_items?: {
    id?: number;
    user_id?: number;
    from_period?: string;
    amount?: number;
    status?: string;
  }[];
}
