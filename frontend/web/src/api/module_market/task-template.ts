import { request } from "@utils";
import type { FormSchema } from "./form-schema";

const API_PATH = "/market/templates";

const TaskTemplateAPI = {
  listTemplate(query?: TaskTemplatePageQuery) {
    return request<ApiResponse<PageResult<TaskTemplateTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailTemplate(id: number) {
    return request<ApiResponse<TaskTemplateTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createTemplate(body: TaskTemplateForm) {
    return request<ApiResponse<TaskTemplateTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateTemplate(id: number, body: TaskTemplateForm) {
    return request<ApiResponse<TaskTemplateTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteTemplate(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default TaskTemplateAPI;

export interface TaskTemplatePageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
  category_id?: number;
  enabled?: boolean;
}

/** 任务设计配置（与后端 app/modules/market/config.py 的 TaskConfig 对齐） */
export interface TaskConfig {
  subject_type?: string;
  unit?: string;
  pricing_mode?: string;
  price?: number | null;
  exec_standard?: string | null;
  executor_requirement?: string | null;
  report_required?: boolean;
  form_schema?: FormSchema;
}

export interface TaskTemplateTable extends BaseType {
  code?: string;
  name?: string;
  category_id?: number;
  category?: { id?: number; name?: string } | null;
  config?: TaskConfig | null;
  enabled?: boolean;
}

export interface TaskTemplateForm extends BaseFormType {
  name?: string;
  category_id?: number;
  config?: TaskConfig;
  enabled?: boolean;
}
