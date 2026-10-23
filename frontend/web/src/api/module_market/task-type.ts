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
  default_kind?: string;
  exec_standard?: string;
  required?: boolean;
  form_schema?: FormSchemaField[];
}

export interface TaskTypeForm extends BaseFormType {
  code?: string;
  name?: string;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  default_kind?: string;
  exec_standard?: string;
  required?: boolean;
  form_schema?: FormSchemaField[];
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
  | "file";

/** 采集字段选项 */
export interface FormSchemaOption {
  /** 选项显示名 */
  label: string;
  /** 选项值 */
  value: string;
}

/** 采集字段定义 */
export interface FormSchemaField {
  /** 字段唯一标识，作为表单数据的 key（建议英文/拼音，如 hospital_name，勿重复） */
  name: string;
  /** 字段显示名称（如 医院名称） */
  label: string;
  /** 字段类型 */
  type: FormSchemaFieldType;
  /** 是否必填 */
  required?: boolean;
  /** 输入占位提示 */
  placeholder?: string;
  /** 选项列表（仅 select/radio/checkbox 需要） */
  options?: FormSchemaOption[];
}
