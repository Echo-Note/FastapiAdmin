import { request } from "@utils";

import type { FormSchemaField } from "./task-type";

const API_PATH = "/market/templates";

const TemplateAPI = {
  listTemplate(query?: TemplatePageQuery) {
    return request<ApiResponse<PageResult<TemplateTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailTemplate(id: number) {
    return request<ApiResponse<TemplateTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createTemplate(body: TemplateForm) {
    return request<ApiResponse<TemplateTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateTemplate(id: number, body: TemplateForm) {
    return request<ApiResponse<TemplateTable>>({
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

export default TemplateAPI;

export interface TemplatePageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
}

export interface TemplateTable extends BaseType {
  code?: string;
  name?: string;
  scope?: string;
  form_schema?: FormSchemaField[];
}

export interface TemplateForm extends BaseFormType {
  code?: string;
  name?: string;
  scope?: string;
  form_schema?: FormSchemaField[];
}
