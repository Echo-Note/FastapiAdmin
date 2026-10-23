import { request } from "@utils";

const API_PATH = "/market/reports";

const ReportAPI = {
  listReport(query?: ReportPageQuery) {
    return request<ApiResponse<PageResult<ReportTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailReport(id: number) {
    return request<ApiResponse<ReportTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  generateReport(body: { company_id: number; period: string; service_item_id?: number; task_type_id?: number }) {
    return request<ApiResponse<ReportTable>>({
      url: `${API_PATH}/generate`,
      method: "post",
      data: body,
    });
  },
};

export default ReportAPI;

export interface ReportPageQuery extends PageQuery, UserByQueryParams {
  company_id?: number;
  service_item_id?: number;
  task_type_id?: number;
  period?: string;
  status?: string;
}

export interface ReportTable extends BaseType {
  company_id?: number;
  company?: { id?: number; name?: string } | null;
  service_item_id?: number | null;
  task_type_id?: number | null;
  period?: string;
  summary?: Record<string, unknown>;
  attachment?: string | null;
  status?: string;
}
