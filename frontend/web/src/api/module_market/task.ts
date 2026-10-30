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

  /** 发布任务（DRAFT → PUBLISHED；发布与分派解耦，仅状态流转） */
  publishTask(id: number) {
    return request<ApiResponse<TaskTable>>({
      url: `${API_PATH}/publish/${id}`,
      method: "post",
    });
  },

  /** 批量发布任务（仅状态流转，不处理分派） */
  batchPublishTask(body: { ids: number[] }) {
    return request<ApiResponse<TaskBatchPublishResult>>({
      url: `${API_PATH}/batch-publish`,
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
  /** 三级任务ID */
  item_id?: number;
  /** 一级分类ID */
  category_id?: number;
  /** 排除的任务状态（如 DRAFT，仅展示已发布任务） */
  exclude_status?: string;
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

/** 三级任务（嵌套在任务响应中） */
export interface TaskItemBrief {
  id?: number;
  code?: string;
  name?: string;
  template_id?: number;
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
  /** 所属项目摘要 */
  project?: { id?: number; name?: string; code?: string } | null;
  template_id?: number;
  template?: TaskTemplateBrief | null;
  /** 三级任务ID（叶子模板任务为空） */
  item_id?: number | null;
  /** 三级任务 */
  item?: TaskItemBrief | null;
  name?: string;
  period?: string;
  assign_mode?: string;
  status?: string;
  publisher_id?: number | null;
  published_at?: string | null;
  /** 已分派/接收人数（后端列表聚合字段） */
  assignment_count?: number;
}

export interface TaskForm extends BaseFormType {
  project_id?: number;
  /** 三级任务ID（与 template_id 二选一） */
  item_id?: number;
  /** 叶子模板ID（无三级任务时） */
  template_id?: number;
  period?: string;
  assign_mode?: string;
  status?: string;
}

/** 批量发布结果 */
export interface TaskBatchPublishResult {
  published: number;
  failed: Array<{ id: number; msg: string }>;
}
