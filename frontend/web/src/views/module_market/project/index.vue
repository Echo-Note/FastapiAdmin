<!-- 项目管理：对外交付/结算单元，按关联的二级模板发布生成任务 -->
<template>
  <div class="fa-full-height">
    <FaSearchBar
      v-show="showSearchBar"
      ref="searchBarRef"
      v-model="searchForm"
      :items="searchItems"
      :is-expand="false"
      :show-expand="true"
      :show-reset="true"
      :show-search="true"
      @search="handleSearch"
      @reset="onResetSearch"
    />

    <ElCard class="fa-table-card" :style="{ 'margin-top': showSearchBar ? '12px' : '0' }">
      <FaTableHeader v-model:columns="columnChecks" v-model:showSearchBar="showSearchBar" :loading="loading" @refresh="refreshData">
        <template #left>
          <FaTableHeaderLeft
            :remove-ids="selectedIds"
            :perm-create="['module_market:project:create']"
            :perm-delete="['module_market:project:delete']"
            :delete-loading="batchDeleting"
            @add="handleAdd"
            @delete="handleBatchDelete"
          />
        </template>
      </FaTableHeader>

      <FaTable
        ref="faTableRef"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @selection-change="onTableSelectionChange"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>

    <FaDialog
      v-model="dialogVisible.visible"
      :title="dialogVisible.title"
      width="640px"
      :form-mode="dialogVisible.type"
      :confirm-loading="submitLoading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <FaDescriptions :column="4" :data="detailFormData" :items="detailItems" max-height="70vh">
          <template #taskUnitNames="{ row }">{{ resolveUnitNames(row) }}</template>
        </FaDescriptions>
      </template>
      <template v-else>
        <FaForm
          scrollbar
          max-height="70vh"
          :key="formRenderKey"
          ref="dataFormRef"
          v-model="formData"
          :items="formItems"
          :rules="rules"
          label-suffix=":"
          :label-width="110"
          label-position="right"
          :span="24"
          :gutter="16"
        >
          <template #period>
            <ElDatePicker
              v-model="formData.period"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="请选择截止日期"
              :shortcuts="periodShortcuts"
              :clearable="true"
              style="width: 100%"
            />
          </template>
          <template #task_units>
            <ElTreeSelect
              v-model="selectedUnitIds"
              :data="taskUnitTreeData"
              multiple
              show-checkbox
              filterable
              clearable
              :filter-node-method="filterTemplateNode"
              :props="{ label: 'name', children: 'children', disabled: 'disabled' }"
              node-key="id"
              :render-after-expand="false"
              placeholder="请选择任务"
              style="width: 100%"
            />
          </template>
        </FaForm>
      </template>
    </FaDialog>
  </div>
</template>

<script setup lang="ts">
import ProjectAPI, { type ProjectForm, type ProjectTable } from "@/api/module_market/project";
import CompanyAPI from "@/api/module_market/company";
import TaskCategoryAPI, { type TaskCategoryTreeItem } from "@/api/module_market/task-category";
import dayjs from "dayjs";
import { useDictStore } from "@stores";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { ElMessageBox } from "element-plus";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketProject", inheritAttrs: false });

const dictStore = useDictStore();

// ── 字典：项目状态（单向流转 DRAFT → IN_PROGRESS → COMPLETED → CLOSED）──
const projectStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_project_status"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const statusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_project_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

