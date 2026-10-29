<!-- 任务目录：一级分类 + 二级模板 + 三级任务 树形表格（单页完成全部 CRUD） -->
<template>
  <div class="fa-full-height">
    <ElCard class="fa-table-card">
      <FaTableHeader :loading="loading" @refresh="loadTree">
        <template #left>
          <div class="inline-flex flex-wrap items-center gap-2">
            <FaTableHeaderLeft :perm-create="['module_market:task_category:create']" @add="openCategoryCreate" />
            <ElButton @click="toggleExpand">{{ isExpanded ? "收起" : "展开" }}</ElButton>
          </div>
        </template>
      </FaTableHeader>

      <FaTable
        ref="faTableRef"
        row-key="_rowKey"
        :loading="loading"
        :data="treeData"
        :columns="columns"
        :tree-props="{ children: 'children' }"
        :default-expand-all="false"
      />
    </ElCard>

    <!-- 一级分类：新增/编辑 -->
    <FaDialog
      v-model="categoryDialogVisible"
      :title="categoryDialogMode === 'create' ? '新增一级分类' : '修改一级分类'"
      width="640px"
      :form-mode="categoryDialogMode"
      :confirm-loading="categorySubmitting"
      @confirm="handleCategorySubmit()"
      @cancel="categoryDialogVisible = false"
    >
      <FaForm
        ref="categoryFormRef"
        v-model="categoryForm"
        :items="categoryFormItems"
        :rules="categoryRules"
        label-suffix=":"
        :label-width="110"
        label-position="right"
        :span="24"
        :gutter="16"
      />
    </FaDialog>

    <!-- 二级模板：新增/编辑 -->
    <ElDialog
      v-model="templateDialogVisible"
      :title="templateDialogMode === 'create' ? '新增二级模板' : '修改二级模板'"
      width="820px"
      :close-on-click-modal="false"
    >
      <FaForm
        ref="templateFormRef"
        v-model="templateForm"
        :items="templateFormItems"
        :rules="templateRules"
        label-suffix=":"
        :label-width="130"
        label-position="right"
        :span="24"
        :gutter="16"
        scrollbar
        max-height="70vh"
      >
        <template #form_schema>
          <FormSchemaEditor v-model="templateForm.form_schema" />
        </template>
      </FaForm>
      <template #footer>
        <ElButton @click="templateDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="templateSubmitting" @click="handleTemplateSubmit">确定</ElButton>
      </template>
    </ElDialog>

    <!-- 三级任务：新增/编辑（采集字段可视化编辑） -->
    <ElDialog
      v-model="itemDialogVisible"
      :title="itemDialogMode === 'create' ? '新增三级任务' : '修改三级任务'"
      width="1100px"
      draggable
      :close-on-click-modal="false"
    >
      <FaForm
        ref="itemFormRef"
        v-model="itemForm"
        :items="itemFormItems"
        :rules="itemRules"
        label-suffix=":"
        :label-width="130"
        label-position="right"
        :span="24"
        :gutter="16"
        scrollbar
        max-height="70vh"
      >
        <template #form_schema>
          <FormSchemaEditor v-model="itemForm.form_schema" />
        </template>
      </FaForm>
      <template #footer>
        <ElButton @click="itemDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="itemSubmitting" @click="handleItemSubmit">确定</ElButton>
      </template>
    </ElDialog>

    <!-- 一级分类详情 -->
    <ElDialog v-model="categoryDetailVisible" title="一级分类详情" width="640px">
      <FaDescriptions :column="2" :data="categoryDetailData" :items="categoryDetailItems" max-height="60vh" />
    </ElDialog>

    <!-- 二级模板详情 -->
    <ElDialog v-model="templateDetailVisible" title="二级模板详情" width="720px">
      <FaDescriptions :column="2" :data="templateDetailData" :items="templateDetailItems" max-height="60vh" />
    </ElDialog>

    <!-- 三级任务详情 -->
    <ElDialog v-model="itemDetailVisible" title="三级任务详情" width="960px">
      <FaDescriptions :column="2" :data="itemDetailData" :items="itemDetailItems" max-height="60vh" />

      <!-- 采集表单：任务自包含完整分节，按分节块展示 -->
      <div v-for="section in itemDetailSections" :key="section.code" class="mt-3 overflow-hidden rounded-md border border-gray-200">
        <div class="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-2">
          <span class="text-sm font-medium text-gray-700">{{ section.name }}{{ section.required ? "（必填）" : "" }}</span>
          <span class="text-xs text-gray-400">{{ section.code }}</span>
        </div>
        <ElTable :data="section.fields" border size="small">
          <ElTableColumn label="字段标识" prop="name" min-width="130" show-overflow-tooltip />
          <ElTableColumn label="显示名" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.field.label }}</template>
          </ElTableColumn>
          <ElTableColumn label="类型" width="90" align="center">
            <template #default="{ row }">{{ columnTypeLabel(row.field.type) }}</template>
          </ElTableColumn>
          <ElTableColumn label="必填" width="60" align="center">
            <template #default="{ row }">
              <span :class="row.field.required ? 'text-red-500' : 'text-gray-400'">{{ row.field.required ? "是" : "否" }}</span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="选项/子列" min-width="240">
            <template #default="{ row }">
              <template v-if="row.field.type === 'table'">
                <div v-for="col in row.field.columns ?? []" :key="col.name" class="flex items-center gap-1 py-0.5 text-xs">
                  <span>{{ col.label }}</span>
                  <span class="text-gray-400">{{ col.name }}</span>
                  <span class="text-blue-400">{{ columnTypeLabel(col.type) }}</span>
                  <span v-if="col.required" class="text-red-400">必填</span>
                </div>
              </template>
              <span v-else-if="row.field.options?.length">{{ row.field.options.map((o: FormSchemaOption) => o.label).join("、") }}</span>
              <span v-else class="text-gray-400">—</span>
            </template>
          </ElTableColumn>
        </ElTable>
      </div>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import TaskCategoryAPI, {
  type TaskCategoryForm,
  type TaskCategoryTable,
  type TaskCategoryTreeItem,
  type TaskItemTreeItem,
  type TaskTemplateTreeItem,
} from "@/api/module_market/task-category";
import TaskTemplateAPI, { type TaskConfig, type TaskTemplateTable } from "@/api/module_market/task-template";
import TaskItemAPI, { type TaskItemConfig, type TaskItemForm, type TaskItemTable } from "@/api/module_market/task-item";
import type { FormSchema, FormSchemaField, FormSchemaOption } from "@/api/module_market/form-schema";
import FormSchemaEditor from "@/components/forms/form-schema-editor/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { useTableColumns } from "@/hooks/core/useTableColumns";
import { useDictStore } from "@stores";
import { ElMessage } from "element-plus";
import { renderTableOperationCell, type TableOperationAction } from "@utils";
import { useFormDraft } from "@/hooks/core/useFormDraft";

