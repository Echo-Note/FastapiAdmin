<!-- 任务类型（对内计价项）：CRUD（form_schema 挂载在采集模板上，此处仅选择模板） -->
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
            :perm-create="['module_market:tasktype:create']"
            :perm-delete="['module_market:tasktype:delete']"
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
      width="720px"
      :form-mode="dialogVisible.type"
      :confirm-loading="submitLoading"
      @cancel="handleCloseDialog"
      @close="handleCloseDialog"
      @confirm="handleSubmit()"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <ElScrollbar max-height="70vh">
          <FaDescriptions :column="4" :data="detailFormData" :items="detailItems" />
          <div class="mt-4">
            <div class="mb-2 text-sm font-medium text-gray-700">采集字段（来自采集模板「{{ detailFormData.template?.name ?? "-" }}」，{{ detailFormData.template?.form_schema?.length ?? 0 }} 个）</div>
            <ElTable :data="detailFormData.template?.form_schema ?? []" border size="small">
              <ElTableColumn type="index" label="序" width="50" align="center" />
              <ElTableColumn label="分节" prop="section" min-width="120" show-overflow-tooltip />
              <ElTableColumn label="显示名" prop="label" min-width="110" show-overflow-tooltip />
              <ElTableColumn label="字段标识" prop="name" min-width="120" show-overflow-tooltip />
              <ElTableColumn label="类型" prop="type" width="90" align="center" />
              <ElTableColumn label="必填" width="60" align="center">
                <template #default="{ row }">
                  <span :class="row.required ? 'text-red-500' : 'text-gray-400'">{{ row.required ? "是" : "否" }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="选项" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">{{ row.options?.map((o: { label: string }) => o.label).join("、") || "—" }}</template>
              </ElTableColumn>
            </ElTable>
          </div>
        </ElScrollbar>
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
          :label-width="120"
          label-position="right"
          :span="24"
          :gutter="16"
        />
      </template>
    </FaDialog>
  </div>
</template>

<script setup lang="ts">
import TemplateAPI, { type TemplateTable } from "@/api/module_market/template";
import TaskTypeAPI, { type TaskTypeTable } from "@/api/module_market/task-type";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketTaskType", inheritAttrs: false });

/** 本地表单类型：form_schema 由所选采集模板承载 */
interface TaskTypeLocalForm {
  id?: number;
  code?: string;
  name?: string;
  task_no?: number;
  template_id?: number;
  template?: { name?: string; form_schema?: import("@/api/module_market/task-type").FormSchemaField[] } | null;
  service_type?: string;
  service_item?: string;
  service_task?: string;
  unit?: string;
  default_price?: number;
  exec_standard?: string;
  required?: boolean;
  min_qty?: number | null;
  max_per_period?: number | null;
  dedup_rule?: string | null;
}

const searchForm = ref<{ code?: string; name?: string }>({ code: undefined, name: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "唯一编码", key: "code", type: "input", placeholder: "请输入唯一编码", clearable: true, span: 6 },
  { label: "任务类型名", key: "name", type: "input", placeholder: "请输入任务类型名", clearable: true, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<TaskTypeTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
};

function buildRowActions(row: TaskTypeTable): TableOperationAction[] {
  return [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:tasktype:query", run: () => opCtx.onDetail(row.id!) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:tasktype:update", run: () => opCtx.onEdit(row.id!) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:tasktype:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: TaskTypeAPI.listTaskType,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<TaskTypeTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "task_no", label: "任务号", width: 80, align: "center" },
        { prop: "code", label: "唯一编码", minWidth: 140, showOverflowTooltip: true },
        { prop: "name", label: "任务类型名", minWidth: 140, showOverflowTooltip: true },
        { prop: "service_type", label: "服务类型", minWidth: 110, showOverflowTooltip: true },
        { prop: "service_item", label: "服务项目", minWidth: 110, showOverflowTooltip: true },
        { prop: "service_task", label: "服务任务", minWidth: 130, showOverflowTooltip: true },
        { prop: "unit", label: "计价单位", width: 100, showOverflowTooltip: true },
        { prop: "default_price", label: "默认单价", width: 100, align: "right" },
        { prop: "template.name", label: "采集模板", minWidth: 140, showOverflowTooltip: true },
        { prop: "required", label: "必选", width: 70, align: "center", formatter: (row: TaskTypeTable) => (row.required ? "是" : "否") },
        { prop: "operation", label: "操作", width: 180, fixed: "right", align: "center", formatter: (row: TaskTypeTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<TaskTypeLocalForm>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "唯一编码", prop: "code" },
  { label: "任务类型名", prop: "name" },
  { label: "任务号", prop: "task_no" },
  { label: "采集模板", prop: "template.name" },
  { label: "服务类型", prop: "service_type" },
  { label: "服务项目", prop: "service_item" },
  { label: "服务任务", prop: "service_task" },
  { label: "计价单位", prop: "unit" },
  { label: "默认单价", prop: "default_price" },
  { label: "是否必选", prop: "required", tag: { map: { true: { type: "success", text: "是" }, false: { type: "info", text: "否" } } } },
  { label: "必选最低量", prop: "min_qty" },
  { label: "周期次数上限", prop: "max_per_period" },
  { label: "去重约束", prop: "dedup_rule", span: 2 },
  { label: "执行标准", prop: "exec_standard", span: 4 },
];

const formData = ref<TaskTypeLocalForm>({ id: undefined, code: undefined, name: undefined, task_no: undefined, template_id: undefined, service_type: undefined, service_item: undefined, service_task: undefined, unit: undefined, default_price: undefined, exec_standard: undefined, required: false, min_qty: null, max_per_period: null, dedup_rule: null });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: TaskTypeLocalForm = { id: undefined, code: undefined, name: undefined, task_no: undefined, template_id: undefined, service_type: undefined, service_item: undefined, service_task: undefined, unit: undefined, default_price: undefined, exec_standard: undefined, required: false, min_qty: null, max_per_period: null, dedup_rule: null };

const rules = reactive({
  code: [{ required: true, message: "请输入唯一编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入任务类型名", trigger: "blur" }],
  task_no: [{ required: true, message: "请输入任务号", trigger: "blur" }],
  template_id: [{ required: true, message: "请选择采集模板", trigger: "change" }],
  service_type: [{ required: true, message: "请输入服务类型", trigger: "blur" }],
  service_item: [{ required: true, message: "请输入服务项目", trigger: "blur" }],
  service_task: [{ required: true, message: "请输入服务任务", trigger: "blur" }],
  unit: [{ required: true, message: "请输入计价单位", trigger: "blur" }],
  default_price: [{ required: true, message: "请输入默认单价", trigger: "blur" }],
});

/** 采集模板下拉选项（全量加载） */
const templateOptions = ref<{ label: string; value: number }[]>([]);

async function loadTemplateOptions() {
  try {
    const res = await TemplateAPI.listTemplate({ page_no: 1, page_size: 100 });
    templateOptions.value = (res.data.data?.items ?? []).map((t: TemplateTable) => ({ label: `${t.name}（${t.scope}）`, value: t.id! }));
  }
  catch {
    templateOptions.value = [];
  }
}

const formItems = computed<FormItem[]>(() => [
  { label: "唯一编码", key: "code", type: "input", span: 24, props: { placeholder: "如 hospital_delivery", maxlength: 64 } },
  { label: "任务类型名", key: "name", type: "input", span: 24, props: { placeholder: "请输入任务类型名", maxlength: 128 } },
  { label: "任务号", key: "task_no", type: "number", span: 24, props: { min: 1, max: 32767, controlsPosition: "right" } },
  { label: "采集模板", key: "template_id", type: "select", span: 24, props: { placeholder: "请选择采集模板", options: templateOptions.value } },
  { label: "服务类型", key: "service_type", type: "input", span: 24, props: { placeholder: "结算单三级-类型（如 医院管理）", maxlength: 64 } },
  { label: "服务项目", key: "service_item", type: "input", span: 24, props: { placeholder: "结算单三级-项目（如 等级医院）", maxlength: 64 } },
  { label: "服务任务", key: "service_task", type: "input", span: 24, props: { placeholder: "结算单三级-任务（如 等级医院管理）", maxlength: 64 } },
  { label: "计价单位", key: "unit", type: "input", span: 24, props: { placeholder: "如 家/月、份、次", maxlength: 32 } },
  { label: "默认单价", key: "default_price", type: "number", span: 24, props: { min: 0, precision: 2, controlsPosition: "right" } },
  { label: "是否必选", key: "required", type: "switch", span: 24 },
  { label: "必选最低量", key: "min_qty", type: "number", span: 24, props: { min: 0, controlsPosition: "right" } },
  { label: "周期次数上限", key: "max_per_period", type: "number", span: 24, props: { min: 0, controlsPosition: "right" } },
  { label: "去重约束", key: "dedup_rule", type: "input", span: 24, props: { placeholder: "如 单个医务人员单月单项目只能调研一次", maxlength: 128 } },
  { label: "执行标准", key: "exec_standard", type: "input", span: 24, props: { type: "textarea", rows: 3, placeholder: "请输入执行标准" } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<TaskTypeLocalForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: async (id: number) => {
    const res = await TaskTypeAPI.detailTaskType(id);
    return { data: { data: { ...res.data.data, template: res.data.data?.template ?? null } as TaskTypeLocalForm } };
  },
  createApi: async (form: TaskTypeLocalForm) => {
    const { template: _template, ...payload } = form;
    void _template;
    return TaskTypeAPI.createTaskType({ ...payload, min_qty: form.min_qty ?? null, max_per_period: form.max_per_period ?? null, dedup_rule: form.dedup_rule ?? null });
  },
  updateApi: async (id: number, form: TaskTypeLocalForm) => {
    const { template: _template, ...payload } = form;
    void _template;
    return TaskTypeAPI.updateTaskType(id, { ...payload, min_qty: form.min_qty ?? null, max_per_period: form.max_per_period ?? null, dedup_rule: form.dedup_rule ?? null });
  },
  titles: { create: "新增任务类型", update: "修改任务类型", detail: "任务类型详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function handleAdd() {
  await loadTemplateOptions();
  await handleOpenDialog("create");
}

async function handleSearch(params: { code?: string; name?: string }) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { code: undefined, name: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除「${name}」吗？`);
    await TaskTypeAPI.deleteTaskType([id]);
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
    await TaskTypeAPI.deleteTaskType(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

onMounted(() => {
  void loadTemplateOptions();
});
</script>
