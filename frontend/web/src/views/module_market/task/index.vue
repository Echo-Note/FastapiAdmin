<!-- 任务管理：CRUD + 发布 + 归集结算 -->
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
            :perm-create="['module_market:task:create']"
            :perm-delete="['module_market:task:delete']"
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
        <FaDescriptions :column="4" :data="detailFormData" :items="detailItems" max-height="70vh" />
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
import TaskAPI, { type TaskForm, type TaskTable } from "@/api/module_market/task";
import TaskTypeAPI from "@/api/module_market/task-type";
import CompanyAPI from "@/api/module_market/company";
import { ASSIGN_MODE_MAP, ASSIGN_MODE_OPTIONS, TASK_STATUS_MAP } from "@/api/module_market/constants";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { ElMessageBox } from "element-plus";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketTask", inheritAttrs: false });

const searchForm = ref<{ task_no?: string; task_type_id?: number; company_id?: number; period?: string; status?: string }>({ task_no: undefined, task_type_id: undefined, company_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const taskTypeOptions = ref<OptionType[]>([]);
const companyOptions = ref<OptionType[]>([]);
const statusOptions = computed<OptionType[]>(() => Object.entries(TASK_STATUS_MAP).map(([value, v]) => ({ value, label: v.text })));

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "任务号", key: "task_no", type: "input", placeholder: "请输入任务号", clearable: true, span: 6 },
  { label: "任务类型", key: "task_type_id", type: "select", props: { placeholder: "请选择任务类型", options: taskTypeOptions.value, clearable: true }, span: 6 },
  { label: "委托公司", key: "company_id", type: "select", props: { placeholder: "请选择医药公司", options: companyOptions.value, clearable: true }, span: 6 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-10", clearable: true, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<TaskTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
  onPublish: publishRow,
  onSettle: settleRow,
};

function buildRowActions(row: TaskTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:task:query", run: () => opCtx.onDetail(row.id!) },
  ];
  if (row.status === "DRAFT") {
    actions.push({ key: "edit", label: "编辑", artType: "edit", perm: "module_market:task:update", run: () => opCtx.onEdit(row.id!) });
    actions.push({ key: "publish", label: "发布", artType: "edit", perm: "module_market:task:publish", run: () => opCtx.onPublish(row.id!, row.task_no ?? "") });
    actions.push({ key: "delete", label: "删除", artType: "delete", perm: "module_market:task:delete", run: () => opCtx.onDelete(row.id!, row.task_no ?? "") });
  } else if (row.status === "DEADLINE" || row.status === "IN_PROGRESS" || row.status === "PUBLISHED") {
    actions.push({ key: "settle", label: "归集结算", artType: "edit", perm: "module_market:settlement:run", run: () => opCtx.onSettle(row.id!, row.task_no ?? "") });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: TaskAPI.listTask,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<TaskTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task_no", label: "任务号", minWidth: 120, showOverflowTooltip: true },
        { prop: "task_type", label: "任务类型", minWidth: 140, formatter: (row: TaskTable) => row.task_type?.name ?? "—" },
        { prop: "company", label: "委托公司", minWidth: 140, formatter: (row: TaskTable) => row.company?.name ?? "—" },
        { prop: "period", label: "周期", width: 90 },
        { prop: "unit_price", label: "单价", width: 90, align: "right" },
        { prop: "exec_qty", label: "执行数量", width: 90, align: "right" },
        { prop: "assign_mode", label: "分配方式", width: 100, status: ASSIGN_MODE_MAP },
        { prop: "assign_limit", label: "接单人数", width: 90, align: "right" },
        { prop: "status", label: "状态", width: 92, status: TASK_STATUS_MAP },
        { prop: "deadline_at", label: "截止时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 220, fixed: "right", align: "center", formatter: (row: TaskTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<TaskTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "任务号", prop: "task_no" },
  { label: "任务类型", prop: "task_type.name" },
  { label: "委托公司", prop: "company.name" },
  { label: "周期", prop: "period" },
  { label: "本期单价", prop: "unit_price" },
  { label: "执行数量", prop: "exec_qty" },
  { label: "分配方式", prop: "assign_mode", tag: { map: ASSIGN_MODE_MAP } },
  { label: "最大接单人数", prop: "assign_limit" },
  { label: "状态", prop: "status", tag: { map: TASK_STATUS_MAP } },
  { label: "发布时间", prop: "published_at" },
  { label: "截止时间", prop: "deadline_at" },
  { label: "创建人", prop: "created_by.name" },
];

const formData = ref<TaskForm>({ id: undefined, task_no: undefined, task_type_id: undefined, company_id: undefined, period: undefined, unit_price: undefined, exec_qty: undefined, assign_mode: "direct", assign_limit: undefined, deadline_at: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: TaskForm = { id: undefined, task_no: undefined, task_type_id: undefined, company_id: undefined, period: undefined, unit_price: undefined, exec_qty: undefined, assign_mode: "direct", assign_limit: undefined, deadline_at: undefined };

const rules = reactive({
  task_no: [{ required: true, message: "请输入任务号", trigger: "blur" }],
  task_type_id: [{ required: true, message: "请选择任务类型", trigger: "change" }],
  company_id: [{ required: true, message: "请选择委托公司", trigger: "change" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
  exec_qty: [{ required: true, message: "请输入执行数量", trigger: "blur" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "任务号", key: "task_no", type: "input", span: 24, props: { placeholder: "如 1-4、5-17…", maxlength: 32 } },
  { label: "任务类型", key: "task_type_id", type: "select", span: 24, props: { placeholder: "请选择任务类型模板", options: taskTypeOptions.value } },
  { label: "委托公司", key: "company_id", type: "select", span: 24, props: { placeholder: "请选择医药公司", options: companyOptions.value } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-10", maxlength: 16 } },
  { label: "本期单价", key: "unit_price", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right", placeholder: "缺省取模板默认单价" } },
  { label: "执行数量", key: "exec_qty", type: "number", span: 24, props: { min: 1, controlsPosition: "right" } },
  { label: "分配方式", key: "assign_mode", type: "select", span: 24, props: { placeholder: "请选择分配方式", options: ASSIGN_MODE_OPTIONS } },
  { label: "最大接单人数", key: "assign_limit", type: "number", span: 24, props: { min: 1, controlsPosition: "right", placeholder: "公开大厅任务必填，先到先得、抢完即止" } },
  { label: "截止时间", key: "deadline_at", type: "datetime", span: 24, props: { placeholder: "请选择截止时间" } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<TaskForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  // 详情接口返回 TaskTable（含 task_type/company 嵌套），表单仅使用其中扁平的 id 字段，
  // 此处通过类型断言将两者桥接：运行时 detailTask 返回的完整 TaskTable 同时满足详情展示与表单回填。
  detailApi: TaskAPI.detailTask as unknown as (id: number) => Promise<{ data: { data?: TaskForm } }>,
  createApi: TaskAPI.createTask,
  updateApi: TaskAPI.updateTask,
  titles: { create: "新增任务", update: "修改任务", detail: "任务详情" },
  detailFormData: detailFormData as unknown as Ref<Partial<TaskForm>>,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function loadOptions() {
  const [typeRes, companyRes] = await Promise.all([
    TaskTypeAPI.listTaskType({ page_no: 1, page_size: 100 }),
    CompanyAPI.listCompany({ page_no: 1, page_size: 100 }),
  ]);
  taskTypeOptions.value = typeRes.data.data.items.map((t) => ({ value: t.id!, label: t.name ?? "" }));
  companyOptions.value = companyRes.data.data.items.map((c) => ({ value: c.id!, label: c.name ?? "" }));
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
  searchForm.value = { task_no: undefined, task_type_id: undefined, company_id: undefined, period: undefined, status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, taskNo: string) {
  try {
    await confirmDelete(`确定删除任务「${taskNo}」吗？`);
    await TaskAPI.deleteTask([id]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await confirmBatchDelete(selectedIds.value.length, selectedRows.value.map((r) => String(r.task_no ?? r.id)));
    batchDeleting.value = true;
    await TaskAPI.deleteTask(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

async function publishRow(id: number, taskNo: string) {
  try {
    await ElMessageBox.confirm(`确定发布任务「${taskNo}」吗？`, "发布任务", { type: "warning" });
    await TaskAPI.publishTask(id);
    await refreshData();
  } catch {
    // 用户取消
  }
}

async function settleRow(id: number, taskNo: string) {
  try {
    await ElMessageBox.confirm(`确定对任务「${taskNo}」触发归集结算吗？系统将汇总全部审核通过的成果并生成结算单。`, "归集结算", { type: "warning" });
    await TaskAPI.settleTask(id);
    await refreshData();
  } catch {
    // 用户取消
  }
}
</script>
