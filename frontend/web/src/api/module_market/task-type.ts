import { request } from "@utils";

const API_PATH = "/market/task-types";

const TaskTypeAPI = {
  listTaskType(query?: TaskTypePageQuery) {
    return request<ApiResponse<PageResult<TaskTypeTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailTaskType(id: number) {
    return request<ApiResponse<TaskTypeTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createTaskType(body: TaskTypeForm) {
    return request<ApiResponse<TaskTypeTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateTaskType(id: number, body: TaskTypeForm) {
    return request<ApiResponse<TaskTypeTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteTaskType(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default TaskTypeAPI;

export interface TaskTypePageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
}

export interface TaskTypeTable extends BaseType {
  code?: string;
  name?: string;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  exec_standard?: string;
  required?: boolean;
  form_schema?: Record<string, unknown>[];
}

export interface TaskTypeForm extends BaseFormType {
  code?: string;
  name?: string;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  exec_standard?: string;
  required?: boolean;
  form_schema?: Record<string, unknown>[];
}
