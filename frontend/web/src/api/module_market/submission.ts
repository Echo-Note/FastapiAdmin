import { request } from "@utils";

const API_PATH = "/market/submissions";

const SubmissionAPI = {
  listSubmission(query?: SubmissionPageQuery) {
    return request<ApiResponse<PageResult<SubmissionTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailSubmission(id: number) {
    return request<ApiResponse<SubmissionTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  reviewSubmission(id: number, body: { approved: boolean; review_comment?: string }) {
    return request<ApiResponse<SubmissionTable>>({
      url: `${API_PATH}/review/${id}`,
      method: "post",
      data: body,
    });
  },
};

export default SubmissionAPI;

export interface SubmissionPageQuery extends PageQuery, UserByQueryParams {
  assignment_id?: number;
  user_id?: number;
  institution_id?: number;
  status?: string;
}

export interface SubmissionTable extends BaseType {
  assignment_id?: number;
  user_id?: number;
  subject_type?: string;
  institution_id?: number | null;
  institution?: { id?: number; name?: string; type?: string } | null;
  subject_name?: string | null;
  region?: string | null;
  archive_no?: string | null;
  period?: string;
  form_data?: Record<string, unknown>;
  status?: string;
  version?: number;
  reviewer_id?: number | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  ai_check_status?: string | null;
  ai_check_result?: Record<string, unknown> | null;
}
