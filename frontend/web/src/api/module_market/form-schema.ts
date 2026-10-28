/**
 * 动态表单结构（form_schema）前端类型定义。
 *
 * 权威定义源是后端 `app/modules/market/form_schema.py` 的 Pydantic 模型
 * （FormSchemaField / FormSchemaOption / FormSchemaColumn / FormSchemaSection）。
 *
 * - 二级模板的通用采集字段：`TaskConfig.form_schema`（FormSchema 有序分节列表）。
 * - 三级任务的专属采集字段：`TaskItemConfig.form_schema`（同构的 FormSchema 有序分节列表）。
 * - 字段形态：单值字段 + `type=table` 多行子表（columns 子列），可同分节混排。
 */

/** 采集字段选项（select/radio/checkbox 的可选项），对齐后端 FormSchemaOption */
export interface FormSchemaOption {
  /** 选项显示名 */
  label: string;
  /** 选项值 */
  value: string;
}

/** 多行子表（type=table）的子列定义，对齐后端 FormSchemaColumn（不允许再嵌套 table） */
export interface FormSchemaColumn {
  /** 子列唯一标识（如 product_name） */
  name: string;
  /** 子列显示名（如 产品名称） */
  label: string;
  /** 子列类型 */
  type: Exclude<FormSchemaFieldType, "table">;
  /** 该列是否必填 */
  required?: boolean;
  /** 输入占位提示 */
  placeholder?: string | null;
  /** 选项列表（仅 select/radio/checkbox 需要） */
  options?: FormSchemaOption[] | null;
}

/** 采集字段类型，对齐后端 FormSchemaField.type（table 为分节内多行子表） */
export type FormSchemaFieldType =
  | "text"
  | "textarea"
  | "number"
  | "date"
  | "select"
  | "radio"
  | "checkbox"
  | "image"
  | "file"
  | "table";

/** 采集字段定义，对齐后端 FormSchemaField（字段名由外层 dict 的 key 表达） */
export interface FormSchemaField {
  /** 字段显示名（如 医院名称） */
  label: string;
  /** 字段类型 */
  type: FormSchemaFieldType;
  /** 是否必填 */
  required?: boolean;
  /** 输入占位提示 */
  placeholder?: string | null;
  /** 选项列表（仅 select/radio/checkbox 需要） */
  options?: FormSchemaOption[] | null;
  /** 子表列定义（仅 type=table 需要） */
  columns?: FormSchemaColumn[] | null;
}

/** 采集表单分节：英文 code + 中文 name + 其下字段，对齐后端 FormSchemaSection */
export interface FormSchemaSection {
  /** 分节唯一标识（如 execution_info） */
  code: string;
  /** 分节显示名（如 执行信息） */
  name: string;
  /** 分节是否必填（标题展示「(必填)」标记） */
  required?: boolean;
  /** 分节下字段（字段名 → 字段定义） */
  fields: Record<string, FormSchemaField>;
}

/** 采集表单结构：有序分节列表（二级模板与三级任务共用） */
export type FormSchema = FormSchemaSection[];
