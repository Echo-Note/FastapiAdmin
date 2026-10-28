<!-- 机构主数据（医院/药店/商业公司）：CRUD -->
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
            :perm-create="['module_market:institution:create']"
            :perm-delete="['module_market:institution:delete']"
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
import InstitutionAPI, { type InstitutionForm, type InstitutionTable } from "@/api/module_market/institution";
import { useDictStore } from "@stores";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketInstitution", inheritAttrs: false });

const dictStore = useDictStore();

// ── 字典：机构类型 / 启用状态 ──
const institutionTypeMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_institution_type"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const institutionTypeOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_institution_type") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);
// 启用状态：后端 status 为 Integer(0/1)，字典值为字符串 "0"/"1"，此处做数值映射
const enableStatusMap = computed<Record<number, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_enable_status"] ?? []).map((d) => [
      Number(d.dict_value),
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const enableStatusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_enable_status") ?? []).map((d) => ({ value: Number(d.dict_value), label: d.dict_label }))
);

const searchForm = ref<{ name?: string; type?: string; region?: string; status?: number }>({ name: undefined, type: undefined, region: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "机构名称", key: "name", type: "input", placeholder: "请输入机构名称", clearable: true, span: 6 },
  { label: "机构类型", key: "type", type: "select", props: { placeholder: "请选择机构类型", options: institutionTypeOptions.value, clearable: true }, span: 6 },
  { label: "所在区域", key: "region", type: "input", placeholder: "请输入所在区域", clearable: true, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: enableStatusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<InstitutionTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: deleteRow,
};

function buildRowActions(row: InstitutionTable): TableOperationAction[] {
  return [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:institution:query", run: () => opCtx.onDetail(row.id!) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:institution:update", run: () => opCtx.onEdit(row.id!) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:institution:delete", run: () => opCtx.onDelete(row.id!, row.name ?? "") },
  ];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: InstitutionAPI.listInstitution,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<InstitutionTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "name", label: "机构名称", minWidth: 160, showOverflowTooltip: true },
        { prop: "type", label: "机构类型", width: 110, status: institutionTypeMap.value },
        { prop: "level", label: "等级", width: 100, showOverflowTooltip: true },
        { prop: "region", label: "所在区域", width: 120, showOverflowTooltip: true },
        { prop: "contact", label: "联系人", width: 100, showOverflowTooltip: true },
        { prop: "contact_phone", label: "联系电话", width: 140, showOverflowTooltip: true },
        { prop: "status", label: "状态", width: 88, status: enableStatusMap.value },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 180, fixed: "right", align: "center", formatter: (row: InstitutionTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<InstitutionTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "机构名称", prop: "name" },
  { label: "机构类型", prop: "type", tag: { map: institutionTypeMap.value } },
  { label: "等级", prop: "level" },
  { label: "所在区域", prop: "region" },
  { label: "联系人", prop: "contact" },
  { label: "联系电话", prop: "contact_phone" },
  { label: "状态", prop: "status", tag: { map: enableStatusMap.value } },
  { label: "创建人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
  { label: "详细地址", prop: "address", span: 4 },
  { label: "备注", prop: "description", span: 4 },
];

const formData = ref<InstitutionForm>({ id: undefined, name: undefined, type: undefined, level: undefined, region: undefined, address: undefined, contact: undefined, contact_phone: undefined, status: 0, description: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: InstitutionForm = { id: undefined, name: undefined, type: undefined, level: undefined, region: undefined, address: undefined, contact: undefined, contact_phone: undefined, status: 0, description: undefined };

const rules = reactive({
  name: [{ required: true, message: "请输入机构名称", trigger: "blur" }],
  type: [{ required: true, message: "请选择机构类型", trigger: "change" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "机构名称", key: "name", type: "input", span: 24, props: { placeholder: "请输入机构名称", maxlength: 128 } },
  { label: "机构类型", key: "type", type: "select", span: 24, props: { placeholder: "请选择机构类型", options: institutionTypeOptions.value } },
  { label: "等级", key: "level", type: "input", span: 24, props: { placeholder: "如 三甲 / 二级（可选）", maxlength: 32 } },
  { label: "所在区域", key: "region", type: "input", span: 24, props: { placeholder: "请输入所在区域", maxlength: 64 } },
  { label: "详细地址", key: "address", type: "input", span: 24, props: { placeholder: "请输入详细地址", maxlength: 255 } },
  { label: "联系人", key: "contact", type: "input", span: 24, props: { placeholder: "请输入联系人", maxlength: 32 } },
  { label: "联系电话", key: "contact_phone", type: "input", span: 24, props: { placeholder: "请输入联系电话", maxlength: 20 } },
  { label: "状态", key: "status", type: "radiogroup", span: 24, props: { options: enableStatusOptions.value } },
  { label: "备注", key: "description", type: "input", span: 24, props: { type: "textarea", rows: 3, maxlength: 200, showWordLimit: true, placeholder: "请输入备注" } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<InstitutionForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: InstitutionAPI.detailInstitution,
  createApi: InstitutionAPI.createInstitution,
  updateApi: InstitutionAPI.updateInstitution,
  titles: { create: "新增机构", update: "修改机构", detail: "机构详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

async function handleAdd() {
  await handleOpenDialog("create");
}

async function handleSearch(params: { name?: string; type?: string; region?: string; status?: number }) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { name: undefined, type: undefined, region: undefined, status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除「${name}」吗？`);
    await InstitutionAPI.deleteInstitution([id]);
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
    await InstitutionAPI.deleteInstitution(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

onMounted(async () => {
  await dictStore.getDict(["market_institution_type", "market_enable_status"]);
});
</script>
