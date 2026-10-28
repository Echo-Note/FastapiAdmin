import { request } from "@utils";

const API_PATH = "/market/payout";

const PayoutAPI = {
  /** 发放额度配置分页 */
  listPayout(query?: PayoutConfigPageQuery) {
    return request<ApiResponse<PageResult<PayoutConfigTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  /** 发放额度配置详情 */
  detailPayout(id: number) {
    return request<ApiResponse<PayoutConfigTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  /** 创建发放额度配置（user_id + period 唯一） */
  createPayout(body: PayoutConfigForm) {
    return request<ApiResponse<PayoutConfigTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  /** 更新发放额度配置 */
  updatePayout(id: number, body: PayoutConfigUpdateForm) {
    return request<ApiResponse<PayoutConfigTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  /** 删除发放额度配置 */
  deletePayout(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  /** 津贴账户分页 */
  listAllowance(query?: PageQuery) {
    return request<ApiResponse<PageResult<AllowanceTable>>>({
      url: `${API_PATH}/allowance`,
      method: "get",
      params: query,
    });
  },

  /** 津贴明细分页（可按 user_id 过滤） */
  listAllowanceDetail(query?: AllowanceDetailPageQuery) {
    return request<ApiResponse<PageResult<AllowanceDetailTable>>>({
      url: `${API_PATH}/allowance/detail`,
      method: "get",
      params: query,
    });
  },
};

export default PayoutAPI;

export interface PayoutConfigPageQuery extends PageQuery, UserByQueryParams {
  user_id?: number;
  period?: string;
  enabled?: boolean;
}

export interface PayoutConfigTable extends BaseType {
  user_id?: number;
  period?: string;
  payout_limit?: number;
  enabled?: boolean;
}

export interface PayoutConfigForm {
  user_id: number;
  period: string;
  payout_limit: number;
  enabled: boolean;
}

export interface PayoutConfigUpdateForm {
  payout_limit?: number;
  enabled?: boolean;
}

export interface AllowanceTable extends BaseType {
  user_id?: number;
  balance?: number;
}

export interface AllowanceDetailPageQuery extends PageQuery {
  user_id?: number;
}

export interface AllowanceDetailTable extends BaseType {
  user_id?: number;
  from_period?: string;
  amount?: number;
  status?: string;
  paid_at?: string | null;
}
