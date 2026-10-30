import { request } from "@utils";

const API_PATH = "/market/products";

const ProductAPI = {
  listProduct(query?: ProductPageQuery) {
    return request<ApiResponse<PageResult<ProductTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailProduct(id: number) {
    return request<ApiResponse<ProductTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createProduct(body: ProductForm) {
    return request<ApiResponse<ProductTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateProduct(id: number, body: ProductForm) {
    return request<ApiResponse<ProductTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteProduct(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  auditProduct(body: ProductAuditParams) {
    return request<ApiResponse<number>>({
      url: `${API_PATH}/audit`,
      method: "put",
      data: body,
    });
  },
};

export default ProductAPI;

export interface ProductPageQuery extends PageQuery, UserByQueryParams {
  name?: string;
  manufacturer?: string;
  audit_status?: string;
  source?: string;
}

export interface ProductTable extends BaseType {
  name?: string;
  spec?: string;
  manufacturer?: string;
  source?: string;
  audit_status?: string;
  submitter_id?: number | null;
  reviewer_id?: number | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  display_name?: string;
}

export interface ProductForm extends BaseFormType {
  name?: string;
  spec?: string;
  manufacturer?: string;
}

export interface ProductAuditParams {
  ids: number[];
  approved: boolean;
  review_comment?: string;
}
