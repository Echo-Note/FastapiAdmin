<!-- 医药公司主数据：CRUD -->
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
            :perm-create="['module_market:company:create']"
            :perm-delete="['module_market:company:delete']"
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
          :label-width="100"
          label-position="right"
          :span="24"
          :gutter="16"
        />
      </template>
    </FaDialog>
  </div>
</template>

<script setup lang="ts">
import CompanyAPI, { type CompanyForm, type CompanyTable } from "@/api/module_market/company";
import { ENABLE_STATUS_MAP, ENABLE_STATUS_OPTIONS } from "@/api/module_market/constants";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketCompany", inheritAttrs: false });

const searchForm = ref<{ name?: string; status?: number }>({ name: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "公司名称", key: "name", type: "input", placeholder: "请输入公司名称", clearable: true, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: ENABLE_STATUS_OPTIONS, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<CompanyTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
};

function buildRowActions(row: CompanyTable): TableOperationAction[] {
  return [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:company:query", run: () => opCtx.onDetail(row.id!) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:company:update", run: () => opCtx.onEdit(row.id!) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:company:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: CompanyAPI.listCompany,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<CompanyTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "name", label: "公司名称", minWidth: 160, showOverflowTooltip: true },
        { prop: "code", label: "公司编码", minWidth: 120, showOverflowTooltip: true },
        { prop: "credit_code", label: "统一社会信用代码", minWidth: 180, showOverflowTooltip: true },
        { prop: "contact", label: "联系人", width: 100, showOverflowTooltip: true },
        { prop: "contact_phone", label: "联系电话", width: 140, showOverflowTooltip: true },
        { prop: "status", label: "状态", width: 88, status: ENABLE_STATUS_MAP },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 180, fixed: "right", align: "center", formatter: (row: CompanyTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<CompanyTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "公司名称", prop: "name" },
  { label: "公司编码", prop: "code" },
  { label: "统一社会信用代码", prop: "credit_code" },
  { label: "联系人", prop: "contact" },
  { label: "联系电话", prop: "contact_phone" },
  { label: "公司地址", prop: "address" },
  { label: "状态", prop: "status", tag: { map: ENABLE_STATUS_MAP } },
  { label: "创建人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
  { label: "备注", prop: "description", span: 4 },
];

const formData = ref<CompanyForm>({ id: undefined, name: undefined, code: undefined, credit_code: undefined, contact: undefined, contact_phone: undefined, address: undefined, status: 0, description: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: CompanyForm = { id: undefined, name: undefined, code: undefined, credit_code: undefined, contact: undefined, contact_phone: undefined, address: undefined, status: 0, description: undefined };

const rules = reactive({ name: [{ required: true, message: "请输入公司名称", trigger: "blur" }] });

const formItems = computed<FormItem[]>(() => [
  { label: "公司名称", key: "name", type: "input", span: 24, props: { placeholder: "请输入公司名称", maxlength: 128 } },
  { label: "公司编码", key: "code", type: "input", span: 24, props: { placeholder: "请输入公司编码", maxlength: 64 } },
  { label: "统一社会信用代码", key: "credit_code", type: "input", span: 24, props: { placeholder: "请输入统一社会信用代码", maxlength: 32 } },
  { label: "联系人", key: "contact", type: "input", span: 24, props: { placeholder: "请输入联系人", maxlength: 32 } },
  { label: "联系电话", key: "contact_phone", type: "input", span: 24, props: { placeholder: "请输入联系电话", maxlength: 20 } },
  { label: "公司地址", key: "address", type: "input", span: 24, props: { placeholder: "请输入公司地址", maxlength: 255 } },
  { label: "状态", key: "status", type: "radiogroup", span: 24, props: { options: [...ENABLE_STATUS_OPTIONS] } },
  { label: "备注", key: "description", type: "input", span: 24, props: { type: "textarea", rows: 3, maxlength: 200, showWordLimit: true, placeholder: "请输入备注" } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<CompanyForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: CompanyAPI.detailCompany,
  createApi: CompanyAPI.createCompany,
  updateApi: CompanyAPI.updateCompany,
  titles: { create: "新增医药公司", update: "修改医药公司", detail: "医药公司详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function handleAdd() {
  await handleOpenDialog("create");
}

async function handleSearch(params: { name?: string; status?: number }) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { name: undefined, status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除「${name}」吗？`);
    await CompanyAPI.deleteCompany([id]);
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
    await CompanyAPI.deleteCompany(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}
</script>