defineOptions({ name: "MarketTaskCatalog", inheritAttrs: false });

const dictStore = useDictStore();

// ── 树数据 ──
type NodeType = "category" | "template" | "item";
interface CategoryNode extends TaskCategoryTreeItem {
  _rowKey: string;
  _nodeType: NodeType;
  children?: TemplateNode[];
}
interface TemplateNode extends Omit<TaskTemplateTreeItem, "items"> {
  _rowKey: string;
  _nodeType: NodeType;
  children?: ItemNode[];
}
interface ItemNode extends TaskItemTreeItem {
  _rowKey: string;
  _nodeType: NodeType;
}

type CatalogRow = CategoryNode | TemplateNode | ItemNode;

const treeData = ref<CategoryNode[]>([]);
const loading = ref(false);
const isExpanded = ref(false);
const faTableRef = ref<{ elTableRef?: { toggleRowExpansion: (row: CatalogRow, expanded?: boolean) => void } } | null>(null);

const categoryOptions = ref<OptionType[]>([]);
const subjectTypeOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_subject_type") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

function nodeType(row: CatalogRow): NodeType {
  return row._nodeType;
}

async function loadTree() {
  loading.value = true;
  try {
    const res = await TaskCategoryAPI.treeCategory();
    const raw = res.data.data ?? [];
    // 分类/模板/任务 id 各自独立自增，直接用作树形 row-key 会冲突导致展开异常；
    // 给每个节点生成带前缀的唯一 key，并统一用 children 承载子节点。
    treeData.value = raw.map((c) => ({
      ...c,
      _rowKey: `category-${c.id}`,
      _nodeType: "category" as NodeType,
      children: (c.children ?? []).map((t) => ({
        ...t,
        _rowKey: `template-${t.id}`,
        _nodeType: "template" as NodeType,
        children: (t.items ?? []).map((i) => ({ ...i, _rowKey: `item-${i.id}`, _nodeType: "item" as NodeType })),
      })),
    }));
    categoryOptions.value = raw.map((c) => ({ value: c.id!, label: c.name ?? c.code ?? "" }));
  } catch {
    treeData.value = [];
  } finally {
    loading.value = false;
  }
}

