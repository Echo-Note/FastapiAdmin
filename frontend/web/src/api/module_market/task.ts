import { request } from "@utils";

import type { SettlementTable } from "./settlement";

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

  /** 发布任务（DRAFT → PUBLISHED） */
  publishTask(id: number) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/publish/${id}`,
      method: "post",
      data: {},
    });
  },

  /** 判定任务完成（运营手动） */
  completeTask(id: number) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/complete/${id}`,
      method: "post",
      data: {},
    });
  },

  /** 触发归集结算（需先判定完成） */
  settleTask(id: number) {
    return request<ApiResponse<SettlementTable[]>>({
      url: `${API_PATH}/settle/${id}`,
      method: "post",
      data: {},
    });
  },
};

export default TaskAPI;

export interface TaskPageQuery extends PageQuery, UserByQueryParams {
  task_no?: string;
  task_type_id?: number;
  task_kind?: string;
  period?: string;
  assign_mode?: string;
  status?: string;
}

/** 任务类型模板（嵌套在任务响应中） */
export interface TaskTypeBrief {
  id?: number;
  code?: string;
  name?: string;
  task_no?: number;
  template_id?: number;
  template?: { id?: number; code?: string; name?: string; form_schema?: Record<string, unknown>[] } | null;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  default_kind?: string;
  exec_standard?: string | null;
  required?: boolean;
  min_qty?: number | null;
  max_per_period?: number | null;
  dedup_rule?: string | null;
}

export interface TaskTable extends BaseType {
  task_no?: string;
  task_type_id?: number;
  task_type?: TaskTypeBrief | null;
  task_kind?: string;
  period?: string;
  exec_time_start?: string | null;
  exec_time_end?: string | null;
  unit_price?: number;
  exec_qty?: number;
  assign_mode?: string;
  claimed_count?: number;
  status?: string;
  completed_at?: string | null;
  publisher_id?: number | null;
  published_at?: string | null;
  /** 归集到的项目ID列表（多对多） */
  project_ids?: number[];
}

export interface TaskForm extends BaseFormType {
  task_no?: string;
  task_type_id?: number;
  task_kind?: string;
  period?: string;
  exec_time_start?: string | null;
  exec_time_end?: string | null;
  unit_price?: number;
  exec_qty?: number;
  assign_mode?: string;
  /** 归集到的项目 ID 列表（多对多） */
  project_ids?: number[];
}
