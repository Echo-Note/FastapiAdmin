import { request } from "@utils";

const API_PATH = "/market/projects";

const ProjectAPI = {
  listProject(query?: ProjectPageQuery) {
    return request<ApiResponse<PageResult<ProjectTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailProject(id: number) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createProject(body: ProjectForm) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateProject(id: number, body: ProjectForm) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteProject(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  /** 项目关联二级任务模板（幂等） */
  addProjectTemplate(id: number, body: { template_id: number }) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/templates/${id}`,
      method: "post",
      data: body,
    });
  },

  /** 移除项目关联的二级任务模板 */
  removeProjectTemplate(id: number, template_id: number) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/templates/${id}/${template_id}`,
      method: "delete",
    });
  },

  /** 项目状态流转（草稿 → 进行中 → 已完成 → 已关闭） */
  changeProjectStatus(id: number, status: string) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/status/${id}`,
      method: "post",
      data: { status },
    });
  },

  /** 发布项目：按关联的二级模板批量生成任务实例 */
  publishProject(id: number) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/publish/${id}`,
      method: "post",
      data: {},
    });
  },
};

export default ProjectAPI;

export interface ProjectPageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
  company_id?: number;
  period?: string;
  status?: string;
}

export interface ProjectTable extends BaseType {
  code?: string;
  name?: string;
  company_id?: number;
  company?: { id?: number; name?: string } | null;
  period?: string;
  status?: string;
  publisher_id?: number | null;
  /** 关联的二级任务模板 ID 列表 */
  template_ids?: number[];
}

export interface ProjectForm extends BaseFormType {
  name?: string;
  company_id?: number;
  period?: string;
  template_ids?: number[];
}
