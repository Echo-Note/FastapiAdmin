<!-- 项目管理：对外交付/结算单元，任务可归集到多个项目 -->
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
          <template #taskNames="{ row }">{{ resolveTaskNames(row) }}</template>
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
        />
      </template>
    </FaDialog>
  </div>
</template>

<script setup lang="ts">
import ProjectAPI, { type ProjectForm, type ProjectTable } from "@/api/module_market/project";
import CompanyAPI from "@/api/module_market/company";
import TaskAPI from "@/api/module_market/task";
import { PROJECT_STATUS_MAP } from "@/api/module_market/constants";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { ElMessageBox } from "element-plus";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketProject", inheritAttrs: false });

const searchForm = ref<{ code?: string; name?: string; company_id?: number; period?: string; status?: string }>({ code: undefined, name: undefined, company_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const companyOptions = ref<OptionType[]>([]);
const taskOptions = ref<OptionType[]>([]);
const taskMap = ref<Record<number, string>>({});
const statusOptions = computed<OptionType[]>(() => Object.entries(PROJECT_STATUS_MAP).map(([value, v]) => ({ value, label: v.text })));

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "项目编码", key: "code", type: "input", placeholder: "请输入项目编码", clearable: true, span: 6 },
  { label: "项目名", key: "name", type: "input", placeholder: "请输入项目名", clearable: true, span: 6 },
  { label: "委托方", key: "company_id", type: "select", props: { placeholder: "请选择医药公司", options: companyOptions.value, clearable: true }, span: 6 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-10", clearable: true, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<ProjectTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
  onAdvance: advanceStatus,
};

function buildRowActions(row: ProjectTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:project:query", run: () => opCtx.onDetail(row.id!) },
  ];
  if (row.status === "DRAFT") {
    actions.push({ key: "edit", label: "编辑", artType: "edit", perm: "module_market:project:update", run: () => opCtx.onEdit(row.id!) });
    actions.push({ key: "delete", label: "删除", artType: "delete", perm: "module_market:project:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") });
    actions.push({ key: "advance", label: "开始进行", artType: "edit", perm: "module_market:project:update", run: () => opCtx.onAdvance(row.id!, row.name ?? "", "IN_PROGRESS") });
  } else if (row.status === "IN_PROGRESS") {
    actions.push({ key: "advance", label: "判定完成", artType: "edit", perm: "module_market:project:update", run: () => opCtx.onAdvance(row.id!, row.name ?? "", "COMPLETED") });
  } else if (row.status === "COMPLETED") {
    actions.push({ key: "advance", label: "归档关闭", artType: "edit", perm: "module_market:project:update", run: () => opCtx.onAdvance(row.id!, row.name ?? "", "CLOSED") });
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
        { prop: "code", label: "项目编码", minWidth: 120, showOverflowTooltip: true },
        { prop: "name", label: "项目名", minWidth: 150, showOverflowTooltip: true },
        { prop: "company", label: "委托方", minWidth: 150, formatter: (row: ProjectTable) => row.company?.name ?? "—" },
        { prop: "amount", label: "对外金额", width: 110, align: "right" },
        { prop: "period", label: "周期", width: 90 },
        { prop: "task_ids", label: "归集任务数", width: 100, align: "center", formatter: (row: ProjectTable) => row.task_ids?.length ?? 0 },
        { prop: "status", label: "状态", width: 92, status: PROJECT_STATUS_MAP },
        { prop: "operation", label: "操作", width: 200, fixed: "right", align: "center", formatter: (row: ProjectTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<ProjectTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "项目编码", prop: "code" },
  { label: "项目名", prop: "name" },
  { label: "委托方", prop: "company.name" },
  { label: "对外金额", prop: "amount" },
  { label: "周期", prop: "period" },
  { label: "状态", prop: "status", tag: { map: PROJECT_STATUS_MAP } },
  { label: "归集任务", prop: "task_ids", slot: "taskNames" },
  { label: "创建人", prop: "created_by.name" },
];

const formData = ref<ProjectForm>({ id: undefined, code: undefined, name: undefined, company_id: undefined, amount: 0, period: undefined, task_ids: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: ProjectForm = { id: undefined, code: undefined, name: undefined, company_id: undefined, amount: 0, period: undefined, task_ids: undefined };

const rules = reactive({
  code: [{ required: true, message: "请输入项目编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入项目名", trigger: "blur" }],
  company_id: [{ required: true, message: "请选择委托方", trigger: "change" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "项目编码", key: "code", type: "input", span: 24, props: { placeholder: "唯一编码", maxlength: 64 } },
  { label: "项目名", key: "name", type: "input", span: 24, props: { placeholder: "项目名称", maxlength: 128 } },
  { label: "委托方", key: "company_id", type: "select", span: 24, props: { placeholder: "请选择医药公司", options: companyOptions.value, filterable: true } },
  { label: "对外金额", key: "amount", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right", placeholder: "与任务金额不挂钩" } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-10", maxlength: 16 } },
  { label: "归集任务", key: "task_ids", type: "select", span: 24, props: { placeholder: "请选择归集任务（可多选）", options: taskOptions.value, multiple: true, filterable: true, clearable: true } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<ProjectForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: ProjectAPI.detailProject as unknown as (id: number) => Promise<{ data: { data?: ProjectForm } }>,
  createApi: ProjectAPI.createProject,
  updateApi: ProjectAPI.updateProject,
  titles: { create: "新增项目", update: "修改项目", detail: "项目详情" },
  detailFormData: detailFormData as unknown as Ref<Partial<ProjectForm>>,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

function resolveTaskNames(row: Record<string, unknown> | null): string {
  const ids = (row?.task_ids as number[] | undefined) ?? [];
  if (ids.length === 0) return "—";
  return ids.map((id) => taskMap.value[id] ?? `#${id}`).join("、");
}

async function loadOptions() {
  const [companyRes, taskRes] = await Promise.all([
    CompanyAPI.listCompany({ page_no: 1, page_size: 100 }),
    TaskAPI.listTask({ page_no: 1, page_size: 100 }),
  ]);
  companyOptions.value = companyRes.data.data.items.map((c) => ({ value: c.id!, label: c.name ?? "" }));
  taskOptions.value = taskRes.data.data.items.map((t) => ({ value: t.id!, label: t.task_no ?? "" }));
  taskMap.value = Object.fromEntries(taskRes.data.data.items.map((t) => [t.id!, t.task_no ?? ""]));
}

onMounted(loadOptions);

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

async function advanceStatus(id: number, name: string, target: string) {
  const text = PROJECT_STATUS_MAP[target]?.text ?? target;
  try {
    await ElMessageBox.confirm(`确定将项目「${name}」流转为「${text}」吗？`, "状态流转", { type: "warning" });
    await ProjectAPI.changeProjectStatus(id, target);
    await refreshData();
  } catch {
    // 用户取消
  }
}
</script>
