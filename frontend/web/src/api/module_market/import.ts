import { request } from "@utils";

const API_PATH = "/market/import";

/** 成果导入结果统计（对应后端 ImportResultSchema） */
export interface ImportResult {
  company_created: number;
  user_created: number;
  task_created: number;
  assignment_created: number;
  settlement_created: number;
  report_created: number;
  report_attachment_linked: number;
  errors: string[];
  warnings: string[];
}

const ImportAPI = {
  /** 导入结算单（对内/对外自动识别，支持多文件，周期 period 为结算周期） */
  importSettlement(files: File[], period: string) {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return request<ApiResponse<ImportResult>>({
      url: `${API_PATH}/settlement`,
      method: "post",
      params: { period },
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** 关联报告附件（pptx，按服务项目号 + 周期定位报告） */
  linkReport(file: File, serviceNo: number, period: string) {
    const formData = new FormData();
    formData.append("file", file);
    return request<ApiResponse<null>>({
      url: `${API_PATH}/report`,
      method: "post",
      params: { service_no: serviceNo, period },
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export default ImportAPI;
