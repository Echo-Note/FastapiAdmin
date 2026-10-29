<!-- 任务管理：CRUD + 发布 + 状态单向流转 -->
<template>
  <div class="fa-full-height">
    <!-- 流程轻提示：让运营知道发布后的下一步去向 -->
    <ElAlert
      class="market-flow-hint"
      type="info"
      :closable="false"
      show-icon
      title="任务流转提示"
      description="创建任务后先「发布」，再按需「分派」或公开大厅接单；成果在「成果审核」页处理，任务进度通过「状态流转」单向推进（发布→进行中→已完成→已结算→归档）。"
    />

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
        <FaDescriptions :column="4" :data="detailFormData" :items="detailItems" max-height="70vh">
          <template #projectName="{ row }">{{ resolveProjectName(row) }}</template>
          <template #assignMode="{ row }"><component :is="dictTag('market_assign_mode', row?.assign_mode)" /></template>
          <template #statusTag="{ row }"><component :is="dictTag('market_task_status', row?.status)" /></template>
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

    <!-- 状态流转对话框 -->
    <ElDialog v-model="statusDialogVisible" title="任务状态流转" width="480px" :close-on-click-modal="false">
      <ElAlert type="warning" :closable="false" show-icon title="状态只能单向推进，不可回退" class="status-hint" />
      <FaForm
        ref="statusFormRef"
        v-model="statusForm"
        :items="statusFormItems"
        :rules="statusRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="statusDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="statusSubmitting" @click="handleStatusSubmit">确定流转</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { h } from "vue";
import TaskAPI, { type TaskForm, type TaskTable } from "@/api/module_market/task";
import ProjectAPI from "@/api/module_market/project";
import TaskTemplateAPI from "@/api/module_market/task-template";
import { useDictStore } from "@stores";
import StatusTag from "@/components/display/fa-status-tag/index.vue";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { ElMessageBox } from "element-plus";
import { renderTableOperationCell, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketTask", inheritAttrs: false });

const dictStore = useDictStore();

// ── 字典：任务状态 / 分配方式 ──
const taskStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_task_status"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const assignModeOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_assign_mode") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);
const statusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_task_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

/** 用字典渲染状态标签（实时查 dict_label + list_class，避免字典异步加载导致空 map 快照） */
function dictTag(dictType: string, val?: unknown) {
  const strVal = typeof val === "string" ? val : undefined;
  if (!strVal) return "—";
  const item = dictStore.getDictLabel(dictType, strVal);
  if (typeof item === "string") return h(StatusTag, { type: "info" as StatusType, label: item });
  return h(StatusTag, { type: (item.list_class as StatusType) ?? "info", label: item.dict_label ?? strVal });
}

