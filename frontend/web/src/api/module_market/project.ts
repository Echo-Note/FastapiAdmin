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

  /** 任务归集到项目（增量，幂等） */
  addProjectTask(id: number, body: { task_id: number }) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/tasks/${id}`,
      method: "post",
      data: body,
    });
  },

  /** 从项目移除任务归集 */
  removeProjectTask(id: number, task_id: number) {
    return request<ApiResponse<ProjectTable>>({
      url: `${API_PATH}/tasks/${id}/${task_id}`,
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
  amount?: number;
  period?: string;
  status?: string;
  publisher_id?: number | null;
  task_ids?: number[];
}

export interface ProjectForm extends BaseFormType {
  code?: string;
  name?: string;
  company_id?: number;
  amount?: number;
  period?: string;
  task_ids?: number[];
}