function toggleExpand() {
  isExpanded.value = !isExpanded.value;
  nextTick(() => {
    const el = faTableRef.value?.elTableRef;
    if (!el || !treeData.value.length) return;
    const walk = (rows: CatalogRow[]) => {
      rows.forEach((row) => {
        const children = (row as CategoryNode | TemplateNode).children;
        if (children?.length) {
          el.toggleRowExpansion(row, isExpanded.value);
          walk(children);
        }
      });
    };
    walk(treeData.value);
  });
}

// ── 表格列 ──
const { columns } = useTableColumns<CatalogRow>(() => [
  { type: "globalIndex", width: 56, label: "序号" },
  { prop: "name", label: "名称", minWidth: 200, showOverflowTooltip: true, formatter: (row: CatalogRow) => row.name ?? "—" },
  {
    prop: "node_type",
    label: "类型",
    width: 80,
    align: "center",
    formatter: (row: CatalogRow) => ({ category: "分类", template: "模板", item: "任务" }[nodeType(row)]),
  },
  { prop: "code", label: "编号", minWidth: 160, showOverflowTooltip: true, formatter: (row: CatalogRow) => row.code ?? "—" },
  {
    prop: "subject_type",
    label: "采集对象",
    width: 120,
    formatter: (row: CatalogRow) => (nodeType(row) === "template" ? subjectTypeLabel((row as TemplateNode).config?.subject_type) : "—"),
  },
  {
    prop: "enabled",
    label: "启用",
    width: 70,
    align: "center",
    formatter: (row: CatalogRow) => (nodeType(row) === "category" ? "—" : ((row as TemplateNode | ItemNode).enabled ? "是" : "否")),
  },
  { prop: "description", label: "描述", minWidth: 180, showOverflowTooltip: true, formatter: (row: CatalogRow) => (nodeType(row) === "category" ? ((row as CategoryNode).description ?? "—") : "—") },
  {
    prop: "operation",
    label: "操作",
    width: 300,
    fixed: "right",
    align: "center",
    formatter: (row: CatalogRow) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }),
  },
]);

function subjectTypeLabel(val?: string): string {
  if (!val) return "—";
  return subjectTypeOptions.value.find((o) => o.value === val)?.label ?? val;
}

const COLUMN_TYPE_LABELS: Record<string, string> = {
  text: "单行文本",
  textarea: "多行文本",
  number: "数字",
  date: "日期",
  select: "下拉单选",
  radio: "单选按钮",
  checkbox: "多选",
  image: "图片上传",
  file: "文件附件",
  table: "多行子表",
};

function columnTypeLabel(type?: string): string {
  if (!type) return "—";
  return COLUMN_TYPE_LABELS[type] ?? type;
}

function buildRowActions(row: CatalogRow): TableOperationAction[] {
  const t = nodeType(row);
  if (t === "item") {
    return [
      { key: "detail", label: "详情", artType: "view", perm: "module_market:task_template:query", run: () => void openItemDetail(row as ItemNode) },
      { key: "edit", label: "编辑", artType: "edit", perm: "module_market:task_template:update", run: () => void openItemEdit(row as ItemNode) },
      { key: "delete", label: "删除", artType: "delete", perm: "module_market:task_template:delete", run: () => void deleteItemRow(row as ItemNode) },
    ];
  }
  if (t === "template") {
    return [
      { key: "addChild", label: "新增任务", artType: "add", perm: "module_market:task_template:create", run: () => void openItemCreate(row as TemplateNode) },
      { key: "detail", label: "详情", artType: "view", perm: "module_market:task_template:query", run: () => void openTemplateDetail(row.id!) },
      { key: "edit", label: "编辑", artType: "edit", perm: "module_market:task_template:update", run: () => void openTemplateEdit(row as TemplateNode) },
      { key: "delete", label: "删除", artType: "delete", perm: "module_market:task_template:delete", run: () => void deleteTemplateRow(row as TemplateNode) },
    ];
  }
  return [
    { key: "addChild", label: "新增模板", artType: "add", perm: "module_market:task_template:create", run: () => void openTemplateCreate(row as CategoryNode) },
    { key: "detail", label: "详情", artType: "view", perm: "module_market:task_category:query", run: () => void openCategoryDetail(row as CategoryNode) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:task_category:update", run: () => void openCategoryEdit(row as CategoryNode) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:task_category:delete", run: () => void deleteCategoryRow(row as CategoryNode) },
  ];
}

