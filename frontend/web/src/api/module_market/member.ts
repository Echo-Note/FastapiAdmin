import { request } from "@utils";
import type { MarketUserBrief } from "./settlement";

const API_PATH = "/market/members";

const MemberAPI = {
  /** C 端成员分页 */
  listMember(query?: MemberPageQuery) {
    return request<ApiResponse<PageResult<MemberTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  /** C 端成员详情 */
  detailMember(id: number) {
    return request<ApiResponse<MemberTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  /** 把已有用户纳入 C 端（已建档则幂等返回） */
  createMember(body: { user_id: number; status?: string }) {
    return request<ApiResponse<MemberTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  /** 调整成员状态（启用 / 停用） */
  updateMember(id: number, body: { status: string }) {
    return request<ApiResponse<MemberTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },
};

export default MemberAPI;

export interface MemberPageQuery extends PageQuery {
  user_id?: number;
  member_no?: string;
  status?: string;
}

/** C 端成员档案（对齐后端 MemberOutSchema）：存在这条记录 = 该用户是 C 端 */
export interface MemberTable extends BaseType {
  user_id?: number;
  /** 用户摘要：昵称/账号/手机号 */
  user?: MarketUserBrief | null;
  member_no?: string;
  status?: string;
}
