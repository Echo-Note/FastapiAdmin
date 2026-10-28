import { request } from "@utils";

const API_PATH = "/market/institution-images";

const InstitutionImageAPI = {
  listImage(query?: InstitutionImagePageQuery) {
    return request<ApiResponse<PageResult<InstitutionImageTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailImage(id: number) {
    return request<ApiResponse<InstitutionImageTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createImage(body: InstitutionImageForm) {
    return request<ApiResponse<InstitutionImageTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  deleteImage(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  /** 按机构归集查看图片（机构管理页） */
  listByInstitution(institutionId: number, query?: { page_no?: number; page_size?: number }) {
    return request<ApiResponse<PageResult<InstitutionImageTable>>>({
      url: `${API_PATH}/by-institution/${institutionId}`,
      method: "get",
      params: query,
    });
  },
};

export default InstitutionImageAPI;

export interface InstitutionImagePageQuery extends PageQuery, UserByQueryParams {
  institution_id?: number;
  category?: string;
  period?: string;
}

export interface InstitutionImageTable extends BaseType {
  institution_id?: number;
  institution?: { id?: number; name?: string } | null;
  submission_id?: number | null;
  image_url?: string;
  category?: string | null;
  uploaded_by?: number | null;
  period?: string | null;
}

export interface InstitutionImageForm extends BaseFormType {
  institution_id?: number;
  submission_id?: number | null;
  image_url?: string;
  category?: string | null;
  uploaded_by?: number | null;
  period?: string | null;
}
