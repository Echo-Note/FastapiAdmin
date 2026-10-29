import { request } from "@utils";
import type { TaskItemConfig } from "./task-item";
import type { TaskConfig } from "./task-template";

const API_PATH = "/market/categories";

const TaskCategoryAPI = {
  listCategory(query?: TaskCategoryPageQuery) {
    return request<ApiResponse<PageResult<TaskCategoryTable>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  /** 任务目录树：一级分类 + 其下二级模板 */
  treeCategory() {
    return request<ApiResponse<TaskCategoryTreeItem[]>>({
      url: `${API_PATH}/tree`,
      method: "get",
    });
  },

  detailCategory(id: number) {
    return request<ApiResponse<TaskCategoryTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createCategory(body: TaskCategoryForm) {
    return request<ApiResponse<TaskCategoryTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateCategory(id: number, body: TaskCategoryForm) {
    return request<ApiResponse<TaskCategoryTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteCategory(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },
};

export default TaskCategoryAPI;

export interface TaskCategoryPageQuery extends PageQuery, UserByQueryParams {
  code?: string;
  name?: string;
}

export interface TaskCategoryTable extends BaseType {
  code?: string;
  name?: string;
  sort?: number;
  description?: string | null;
}

export interface TaskCategoryForm extends BaseFormType {
  name?: string;
  sort?: number;
  description?: string | null;
}

/** 任务目录树：三级任务子节点（不含 template 嵌套） */
export interface TaskItemTreeItem extends BaseType {
  code?: string;
  name?: string;
  config?: TaskItemConfig | null;
  sort?: number;
  enabled?: boolean;
  /** 前端内部：树形表格唯一 key */
  _rowKey?: string;
}

/** 任务目录树：二级模板子节点（含其下三级任务，不含 category 嵌套） */
export interface TaskTemplateTreeItem extends BaseType {
  code?: string;
  name?: string;
  category_id: number;
  /** 所属一级分类名称（tree 接口返回，供表格展示） */
  category_name?: string | null;
  config?: TaskConfig | null;
  enabled?: boolean;
  /** 其下三级任务 */
  items?: TaskItemTreeItem[];
  /** 前端内部：树形表格唯一 key（分类/模板 id 各自独立自增，需复合前缀避免 row-key 冲突） */
  _rowKey?: string;
}

/** 任务目录树：一级分类节点（含其下二级模板） */
export interface TaskCategoryTreeItem extends TaskCategoryTable {
  children?: TaskTemplateTreeItem[];
  /** 前端内部：树形表格唯一 key */
  _rowKey?: string;
}
