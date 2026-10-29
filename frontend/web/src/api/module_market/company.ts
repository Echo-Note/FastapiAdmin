import { request } from "@utils";

const API_PATH = "/market/companies";

const CompanyAPI = {
  listCompany(query?: CompanyPageQuery) {
    return request<ApiResponse<PageResult<CompanyTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailCompany(id: number) {
    return request<ApiResponse<CompanyTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createCompany(body: CompanyForm) {
    return request<ApiResponse<CompanyTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateCompany(id: number, body: CompanyForm) {
    return request<ApiResponse<CompanyTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteCompany(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default CompanyAPI;

export interface CompanyPageQuery extends PageQuery, UserByQueryParams {
  name?: string;
  credit_code?: string;
  status?: number;
}

export interface CompanyTable extends BaseType {
  name?: string;
  code?: string;
  credit_code?: string;
  contact?: string;
  contact_phone?: string;
  address?: string;
  status?: number;
  description?: string;
}

export interface CompanyForm extends BaseFormType {
  name?: string;
  credit_code?: string;
  contact?: string;
  contact_phone?: string;
  address?: string;
  status?: number;
  description?: string;
}
