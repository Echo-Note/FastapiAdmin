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

  /** 生成月度报告（运营手动触发） */
  generateReport(body: { project_id: number; template_id?: number; period: string }) {
    return request<ApiResponse<ReportTable>>({
      url: `${API_PATH}/generate`,
      method: "post",
      data: body,
    });
  },
};

export default ReportAPI;

export interface ReportPageQuery extends PageQuery, UserByQueryParams {
  project_id?: number;
  template_id?: number;
  period?: string;
  status?: string;
}

export interface ReportTable extends BaseType {
  project_id?: number;
  project?: { id?: number; name?: string } | null;
  template_id?: number | null;
  template?: { id?: number; name?: string } | null;
  period?: string;
  summary?: Record<string, unknown>;
  attachment?: string | null;
  status?: string;
}
