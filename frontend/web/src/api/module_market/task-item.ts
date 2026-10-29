import { request } from "@utils";
import type { FormSchema } from "./form-schema";

const API_PATH = "/market/items";

const TaskItemAPI = {
  listItem(query?: TaskItemPageQuery) {
    return request<ApiResponse<PageResult<TaskItemTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailItem(id: number) {
    return request<ApiResponse<TaskItemTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createItem(body: TaskItemForm) {
    return request<ApiResponse<TaskItemTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateItem(id: number, body: TaskItemForm) {
    return request<ApiResponse<TaskItemTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteItem(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default TaskItemAPI;

export interface TaskItemPageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
  template_id?: number;
  enabled?: boolean;
}

/** 三级任务设计配置（与后端 app/modules/market/config.py 的 TaskItemConfig 对齐） */
export interface TaskItemConfig {
  form_schema?: FormSchema;
  unit?: string | null;
  price?: number | null;
  exec_standard?: string | null;
  executor_requirement?: string | null;
  max_per_month?: number | null;
}

export interface TaskItemTable extends BaseType {
  code?: string;
  name?: string;
  template_id?: number;
  config?: TaskItemConfig | null;
  sort?: number;
  enabled?: boolean;
}

export interface TaskItemForm extends BaseFormType {
  name?: string;
  template_id?: number;
  config?: TaskItemConfig;
  sort?: number;
  enabled?: boolean;
}