// ── 一级分类 CRUD ──
const categoryDialogVisible = ref(false);
const categoryDialogMode = ref<"create" | "update">("create");
const categorySubmitting = ref(false);
const categoryEditId = ref<number | null>(null);
const categoryFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const categoryForm = ref<TaskCategoryForm>({ id: undefined, name: undefined, sort: 0, description: undefined });

const categoryRules = reactive({
  name: [{ required: true, message: "请输入分类名", trigger: "blur" }],
});

const categoryFormItems: import("@/components/forms/fa-form/index.vue").FormItem[] = [
  { label: "分类名", key: "name", type: "input", span: 24, props: { placeholder: "如 商务管理服务", maxlength: 128 } },
  { label: "排序", key: "sort", type: "number", span: 24, props: { min: 0, controlsPosition: "right", placeholder: "越小越靠前" } },
  { label: "描述", key: "description", type: "input", span: 24, props: { type: "textarea", rows: 3, maxlength: 255, showWordLimit: true, placeholder: "分类描述（可选）" } },
];

const categoryDraft = useFormDraft({
  key: "task-catalog-category",
  dialogVisible: categoryDialogVisible,
  form: categoryForm,
  blank: () => ({ id: undefined, name: undefined, sort: 0, description: undefined }),
  mode: categoryDialogMode,
});

function openCategoryCreate() {
  categoryDialogMode.value = "create";
  categoryEditId.value = null;
  categoryDraft.openCreate();
}

function openCategoryEdit(row: CategoryNode) {
  categoryDialogMode.value = "update";
  categoryEditId.value = row.id!;
  categoryForm.value = { id: row.id, name: row.name, sort: row.sort ?? 0, description: row.description ?? undefined };
  categoryDialogVisible.value = true;
}

async function handleCategorySubmit() {
  if (!categoryFormRef.value) return;
  try {
    await categoryFormRef.value.validate();
  } catch {
    return;
  }
  categorySubmitting.value = true;
  try {
    if (categoryDialogMode.value === "create") {
      await TaskCategoryAPI.createCategory(categoryForm.value);
      categoryDraft.done();
    } else {
      await TaskCategoryAPI.updateCategory(categoryEditId.value!, categoryForm.value);
    }
    categoryDialogVisible.value = false;
    await loadTree();
  } catch (e) {
    ElMessage.error((e as Error).message ?? "操作失败");
  } finally {
    categorySubmitting.value = false;
  }
}

async function deleteCategoryRow(row: CategoryNode) {
  try {
    await confirmDelete(`确定删除分类「${row.name}」吗？`);
    await TaskCategoryAPI.deleteCategory([row.id!]);
    await loadTree();
  } catch {
    // 用户取消
  }
}

// ── 二级模板 CRUD ──
interface TemplateEditForm {
  name?: string;
  category_id?: number;
  enabled?: boolean;
  subject_type?: string;
  unit?: string;
  pricing_mode?: string;
  price?: number | null;
  exec_standard?: string | null;
  executor_requirement?: string | null;
  report_required?: boolean;
  form_schema?: FormSchema;
}

const templateDialogVisible = ref(false);
const templateDialogMode = ref<"create" | "update">("create");
const templateSubmitting = ref(false);
const templateEditId = ref<number | null>(null);
const templateFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const templateForm = ref<TemplateEditForm>({});

function blankTemplateForm(): TemplateEditForm {
  return {
    name: undefined,
    category_id: undefined,
    enabled: true,
    subject_type: "institution",
    unit: undefined,
    pricing_mode: "fixed",
    price: null,
    exec_standard: undefined,
    executor_requirement: undefined,
    report_required: true,
    form_schema: [],
  };
}

const templateDraft = useFormDraft({
  key: "task-catalog-template",
  dialogVisible: templateDialogVisible,
  form: templateForm,
  blank: blankTemplateForm,
  mode: templateDialogMode,
});

