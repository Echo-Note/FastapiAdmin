import { request } from "@utils";
import type { MarketUserBrief } from "./settlement";

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

  /** 发放结果分页：按 用户 × 周期 聚合的 应发/期初津贴/额度/实发/滚存 */
  listPayoutResult(query?: PayoutResultPageQuery) {
    return request<ApiResponse<PageResult<PayoutResultTable>>>({
      url: `${API_PATH}/results`,
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

export interface PayoutResultPageQuery extends PageQuery {
  user_id?: number;
  period?: string;
}

/** 发放结果（对齐后端 PayoutResultOutSchema）：口径是「用户 × 周期」，不是单条结算单 */
export interface PayoutResultTable {
  user_id?: number;
  /** C 端用户摘要：昵称/账号/手机号 */
  user?: MarketUserBrief | null;
  period?: string;
  /** 当月应发合计（跨任务） */
  payable?: number;
  /** 期初津贴余额（上期期末未发放额） */
  prev_balance?: number;
  /** 当月发放额度 */
  limit?: number;
  /** 当月实发（受额度封顶） */
  paid?: number;
  /** 期末津贴余额（滚入下月） */
  rollover?: number;
}