const searchForm = ref<{ code?: string; name?: string; company_id?: number; period?: string; status?: string }>({ code: undefined, name: undefined, company_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

/** 任务单元树节点：分类用负 id、中间模板与叶子模板用不同偏移，避免「分类 id / 模板 id / 三级任务 id」各自自增撞车；id 同时作为 node-key 与选中值 */
interface TaskUnitTreeNode {
  id: number;
  name: string;
  disabled?: boolean;
  children?: TaskUnitTreeNode[];
}

/** 叶子模板（无三级任务）偏移：选中值 - LEAF_TEMPLATE_OFFSET = 真实模板 id */
const LEAF_TEMPLATE_OFFSET = 100_000;
/** 有三级任务的中间模板偏移：仅作父级，不进入选中值 */
const TEMPLATE_OFFSET = 300_000;

const companyOptions = ref<OptionType[]>([]);
const taskUnitTreeData = ref<TaskUnitTreeNode[]>([]);
const itemMap = ref<Record<number, string>>({});
const leafTemplateMap = ref<Record<number, string>>({});

/** 把「一级分类 → 二级模板 → 三级任务」目录树转换为 el-tree-select 数据：三级任务为叶子；无三级任务的叶子模板本身即叶子（可选中） */
function buildTaskUnitTree(categories: TaskCategoryTreeItem[]): TaskUnitTreeNode[] {
  return categories.map((cat) => ({
    id: -(cat.id ?? 0),
    name: cat.name ?? "",
    disabled: !cat.children?.length,
    children: (cat.children ?? []).map((tpl) => {
      const items = tpl.items ?? [];
      if (items.length === 0) {
        return { id: LEAF_TEMPLATE_OFFSET + tpl.id!, name: tpl.name ?? tpl.code ?? "" };
      }
      return {
        id: TEMPLATE_OFFSET + tpl.id!,
        name: tpl.name ?? tpl.code ?? "",
        children: items.map((item) => ({ id: item.id!, name: item.name ?? item.code ?? "" })),
      };
    }),
  }));
}

/** 关联模板树节点按名称过滤（el-tree-select 的 filterable 需显式 filter-node-method，否则默认按 label 字段匹配会失效） */
function filterTemplateNode(value: string, data: { name?: string }): boolean {
  return (data.name ?? "").includes(value);
}

/** 截止日期快捷选项：相对今天推算一个月/三个月/六个月/一年 */
const periodShortcuts = [
  { text: "一个月", value: () => dayjs().add(1, "month").toDate() },
  { text: "三个月", value: () => dayjs().add(3, "month").toDate() },
  { text: "六个月", value: () => dayjs().add(6, "month").toDate() },
  { text: "一年", value: () => dayjs().add(1, "year").toDate() },
];

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "项目编号", key: "code", type: "input", placeholder: "请输入项目编号", clearable: true, span: 6 },
  { label: "项目名", key: "name", type: "input", placeholder: "请输入项目名", clearable: true, span: 6 },
  { label: "委托方", key: "company_id", type: "select", props: { placeholder: "请选择医药公司", options: companyOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "截止日期", key: "period", type: "date", props: { type: "date", placeholder: "请选择截止日期", clearable: true }, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<ProjectTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
  onPublish: publishRow,
  onChangeStatus: changeStatusRow,
};

function buildRowActions(row: ProjectTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:project:query", run: () => opCtx.onDetail(row.id!) },
  ];
  if (row.status === "DRAFT") {
    actions.push({ key: "edit", label: "编辑", artType: "edit", perm: "module_market:project:update", run: () => opCtx.onEdit(row.id!) });
    actions.push({ key: "delete", label: "删除", artType: "delete", perm: "module_market:project:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") });
    actions.push({ key: "publish", label: "发布", artType: "edit", perm: "module_market:project:publish", run: () => opCtx.onPublish(row.id!, row.name ?? "") });
    actions.push({ key: "advance", label: `流转为${projectStatusMap.value["IN_PROGRESS"]?.text ?? "进行中"}`, artType: "edit", perm: "module_market:project:update", run: () => opCtx.onChangeStatus(row.id!, row.name ?? "", "IN_PROGRESS") });
  } else if (row.status === "IN_PROGRESS") {
    actions.push({ key: "advance", label: `流转为${projectStatusMap.value["COMPLETED"]?.text ?? "已完成"}`, artType: "edit", perm: "module_market:project:update", run: () => opCtx.onChangeStatus(row.id!, row.name ?? "", "COMPLETED") });
  } else if (row.status === "COMPLETED") {
    actions.push({ key: "advance", label: `流转为${projectStatusMap.value["CLOSED"]?.text ?? "已关闭"}`, artType: "edit", perm: "module_market:project:update", run: () => opCtx.onChangeStatus(row.id!, row.name ?? "", "CLOSED") });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: ProjectAPI.listProject,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<ProjectTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "code", label: "项目编号", minWidth: 120, showOverflowTooltip: true },
        { prop: "name", label: "项目名", minWidth: 150, showOverflowTooltip: true },
        { prop: "company", label: "委托方", minWidth: 150, formatter: (row: ProjectTable) => row.company?.name ?? "—" },
        { prop: "period", label: "截止日期", width: 110 },
        { prop: "item_ids", label: "关联任务数", width: 100, align: "center", formatter: (row: ProjectTable) => (row.item_ids?.length ?? 0) + (row.template_ids?.length ?? 0) },
        { prop: "status", label: "状态", width: 92, status: projectStatusMap.value },
        { prop: "operation", label: "操作", width: 260, fixed: "right", align: "center", formatter: (row: ProjectTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<ProjectTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "项目编号", prop: "code" },
  { label: "项目名", prop: "name" },
  { label: "委托方", prop: "company.name" },
  { label: "截止日期", prop: "period" },
  { label: "状态", prop: "status", tag: { map: projectStatusMap.value } },
  { label: "关联任务", prop: "item_ids", slot: "taskUnitNames", span: 4 },
  { label: "创建人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
];

const formData = ref<ProjectForm>({ id: undefined, name: undefined, company_id: undefined, period: undefined, item_ids: undefined, template_ids: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: ProjectForm = { id: undefined, name: undefined, company_id: undefined, period: undefined, item_ids: undefined, template_ids: undefined };

/** 树选择器选中值：把三级任务 id 与「叶子模板 id + 偏移」合并为单一数组，读写时与 formData.item_ids / template_ids 互转 */
const selectedUnitIds = computed<number[]>({
  get: () => [
    ...(formData.value.item_ids ?? []),
    ...(formData.value.template_ids ?? []).map((id) => id + LEAF_TEMPLATE_OFFSET),
  ],
  set: (vals: number[]) => {
    formData.value.item_ids = vals.filter((id) => id < LEAF_TEMPLATE_OFFSET);
    formData.value.template_ids = vals.filter((id) => id >= LEAF_TEMPLATE_OFFSET).map((id) => id - LEAF_TEMPLATE_OFFSET);
  },
});

const rules = reactive({
  name: [{ required: true, message: "请输入项目名", trigger: "blur" }],
  company_id: [{ required: true, message: "请选择或输入委托方", trigger: "change" }],
  period: [{ required: true, message: "请选择截止日期", trigger: "change" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "项目名", key: "name", type: "input", span: 24, props: { placeholder: "项目名称", maxlength: 128 } },
  { label: "委托方", key: "company_id", type: "select", span: 24, props: { placeholder: "请选择或输入医药公司", options: companyOptions.value, filterable: true, allowCreate: true, defaultFirstOption: true } },
  { label: "截止日期", key: "period", span: 24 },
  { label: "关联任务", key: "task_units", span: 24 },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit: crudSubmit } = useCrudForm<ProjectForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  cacheKey: "project",
  detailApi: ProjectAPI.detailProject as unknown as (id: number) => Promise<{ data: { data?: ProjectForm } }>,
  createApi: ProjectAPI.createProject,
  updateApi: ProjectAPI.updateProject,
  titles: { create: "新增项目", update: "修改项目", detail: "项目详情" },
  detailFormData: detailFormData as unknown as Ref<Partial<ProjectForm>>,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

/** 提交前把「输入的新委托方名称」转换为公司 id（同名复用、否则自动创建） */
async function normalizeCompanyId() {
  const cid = formData.value.company_id;
  if (typeof cid !== "string" || !cid.trim()) return;
  const name = cid.trim();
  const exist = companyOptions.value.find((c) => c.label === name);
  if (exist) {
    formData.value.company_id = exist.value as number;
    return;
  }
  const res = await CompanyAPI.createCompany({ name });
  const id = res.data.data.id!;
  formData.value.company_id = id;
  companyOptions.value.push({ value: id, label: res.data.data.name ?? name });
}

/** 提交表单：先归一化委托方，再走通用 CRUD 提交流程 */
async function handleSubmit() {
  await normalizeCompanyId();
  await crudSubmit();
}

function resolveUnitNames(row: Record<string, unknown> | null): string {
  const itemIds = (row?.item_ids as number[] | undefined) ?? [];
  const templateIds = (row?.template_ids as number[] | undefined) ?? [];
  const names = [
    ...itemIds.map((id) => itemMap.value[id] ?? `#${id}`),
    ...templateIds.map((id) => leafTemplateMap.value[id] ?? `#${id}`),
  ];
  return names.length === 0 ? "—" : names.join("、");
}

async function loadOptions() {
  const [companyRes, treeRes] = await Promise.all([
    CompanyAPI.listCompany({ page_no: 1, page_size: 100 }),
    TaskCategoryAPI.treeCategory(),
  ]);
  companyOptions.value = companyRes.data.data.items.map((c) => ({ value: c.id!, label: c.name ?? "" }));
  const categories = treeRes.data.data ?? [];
  taskUnitTreeData.value = buildTaskUnitTree(categories);
  const itemEntries: [number, string][] = [];
  const leafTemplateEntries: [number, string][] = [];
  for (const cat of categories) {
    for (const tpl of cat.children ?? []) {
      const items = tpl.items ?? [];
      if (items.length === 0) {
        leafTemplateEntries.push([tpl.id!, tpl.name ?? tpl.code ?? ""]);
      } else {
        for (const item of items) itemEntries.push([item.id!, item.name ?? item.code ?? ""]);
      }
    }
  }
  itemMap.value = Object.fromEntries(itemEntries);
  leafTemplateMap.value = Object.fromEntries(leafTemplateEntries);
}

onMounted(async () => {
  await dictStore.getDict(["market_project_status"]);
  await loadOptions();
});

async function handleAdd() {
  await handleOpenDialog("create");
}

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { code: undefined, name: undefined, company_id: undefined, period: undefined, status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除项目「${name}」吗？`);
    await ProjectAPI.deleteProject([id]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await confirmBatchDelete(selectedIds.value.length, selectedRows.value.map((r) => String(r.name ?? r.id)));
    batchDeleting.value = true;
    await ProjectAPI.deleteProject(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

async function publishRow(id: number, name: string) {
  try {
    await ElMessageBox.confirm(`确定发布项目「${name}」吗？发布后将按关联的任务批量生成任务实例。`, "发布项目", { type: "warning" });
    await ProjectAPI.publishProject(id);
    await refreshData();
  } catch {
    // 用户取消
  }
}

async function changeStatusRow(id: number, name: string, target: string) {
  const text = projectStatusMap.value[target]?.text ?? target;
  try {
    await ElMessageBox.confirm(`确定将项目「${name}」流转为「${text}」吗？`, "状态流转", { type: "warning" });
    await ProjectAPI.changeProjectStatus(id, target);
    await refreshData();
  } catch {
    // 用户取消
  }
}
</script>