function fillTemplateFormFromConfig(config?: TaskConfig | null) {
  templateForm.value.subject_type = config?.subject_type ?? "institution";
  templateForm.value.unit = config?.unit;
  templateForm.value.pricing_mode = config?.pricing_mode ?? "fixed";
  templateForm.value.price = config?.price ?? null;
  templateForm.value.exec_standard = config?.exec_standard ?? undefined;
  templateForm.value.executor_requirement = config?.executor_requirement ?? undefined;
  templateForm.value.report_required = config?.report_required ?? true;
  templateForm.value.form_schema = config?.form_schema ? JSON.parse(JSON.stringify(config.form_schema)) : [];
}

function buildTemplateConfig(): TaskConfig {
  return {
    subject_type: templateForm.value.subject_type,
    unit: templateForm.value.unit,
    pricing_mode: templateForm.value.pricing_mode,
    price: templateForm.value.price ?? null,
    exec_standard: templateForm.value.exec_standard ?? null,
    executor_requirement: templateForm.value.executor_requirement ?? null,
    report_required: templateForm.value.report_required ?? true,
    form_schema: templateForm.value.form_schema ?? [],
  };
}

const PRICING_MODE_OPTIONS: OptionType[] = [
  { value: "fixed", label: "固定单价" },
  { value: "actual", label: "按票据实际结算" },
];

const templateRules = reactive({
  name: [{ required: true, message: "请输入模板名", trigger: "blur" }],
  category_id: [{ required: true, message: "请选择分类", trigger: "change" }],
  subject_type: [{ required: true, message: "请选择采集对象", trigger: "change" }],
  unit: [{ required: true, message: "请输入计价单位", trigger: "blur" }],
  pricing_mode: [{ required: true, message: "请选择计价方式", trigger: "change" }],
});

const templateFormItems: import("@/components/forms/fa-form/index.vue").FormItem[] = [
  { label: "模板名", key: "name", type: "input", span: 12, props: { placeholder: "如 等级医疗管理", maxlength: 128 } },
  { label: "一级分类", key: "category_id", type: "select", span: 12, props: { placeholder: "请选择分类", options: categoryOptions.value, filterable: true } },
  { label: "是否启用", key: "enabled", type: "switch", span: 12 },
  { label: "采集对象", key: "subject_type", type: "select", span: 12, props: { placeholder: "请选择采集对象类型", options: subjectTypeOptions.value } },
  { label: "计价单位", key: "unit", type: "input", span: 12, props: { placeholder: "如 元/月/家、元/份", maxlength: 32 } },
  { label: "计价方式", key: "pricing_mode", type: "select", span: 12, props: { placeholder: "请选择计价方式", options: PRICING_MODE_OPTIONS } },
  { label: "固定单价", key: "price", type: "number", span: 12, props: { min: 0, precision: 2, controlsPosition: "right", placeholder: "可暂空（按票据结算时无需）" } },
  { label: "执行人员要求", key: "executor_requirement", type: "input", span: 24, props: { placeholder: "如 临床协调员", maxlength: 128 } },
  { label: "执行标准", key: "exec_standard", type: "input", span: 24, props: { type: "textarea", rows: 3, placeholder: "多行执行标准" } },
  { label: "是否需月度报告", key: "report_required", type: "switch", span: 12 },
  { label: "采集字段（无三级任务时）", key: "form_schema", type: "input", span: 24 },
];

function openTemplateCreate(categoryRow?: CategoryNode) {
  templateDialogMode.value = "create";
  templateEditId.value = null;
  templateDraft.openCreate(categoryRow ? { category_id: categoryRow.id } : undefined);
}

async function openTemplateEdit(row: TemplateNode) {
  const res = await TaskTemplateAPI.detailTemplate(row.id!);
  const tpl = res.data.data;
  templateDialogMode.value = "update";
  templateEditId.value = row.id!;
  templateForm.value = blankTemplateForm();
  templateForm.value.name = tpl.name;
  templateForm.value.category_id = tpl.category_id;
  templateForm.value.enabled = tpl.enabled ?? true;
  fillTemplateFormFromConfig(tpl.config);
  templateDialogVisible.value = true;
}

