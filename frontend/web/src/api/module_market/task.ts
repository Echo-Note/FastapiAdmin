import { request } from "@utils";

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

  publishTask(id: number, body?: { deadline_at?: string }) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/publish/${id}`,
      method: "post",
      data: body,
    });
  },

  settleTask(id: number) {
    return request<ApiResponse<SettlementItem[]>>({
      url: `${API_PATH}/settle/${id}`,
      method: "post",
    });
  },
};

export default TaskAPI;

export interface TaskPageQuery extends PageQuery, UserByQueryParams {
  task_no?: string;
  task_type_id?: number;
  company_id?: number;
  period?: string;
  status?: string;
}

/** 任务类型模板（嵌套在任务响应中） */
export interface TaskTypeBrief {
  id?: number;
  code?: string;
  name?: string;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  required?: boolean;
  form_schema?: Record<string, unknown>[];
}

/** 医药公司（嵌套在任务响应中） */
export interface CompanyBrief {
  id?: number;
  name?: string;
  code?: string;
}

/** 结算明细（任务结算接口返回） */
export interface SettlementItem {
  settlement_id?: number;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  price?: number;
  qty?: number;
  amount?: number;
}

export interface TaskTable extends BaseType {
  task_no?: string;
  task_type_id?: number;
  task_type?: TaskTypeBrief | null;
  company_id?: number;
  company?: CompanyBrief | null;
  period?: string;
  unit_price?: number;
  exec_qty?: number;
  status?: string;
  publisher_id?: number | null;
  published_at?: string | null;
  deadline_at?: string | null;
}

export interface TaskForm extends BaseFormType {
  task_no?: string;
  task_type_id?: number;
  company_id?: number;
  period?: string;
  unit_price?: number;
  exec_qty?: number;
  deadline_at?: string;
}
