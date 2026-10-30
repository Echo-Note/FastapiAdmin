import { request } from "@utils";
import type { FormSchema } from "./form-schema";

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
  /** 按任务所属项目过滤（后端转 assignment→task 子查询） */
  project_id?: number;
  /** 按任务所属二级模板过滤 */
  template_id?: number;
  /** 按三级任务过滤 */
  item_id?: number;
  user_id?: number;
  institution_id?: number;
  /** 档案号（模糊） */
  archive_no?: string;
  /** 提交月份（YYYY-MM） */
  period?: string;
  status?: string;
}

/** 任务上下文（对齐后端 SubmissionTaskContextSchema）：成果表只有 assignment_id，层级由后端升维 */
export interface SubmissionTaskContext {
  id?: number;
  task_no?: string;
  name?: string;
  project_id?: number;
  project_name?: string;
  category_id?: number;
  category_name?: string;
  template_id?: number;
  template_name?: string;
  item_id?: number | null;
  item_name?: string | null;
}

export interface SubmissionTable extends BaseType {
  assignment_id?: number;
  /** 任务上下文（项目 / 分类 / 模板 / 任务），列表与详情都回填 */
  task?: SubmissionTaskContext | null;
  user_id?: number;
  subject_type?: string;
  institution_id?: number | null;
  institution?: { id?: number; name?: string; type?: string } | null;
  subject_name?: string | null;
  region?: string | null;
  archive_no?: string | null;
  period?: string;
  form_data?: Record<string, unknown>;
  /** 采集表单结构：仅详情接口回填，是把 form_data 英文字段名渲染成中文标签的唯一映射源 */
  form_schema?: FormSchema | null;
  status?: string;
  version?: number;
  reviewer_id?: number | null;
  review_comment?: string | null;
  reviewed_at?: string | null;
  ai_check_status?: string | null;
  ai_check_result?: Record<string, unknown> | null;
}