async function handleTemplateSubmit() {
  if (!templateFormRef.value) return;
  try {
    await templateFormRef.value.validate();
  } catch {
    return;
  }
  templateSubmitting.value = true;
  try {
    const payload = {
      name: templateForm.value.name,
      category_id: templateForm.value.category_id,
      enabled: templateForm.value.enabled,
      config: buildTemplateConfig(),
    };
    if (templateDialogMode.value === "create") {
      await TaskTemplateAPI.createTemplate(payload);
      templateDraft.done();
    } else {
      await TaskTemplateAPI.updateTemplate(templateEditId.value!, payload);
    }
    templateDialogVisible.value = false;
    await loadTree();
  } catch (e) {
    ElMessage.error((e as Error).message ?? "操作失败");
  } finally {
    templateSubmitting.value = false;
  }
}

async function deleteTemplateRow(row: TemplateNode) {
  try {
    await confirmDelete(`确定删除模板「${row.name}」吗？`);
    await TaskTemplateAPI.deleteTemplate([row.id!]);
    await loadTree();
  } catch {
    // 用户取消
  }
}

// ── 三级任务 CRUD ──
interface ItemEditForm {
  name?: string;
  template_id?: number;
  enabled?: boolean;
  unit?: string | null;
  exec_standard?: string | null;
  executor_requirement?: string | null;
  max_per_month?: number | null;
  form_schema?: FormSchema;
}

const itemDialogVisible = ref(false);
const itemDialogMode = ref<"create" | "update">("create");
const itemSubmitting = ref(false);
const itemEditId = ref<number | null>(null);
const itemFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const itemForm = ref<ItemEditForm>({});

function blankItemForm(): ItemEditForm {
  return {
    name: undefined,
    template_id: undefined,
    enabled: true,
    unit: undefined,
    exec_standard: undefined,
    executor_requirement: undefined,
    max_per_month: undefined,
    form_schema: [],
  };
}

const itemDraft = useFormDraft({
  key: "task-catalog-item",
  dialogVisible: itemDialogVisible,
  form: itemForm,
  blank: blankItemForm,
  mode: itemDialogMode,
});

const itemRules = reactive({
  name: [{ required: true, message: "请输入任务名", trigger: "blur" }],
});

const itemFormItems: import("@/components/forms/fa-form/index.vue").FormItem[] = [
  { label: "任务名", key: "name", type: "input", span: 12, props: { placeholder: "如 配送协调", maxlength: 128 } },
  { label: "是否启用", key: "enabled", type: "switch", span: 12 },
  { label: "计价单位", key: "unit", type: "input", span: 12, props: { placeholder: "覆盖模板级，如 元/月/家", maxlength: 32 } },
  { label: "执行人员要求", key: "executor_requirement", type: "input", span: 12, props: { placeholder: "覆盖模板级，如 临床协调员", maxlength: 128 } },
  { label: "单月频次上限", key: "max_per_month", type: "number", span: 12, props: { min: 1, controlsPosition: "right", placeholder: "覆盖模板级" } },
  { label: "执行标准", key: "exec_standard", type: "input", span: 24, props: { type: "textarea", rows: 3, placeholder: "覆盖模板级" } },
  { label: "任务采集字段", key: "form_schema", type: "input", span: 24 },
];

function openItemCreate(templateRow?: TemplateNode) {
  itemDialogMode.value = "create";
  itemEditId.value = null;
  itemDraft.openCreate(templateRow ? { template_id: templateRow.id } : undefined);
}

async function openItemEdit(row: ItemNode) {
  const res = await TaskItemAPI.detailItem(row.id!);
  const it = res.data.data;
  itemDialogMode.value = "update";
  itemEditId.value = row.id!;
  itemForm.value = blankItemForm();
  itemForm.value.name = it.name;
  itemForm.value.template_id = it.template_id;
  itemForm.value.enabled = it.enabled ?? true;
  itemForm.value.unit = it.config?.unit ?? undefined;
  itemForm.value.exec_standard = it.config?.exec_standard ?? undefined;
  itemForm.value.executor_requirement = it.config?.executor_requirement ?? undefined;
  itemForm.value.max_per_month = it.config?.max_per_month ?? undefined;
  itemForm.value.form_schema = it.config?.form_schema ? JSON.parse(JSON.stringify(it.config.form_schema)) : [];
  itemDialogVisible.value = true;
}

