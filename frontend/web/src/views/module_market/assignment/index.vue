<!-- 任务分派：批量分派 + 撤销（仅待接收可撤销） -->
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
            :perm-create="['module_market:assignment:create']"
            :perm-delete="['module_market:assignment:delete']"
            :delete-loading="batchDeleting"
            create-text="批量分派"
            @add="openAssignDialog"
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

    <!-- 批量分派对话框 -->
    <ElDialog v-model="assignDialogVisible" title="批量分派任务" width="560px" :close-on-click-modal="false" @closed="resetAssignForm">
      <FaForm
        ref="assignFormRef"
        v-model="assignForm"
        :items="assignFormItems"
        :rules="assignRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="assignDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="assignSubmitting" @click="handleAssignSubmit">确定分派</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { h } from "vue";
import AssignmentAPI, { type AssignmentTable } from "@/api/module_market/assignment";
import TaskAPI from "@/api/module_market/task";
import UserAPI from "@/api/module_system/user";
import { useDictStore } from "@stores";
import StatusTag from "@/components/display/fa-status-tag/index.vue";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketAssignment", inheritAttrs: false });

const dictStore = useDictStore();
const route = useRoute();

// 分配状态字典选项（下拉）
const assignmentStatusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_assignment_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);
// 分配来源（本地常量：运营分派 / 大厅接单）
const SOURCE_MAP: Record<string, { type: StatusType; text: string }> = {
  assigned: { type: "primary", text: "运营分派" },
  claimed: { type: "warning", text: "大厅接单" },
};

/** 用字典渲染状态标签（实时查 dict_label + list_class，避免字典异步加载导致空 map 快照） */
function dictTag(dictType: string, val?: string) {
  if (!val) return "—";
  const item = dictStore.getDictLabel(dictType, val);
  if (typeof item === "string") return h(StatusTag, { type: "info" as StatusType, label: item });
  return h(StatusTag, { type: (item.list_class as StatusType) ?? "info", label: item.dict_label ?? val });
}

const searchForm = ref<{ task_id?: number; user_id?: number; status?: string }>({ task_id: undefined, user_id: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const taskOptions = ref<OptionType[]>([]);
const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "任务", key: "task_id", type: "select", props: { placeholder: "请选择任务", options: taskOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 8 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: assignmentStatusOptions.value, clearable: true }, span: 8 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<AssignmentTable>();

function buildRowActions(row: AssignmentTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [];
  if (row.status === "PENDING") {
    actions.push({ key: "delete", label: "撤销", artType: "delete", perm: "module_market:assignment:delete", run: () => deleteRow(row.id!, String(row.id)) });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshRemove } =
  useTable({
    core: {
      apiFn: AssignmentAPI.listAssignment,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: () => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task", label: "任务号", minWidth: 130, formatter: (row: AssignmentTable) => row.task?.task_no ?? "—" },
        { prop: "task", label: "显示名", minWidth: 160, showOverflowTooltip: true, formatter: (row: AssignmentTable) => row.task?.name ?? "—" },
        { prop: "task.period", label: "周期", width: 90, formatter: (row: AssignmentTable) => row.task?.period ?? "—" },
        { prop: "user_id", label: "接收用户", minWidth: 130, formatter: (row: AssignmentTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "source", label: "来源", width: 96, formatter: (row: AssignmentTable) => h(StatusTag, { type: SOURCE_MAP[row.source ?? ""]?.type ?? "info", label: SOURCE_MAP[row.source ?? ""]?.text ?? row.source ?? "—" }) },
        { prop: "status", label: "状态", width: 92, formatter: (row: AssignmentTable) => dictTag("market_assignment_status", row.status) },
        { prop: "accepted_at", label: "接收时间", width: 168, showOverflowTooltip: true },
        { prop: "submitted_at", label: "首次提交", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 90, fixed: "right", align: "center", formatter: (row: AssignmentTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ],
    },
  });

// ── 批量分派 ──
const assignDialogVisible = ref(false);
const assignSubmitting = ref(false);
const assignFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const assignForm = ref<{ task_id?: number; user_ids: number[] }>({ task_id: undefined, user_ids: [] });

const assignFormItems = computed<FormItem[]>(() => [
  { label: "任务", key: "task_id", type: "select", span: 24, props: { placeholder: "请选择已发布/进行中的任务", options: taskOptions.value, filterable: true } },
  { label: "接收用户", key: "user_ids", type: "select", span: 24, props: { placeholder: "请选择接收用户（可多选）", options: userOptions.value, filterable: true, multiple: true, collapseTags: true, collapseTagsTooltip: true } },
]);

const assignRules = reactive({
  task_id: [{ required: true, message: "请选择任务", trigger: "change" }],
  user_ids: [{ required: true, type: "array", min: 1, message: "请至少选择一名用户", trigger: "change" }],
});

async function loadOptions() {
  const [taskRes, userRes] = await Promise.all([
    TaskAPI.listTask({ page_no: 1, page_size: 100 }),
    UserAPI.listUser({ page_no: 1, page_size: 100 }),
  ]);
  taskOptions.value = taskRes.data.data.items.map((t) => ({ value: t.id!, label: `${t.task_no ?? ""}${t.name ? "（" + t.name + "）" : ""}` }));
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(async () => {
  await dictStore.getDict(["market_assignment_status"]);
  await loadOptions();
  // 从任务页跳转而来：透传 task_id 预填筛选
  const taskId = route.query.task_id;
  if (taskId) {
    searchForm.value.task_id = Number(taskId);
    replaceSearchParams(cleanEmptyArrayParams({ ...searchForm.value }) as Record<string, unknown>);
    getData();
  }
});

function openAssignDialog() {
  assignDialogVisible.value = true;
}

function resetAssignForm() {
  assignForm.value = { task_id: undefined, user_ids: [] };
}

async function handleAssignSubmit() {
  if (!assignFormRef.value) return;
  try {
    await assignFormRef.value.validate();
  } catch {
    return;
  }
  if (!assignForm.value.task_id || assignForm.value.user_ids.length === 0) return;
  assignSubmitting.value = true;
  try {
    await AssignmentAPI.createAssignment({ task_id: assignForm.value.task_id, user_ids: assignForm.value.user_ids });
    assignDialogVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    assignSubmitting.value = false;
  }
}

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { task_id: undefined, user_id: undefined, status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, label: string) {
  try {
    await confirmDelete(`确定撤销分派「${label}」吗？仅待接收状态可撤销。`);
    await AssignmentAPI.deleteAssignment([id]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await confirmBatchDelete(selectedIds.value.length, selectedRows.value.map((r) => String(r.id)));
    batchDeleting.value = true;
    await AssignmentAPI.deleteAssignment(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}
</script>
