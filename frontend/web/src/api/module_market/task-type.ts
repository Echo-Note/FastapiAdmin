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
  task_no?: number;
  template_id?: number;
  template?: { id?: number; code?: string; name?: string; scope?: string; form_schema?: FormSchemaField[] } | null;
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

export interface TaskTypeForm extends BaseFormType {
  code?: string;
  name?: string;
  task_no?: number;
  template_id?: number;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  default_kind?: string;
  exec_standard?: string;
  required?: boolean;
  min_qty?: number | null;
  max_per_period?: number | null;
  dedup_rule?: string | null;
}

/** 采集字段类型（对齐后端 FormSchemaField Pydantic 模型） */
export type FormSchemaFieldType =
  | "text"
  | "textarea"
  | "number"
  | "date"
  | "select"
  | "radio"
  | "checkbox"
  | "image"
  | "file"
  | "table"
  | "section";

/** 采集字段选项 */
export interface FormSchemaOption {
  /** 选项显示名 */
  label: string;
  /** 选项值 */
  value: string;
}

/** 采集字段定义 */
export interface FormSchemaField {
  /** 字段唯一标识，作为表单数据的 key（建议英文/拼音，如 hospital_name；type=section 时可为空） */
  name?: string | null;
  /** 字段显示名称（如 医院名称；type=section 时为分节标题） */
  label: string;
  /** 字段类型 */
  type: FormSchemaFieldType;
  /** 所属分节标题 */
  section?: string | null;
  /** 是否必填 */
  required?: boolean;
  /** 输入占位提示 */
  placeholder?: string;
  /** 选项列表（仅 select/radio/checkbox 需要） */
  options?: FormSchemaOption[];
  /** 多行子表列定义（仅 type=table 需要） */
  columns?: FormSchemaField[] | null;
}
