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
};

export default SettlementAPI;

export interface SettlementPageQuery extends PageQuery, UserByQueryParams {
  task_id?: number;
  user_id?: number;
  status?: string;
}

export interface SettlementItemRow {
  settlement_id?: number;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  price?: number;
  qty?: number;
  amount?: number;
}

export interface SettlementTable extends BaseType {
  task_id?: number;
  user_id?: number;
  qty?: number;
  payable_amount?: number;
  paid_amount?: number | null;
  pay_status?: string | null;
  status?: string;
  items?: SettlementItemRow[];
}
