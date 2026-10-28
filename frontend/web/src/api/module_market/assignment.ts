import { request } from "@utils";

const API_PATH = "/market/assignments";

const AssignmentAPI = {
  listAssignment(query?: AssignmentPageQuery) {
    return request<ApiResponse<PageResult<AssignmentTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailAssignment(id: number) {
    return request<ApiResponse<AssignmentTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  /** 批量分派：一个任务指派给多个 C 端用户 */
  createAssignment(body: { task_id: number; user_ids: number[] }) {
    return request<ApiResponse<AssignmentTable[]>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  deleteAssignment(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default AssignmentAPI;

export interface AssignmentPageQuery extends PageQuery, UserByQueryParams {
  task_id?: number;
  user_id?: number;
  source?: string;
  status?: string;
}

export interface AssignmentTable extends BaseType {
  task_id?: number;
  user_id?: number;
  source?: string;
  status?: string;
  accepted_at?: string | null;
  submitted_at?: string | null;
  task?: {
    id?: number;
    task_no?: string;
    name?: string;
    period?: string;
    assign_mode?: string;
    status?: string;
  } | null;
}
