import { request } from "@utils";

const API_PATH = "/market/institutions";

const InstitutionAPI = {
  listInstitution(query?: InstitutionPageQuery) {
    return request<ApiResponse<PageResult<InstitutionTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailInstitution(id: number) {
    return request<ApiResponse<InstitutionTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  updateInstitution(id: number, body: InstitutionForm) {
    return request<ApiResponse<InstitutionTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteInstitution(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default InstitutionAPI;

export interface InstitutionPageQuery extends PageQuery, UserByQueryParams {
  name?: string;
  type?: string;
  region?: string;
  status?: number;
}

export interface InstitutionTable extends BaseType {
  name?: string;
  type?: string;
  level?: string;
  region?: string;
  address?: string;
  contact?: string;
  contact_phone?: string;
  status?: number;
  description?: string;
}

export interface InstitutionForm extends BaseFormType {
  name?: string;
  type?: string;
  level?: string;
  region?: string;
  address?: string;
  contact?: string;
  contact_phone?: string;
  status?: number;
  description?: string;
}
