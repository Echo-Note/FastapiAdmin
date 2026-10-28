import { request } from "@utils";

const API_PATH = "/market/settlements";

const SettlementAPI = {
  listSettlement(query?: SettlementPageQuery) {
    return request<ApiResponse<PageResult<SettlementTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailSettlement(id: number) {
    return request<ApiResponse<SettlementTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  /** 归集结算：汇总 task × 周期下审核通过成果，生成结算单 */
  settle(body: { task_id: number; period: string }) {
    return request<ApiResponse<SettlementTable[]>>({
      url: `${API_PATH}/settle`,
      method: "post",
      data: body,
    });
  },

  /** 确认结算单 */
  confirmSettlement(id: number) {
    return request<ApiResponse<SettlementTable>>({
      url: `${API_PATH}/confirm/${id}`,
      method: "post",
      data: {},
    });
  },
};

export default SettlementAPI;

export interface SettlementPageQuery extends PageQuery, UserByQueryParams {
  task_id?: number;
  user_id?: number;
  period?: string;
  status?: string;
}

export interface SettlementItemRow {
  settlement_id?: number;
  category_name?: string;
  template_name?: string;
  unit?: string;
  price?: number;
  qty?: number;
  amount?: number;
}

export interface SettlementTable extends BaseType {
  task_id?: number;
  user_id?: number;
  period?: string;
  qty?: number;
  payable_amount?: number;
  paid_amount?: number | null;
  pay_status?: string | null;
  status?: string;
  items?: SettlementItemRow[];
}