const searchForm = ref<{ task_no?: string; name?: string; project_id?: number; template_id?: number; period?: string; assign_mode?: string; status?: string }>({
  task_no: undefined,
  name: undefined,
  project_id: undefined,
  template_id: undefined,
  period: undefined,
  assign_mode: undefined,
  status: undefined,
});
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const projectOptions = ref<OptionType[]>([]);
const templateOptions = ref<OptionType[]>([]);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "任务编号", key: "task_no", type: "input", placeholder: "请输入任务编号", clearable: true, span: 6 },
  { label: "显示名", key: "name", type: "input", placeholder: "请输入任务显示名", clearable: true, span: 6 },
  { label: "项目", key: "project_id", type: "select", props: { placeholder: "请选择项目", options: projectOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "模板", key: "template_id", type: "select", props: { placeholder: "请选择模板", options: templateOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "周期", key: "period", type: "input", placeholder: "如 2026-10", clearable: true, span: 6 },
  { label: "分配方式", key: "assign_mode", type: "select", props: { placeholder: "请选择分配方式", options: assignModeOptions.value, clearable: true }, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<TaskTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
  onPublish: publishRow,
  onChangeStatus: changeStatusRow,
};

function buildRowActions(row: TaskTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:task:query", run: () => opCtx.onDetail(row.id!) },
  ];
  if (row.status === "DRAFT") {
    actions.push({ key: "edit", label: "编辑", artType: "edit", perm: "module_market:task:update", run: () => opCtx.onEdit(row.id!) });
    actions.push({ key: "publish", label: "发布", artType: "edit", perm: "module_market:task:publish", run: () => opCtx.onPublish(row.id!, row.task_no ?? "") });
    actions.push({ key: "delete", label: "删除", artType: "delete", perm: "module_market:task:delete", run: () => opCtx.onDelete(row.id!, row.task_no ?? "") });
  } else if (["PUBLISHED", "IN_PROGRESS", "COMPLETED", "SETTLED"].includes(row.status ?? "")) {
    actions.push({ key: "change_status", label: "状态流转", artType: "edit", perm: "module_market:task:update", run: () => opCtx.onChangeStatus(row) });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: TaskAPI.listTask,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: () => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task_no", label: "任务编号", minWidth: 120, showOverflowTooltip: true },
        { prop: "name", label: "显示名", minWidth: 180, showOverflowTooltip: true },
        { prop: "template", label: "任务模板", minWidth: 140, formatter: (row: TaskTable) => row.template?.name ?? "—" },
        { prop: "period", label: "周期", width: 90 },
        { prop: "assign_mode", label: "分配方式", width: 100, formatter: (row: TaskTable) => dictTag("market_assign_mode", row.assign_mode) },
        { prop: "status", label: "状态", width: 92, formatter: (row: TaskTable) => dictTag("market_task_status", row.status) },
        { prop: "published_at", label: "发布时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 220, fixed: "right", align: "center", formatter: (row: TaskTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ],
    },
  });

const detailFormData = ref<Partial<TaskTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "任务编号", prop: "task_no" },
  { label: "显示名", prop: "name" },
  { label: "任务模板", prop: "template.name" },
  { label: "项目", prop: "project_id", slot: "projectName" },
  { label: "周期", prop: "period" },
  { label: "分配方式", prop: "assign_mode", slot: "assignMode" },
  { label: "状态", prop: "status", slot: "statusTag" },
  { label: "发布人", prop: "publisher_id" },
  { label: "发布时间", prop: "published_at" },
  { label: "创建人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
];

const formData = ref<TaskForm>({ id: undefined, project_id: undefined, template_id: undefined, name: undefined, period: undefined, assign_mode: "direct" });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: TaskForm = { id: undefined, project_id: undefined, template_id: undefined, name: undefined, period: undefined, assign_mode: "direct" };