function buildItemConfig(): TaskItemConfig {
  return {
    form_schema: itemForm.value.form_schema ?? [],
    unit: itemForm.value.unit ?? null,
    exec_standard: itemForm.value.exec_standard ?? null,
    executor_requirement: itemForm.value.executor_requirement ?? null,
    max_per_month: itemForm.value.max_per_month ?? null,
  };
}

async function handleItemSubmit() {
  if (!itemFormRef.value) return;
  try {
    await itemFormRef.value.validate();
  } catch {
    return;
  }
  itemSubmitting.value = true;
  try {
    const payload: TaskItemForm = {
      name: itemForm.value.name,
      template_id: itemForm.value.template_id,
      enabled: itemForm.value.enabled,
      config: buildItemConfig(),
    };
    if (itemDialogMode.value === "create") {
      await TaskItemAPI.createItem(payload);
      itemDraft.done();
    } else {
      await TaskItemAPI.updateItem(itemEditId.value!, payload);
    }
    itemDialogVisible.value = false;
    await loadTree();
  } catch (e) {
    ElMessage.error((e as Error).message ?? "操作失败");
  } finally {
    itemSubmitting.value = false;
  }
}

async function deleteItemRow(row: ItemNode) {
  try {
    await confirmDelete(`确定删除任务「${row.name}」吗？`);
    await TaskItemAPI.deleteItem([row.id!]);
    await loadTree();
  } catch {
    // 用户取消
  }
}

// ── 模板详情 ──
const templateDetailVisible = ref(false);
const templateDetailData = ref<Partial<TaskTemplateTable>>({});
const templateDetailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "模板编号", prop: "code" },
  { label: "模板名", prop: "name" },
  { label: "分类", prop: "category.name" },
  { label: "启用", prop: "enabled" },
  { label: "采集对象", prop: "config.subject_type" },
  { label: "计价单位", prop: "config.unit" },
  { label: "计价方式", prop: "config.pricing_mode" },
  { label: "固定单价", prop: "config.price" },
  { label: "执行人员要求", prop: "config.executor_requirement", span: 2 },
  { label: "执行标准", prop: "config.exec_standard", span: 2 },
  { label: "是否需月度报告", prop: "config.report_required" },
  { label: "创建人", prop: "created_by.name" },
];

async function openTemplateDetail(id: number) {
  const res = await TaskTemplateAPI.detailTemplate(id);
  templateDetailData.value = res.data.data;
  templateDetailVisible.value = true;
}

// ── 分类详情 ──
const categoryDetailVisible = ref(false);
const categoryDetailData = ref<Partial<TaskCategoryTable>>({});
const categoryDetailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "分类编号", prop: "code" },
  { label: "分类名", prop: "name" },
  { label: "排序", prop: "sort" },
  { label: "描述", prop: "description", span: 2 },
  { label: "创建人", prop: "created_by.name" },
];

function openCategoryDetail(row: CategoryNode) {
  categoryDetailData.value = row;
  categoryDetailVisible.value = true;
}

// ── 任务详情 ──
const itemDetailVisible = ref(false);
const itemDetailData = ref<Partial<TaskItemTable>>({});
const itemDetailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "任务编号", prop: "code" },
  { label: "任务名", prop: "name" },
  { label: "排序", prop: "sort" },
  { label: "计价单位", prop: "config.unit" },
  { label: "执行人员要求", prop: "config.executor_requirement" },
  { label: "单月频次上限", prop: "config.max_per_month" },
  { label: "执行标准", prop: "config.exec_standard", span: 2 },
];

/** 任务详情采集表单：任务自包含完整分节，按分节展示 */
const itemDetailSections = computed(() => {
  const sections: { code: string; name: string; required: boolean; fields: { name: string; field: FormSchemaField }[] }[] = [];
  for (const sec of itemDetailData.value.config?.form_schema ?? []) {
    sections.push({
      code: sec.code,
      name: sec.name,
      required: sec.required ?? false,
      fields: Object.entries(sec.fields ?? {}).map(([name, field]) => ({ name, field })),
    });
  }
  return sections;
});

async function openItemDetail(row: ItemNode) {
  const res = await TaskItemAPI.detailItem(row.id!);
  itemDetailData.value = res.data.data;
  itemDetailVisible.value = true;
}

onMounted(async () => {
  await dictStore.getDict(["market_subject_type"]);
  await loadTree();
});
</script>
