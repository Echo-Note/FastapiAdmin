<!-- 采集模板：CRUD（form_schema 用可视化编辑器配置，支持 section/table） -->
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
            :perm-create="['module_market:template:create']"
            :perm-delete="['module_market:template:delete']"
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
      width="880px"
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
            <div class="mb-2 text-sm font-medium text-gray-700">采集字段（{{ detailFormData.form_schema?.length ?? 0 }} 个）</div>
            <ElTable :data="detailFormData.form_schema ?? []" border size="small">
              <ElTableColumn type="index" label="序" width="50" align="center" />
              <ElTableColumn label="分节" prop="section" min-width="120" show-overflow-tooltip />
              <ElTableColumn label="显示名" prop="label" min-width="110" show-overflow-tooltip />
              <ElTableColumn label="字段标识" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.type === "section" ? "—" : row.name || "—" }}</template>
              </ElTableColumn>
              <ElTableColumn label="类型" width="90" align="center">
                <template #default="{ row }">{{ typeLabel(row.type) }}</template>
              </ElTableColumn>
              <ElTableColumn label="必填" width="60" align="center">
                <template #default="{ row }">
                  <span v-if="row.type === 'section'" class="text-gray-400">—</span>
                  <span v-else :class="row.required ? 'text-red-500' : 'text-gray-400'">{{ row.required ? "是" : "否" }}</span>
                </template>
              </ElTableColumn>
              <ElTableColumn label="选项/子列" min-width="160" show-overflow-tooltip>
                <template #default="{ row }">{{ fieldSummary(row as FormSchemaField) }}</template>
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
          :label-width="110"
          label-position="right"
          :span="24"
          :gutter="16"
        >
          <template #form_schema="{ modelValue }">
            <div class="w-full">
              <div class="mb-2 text-sm font-medium text-gray-700">采集字段 Schema</div>
              <FormSchemaEditor v-model="modelValue.form_schema" />
            </div>
          </template>
        </FaForm>
      </template>
    </FaDialog>
  </div>
</template>

<script setup lang="ts">
import TemplateAPI, { type TemplateForm, type TemplateTable } from "@/api/module_market/template";
import type { FormSchemaField } from "@/api/module_market/task-type";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import FormSchemaEditor from "@/components/forms/form-schema-editor/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketTemplate", inheritAttrs: false });

/** 字段类型中文标签（与 form-schema-editor 保持一致） */
const TYPE_LABELS: Record<string, string> = {
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
  section: "分节标题",
};

function typeLabel(type?: string): string {
  return type ? TYPE_LABELS[type] ?? type : "";
}

/** 详情表格「选项/子列」列摘要 */
function fieldSummary(row: FormSchemaField): string {
  if (row.type === "section") return "—";
  if (row.type === "table") return `子列：${(row.columns ?? []).map((c) => c.label).join("、") || "—"}`;
  return (row.options ?? []).map((o) => o.label).join("、") || "—";
}

const searchForm = ref<{ code?: string; name?: string }>({ code: undefined, name: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "唯一编码", key: "code", type: "input", placeholder: "请输入唯一编码", clearable: true, span: 6 },
  { label: "模板名", key: "name", type: "input", placeholder: "请输入模板名", clearable: true, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<TemplateTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
};

function buildRowActions(row: TemplateTable): TableOperationAction[] {
  return [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:template:query", run: () => opCtx.onDetail(row.id!) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:template:update", run: () => opCtx.onEdit(row.id!) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:template:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: TemplateAPI.listTemplate,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<TemplateTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "code", label: "唯一编码", minWidth: 160, showOverflowTooltip: true },
        { prop: "name", label: "模板名", minWidth: 180, showOverflowTooltip: true },
        { prop: "scope", label: "任务号范围", width: 120, showOverflowTooltip: true },
        { prop: "form_schema", label: "字段数", width: 80, align: "center", formatter: (row: TemplateTable) => row.form_schema?.length ?? 0 },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 180, fixed: "right", align: "center", formatter: (row: TemplateTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<TemplateTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "唯一编码", prop: "code" },
  { label: "模板名", prop: "name" },
  { label: "任务号范围", prop: "scope" },
  { label: "创建人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
];

const formData = ref<TemplateForm>({ id: undefined, code: undefined, name: undefined, scope: undefined, form_schema: [] });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: TemplateForm = { id: undefined, code: undefined, name: undefined, scope: undefined, form_schema: [] };

const rules = reactive({
  code: [{ required: true, message: "请输入唯一编码", trigger: "blur" }],
  name: [{ required: true, message: "请输入模板名", trigger: "blur" }],
  scope: [{ required: true, message: "请输入任务号范围", trigger: "blur" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "唯一编码", key: "code", type: "input", span: 24, props: { placeholder: "如 grade_hospital_manage", maxlength: 64 } },
  { label: "模板名", key: "name", type: "input", span: 24, props: { placeholder: "如 等级医院管理采集模板", maxlength: 128 } },
  { label: "任务号范围", key: "scope", type: "input", span: 24, props: { placeholder: "如 5-17（覆盖的计价项任务号范围）", maxlength: 16 } },
  { label: "", key: "form_schema", span: 24 },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<TemplateForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: TemplateAPI.detailTemplate,
  createApi: TemplateAPI.createTemplate,
  updateApi: TemplateAPI.updateTemplate,
  titles: { create: "新增采集模板", update: "修改采集模板", detail: "采集模板详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function handleAdd() {
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
    await TemplateAPI.deleteTemplate([id]);
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
    await TemplateAPI.deleteTemplate(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}
</script>