const rules = reactive({
  project_id: [{ required: true, message: "请选择项目", trigger: "change" }],
  template_id: [{ required: true, message: "请选择任务模板", trigger: "change" }],
  name: [{ required: true, message: "请输入任务显示名", trigger: "blur" }],
  period: [{ required: true, message: "请输入周期", trigger: "blur" }],
  assign_mode: [{ required: true, message: "请选择分配方式", trigger: "change" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "项目", key: "project_id", type: "select", span: 24, props: { placeholder: "请选择项目", options: projectOptions.value, filterable: true } },
  { label: "任务模板", key: "template_id", type: "select", span: 24, props: { placeholder: "请选择二级任务模板", options: templateOptions.value, filterable: true } },
  { label: "显示名", key: "name", type: "input", span: 24, props: { placeholder: "如 一心坦-等级医院管理", maxlength: 256 } },
  { label: "周期", key: "period", type: "input", span: 24, props: { placeholder: "继承项目周期，如 2026-10", maxlength: 16 } },
  { label: "分配方式", key: "assign_mode", type: "select", span: 24, props: { placeholder: "请选择分配方式", options: assignModeOptions.value } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<TaskForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: TaskAPI.detailTask as unknown as (id: number) => Promise<{ data: { data?: TaskForm } }>,
  createApi: TaskAPI.createTask,
  updateApi: TaskAPI.updateTask,
  titles: { create: "新增任务", update: "修改任务", detail: "任务详情" },
  detailFormData: detailFormData as unknown as Ref<Partial<TaskForm>>,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function loadOptions() {
  const [projectRes, templateRes] = await Promise.all([
    ProjectAPI.listProject({ page_no: 1, page_size: 100 }),
    TaskTemplateAPI.listTemplate({ page_no: 1, page_size: 100 }),
  ]);
  projectOptions.value = projectRes.data.data.items.map((p) => ({ value: p.id!, label: p.name ?? p.code ?? "" }));
  templateOptions.value = templateRes.data.data.items.map((t) => ({ value: t.id!, label: t.name ?? t.code ?? "" }));
}

onMounted(async () => {
  await dictStore.getDict(["market_task_status", "market_assign_mode"]);
  await loadOptions();
});

async function handleAdd() {
  await handleOpenDialog("create");
}

function resolveProjectName(row: Record<string, unknown> | null): string {
  const id = row?.project_id as number | undefined;
  if (id == null) return "—";
  return projectOptions.value.find((o) => o.value === id)?.label ?? `#${id}`;
}

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { task_no: undefined, name: undefined, project_id: undefined, template_id: undefined, period: undefined, assign_mode: undefined, status: undefined };
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
    await ElMessageBox.confirm(`确定发布任务「${taskNo}」吗？发布后任务将进入任务大厅/可被分派。`, "发布任务", { type: "warning" });
    await TaskAPI.publishTask(id);
    await refreshData();
  } catch {
    // 用户取消
  }
}

// ── 状态单向流转 ──
const statusDialogVisible = ref(false);
const statusSubmitting = ref(false);
const statusFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const statusForm = ref<{ id?: number; task_no?: string; status?: string; target_status?: string }>({ id: undefined, task_no: undefined, status: undefined, target_status: undefined });
// 单向流转顺序（去掉 DRAFT 起点）
const STATUS_FLOW = ["PUBLISHED", "IN_PROGRESS", "COMPLETED", "SETTLED", "ARCHIVED"] as const;

const statusFormItems = computed<FormItem[]>(() => {
  const cur = statusForm.value.status ?? "";
  const curIdx = STATUS_FLOW.indexOf(cur as (typeof STATUS_FLOW)[number]);
  const next = curIdx >= 0 ? STATUS_FLOW.slice(curIdx + 1) : [];
  return [
    { label: "任务编号", key: "task_no", type: "input", span: 24, props: { disabled: true } },
    { label: "当前状态", key: "status", type: "input", span: 24, props: { disabled: true } },
    { label: "流转到", key: "target_status", type: "select", span: 24, props: { placeholder: "请选择目标状态", options: next.map((s) => ({ value: s, label: taskStatusMap.value[s]?.text ?? s })) } },
  ];
});

const statusRules = reactive({ target_status: [{ required: true, message: "请选择目标状态", trigger: "change" }] });

function changeStatusRow(row: TaskTable) {
  statusForm.value = { id: row.id, task_no: row.task_no, status: row.status, target_status: undefined };
  statusDialogVisible.value = true;
}

async function handleStatusSubmit() {
  if (!statusFormRef.value || statusForm.value.id == null) return;
  try {
    await statusFormRef.value.validate();
  } catch {
    return;
  }
  if (!statusForm.value.target_status) return;
  statusSubmitting.value = true;
  try {
    await TaskAPI.changeStatusTask(statusForm.value.id, { status: statusForm.value.target_status });
    statusDialogVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    statusSubmitting.value = false;
  }
}
</script>

<style scoped>
.market-flow-hint {
  margin-bottom: 12px;
}
.status-hint {
  margin-bottom: 12px;
}
</style>
