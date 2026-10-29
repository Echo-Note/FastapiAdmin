import { request } from "@utils";
import type { FormSchema } from "./form-schema";

const API_PATH = "/market/tasks";

const TaskAPI = {
  listTask(query?: TaskPageQuery) {
    return request<ApiResponse<PageResult<TaskTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailTask(id: number) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createTask(body: TaskForm) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateTask(id: number, body: TaskForm) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteTask(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  /** 发布任务（DRAFT → PUBLISHED；定向分派须传 assignee_ids 指定分派人员） */
  publishTask(id: number, body: { assignee_ids?: number[] } = {}) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/publish/${id}`,
      method: "post",
      data: body,
    });
  },

  /** 单向流转任务状态（PUBLISHED→IN_PROGRESS→COMPLETED→SETTLED→ARCHIVED） */
  changeStatusTask(id: number, body: { status: string }) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/status/${id}`,
      method: "post",
      data: body,
    });
  },
};

export default TaskAPI;

export interface TaskPageQuery extends PageQuery, UserByQueryParams {
  task_no?: string;
  project_id?: number;
  template_id?: number;
  period?: string;
  assign_mode?: string;
  status?: string;
}

/** 二级任务模板（嵌套在任务响应中） */
export interface TaskTemplateBrief {
  id?: number;
  code?: string;
  name?: string;
  config?: TaskConfig | null;
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

export interface TaskTable extends BaseType {
  task_no?: string;
  project_id?: number;
  template_id?: number;
  template?: TaskTemplateBrief | null;
  name?: string;
  period?: string;
  assign_mode?: string;
  status?: string;
  publisher_id?: number | null;
  published_at?: string | null;
}

export interface TaskForm extends BaseFormType {
  project_id?: number;
  template_id?: number;
  name?: string;
  period?: string;
  assign_mode?: string;
  status?: string;
}
