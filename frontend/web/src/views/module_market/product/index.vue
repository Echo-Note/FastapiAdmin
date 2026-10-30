<!-- 产品库：C 端提交成果时的产品三要素字典，C 端自动入库的记录在此审核 -->
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
            :perm-delete="['module_market:product:delete']"
            :delete-loading="batchDeleting"
            @delete="handleBatchDelete"
          />
          <ElButton
            v-hasPerm="'module_market:product:audit'"
            type="success"
            plain
            :disabled="selectedIds.length === 0"
            @click="handleOpenAudit(true)"
          >
            批量通过
          </ElButton>
          <ElButton
            v-hasPerm="'module_market:product:audit'"
            type="warning"
            plain
            :disabled="selectedIds.length === 0"
            @click="handleOpenAudit(false)"
          >
            批量驳回
          </ElButton>
        </template>
        <template #right>
          <ElButton v-hasPerm="'module_market:product:create'" type="primary" @click="handleOpenDialog('create')">
            新增产品
          </ElButton>
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
        <FaDescriptions :column="2" :data="detailFormData" :items="detailItems" max-height="70vh" />
      </template>
      <template v-else>
        <FaForm
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

    <!-- 驳回意见：通过时无需填写，驳回必须填 -->
    <ElDialog v-model="auditDialog.visible" :title="auditDialog.approved ? '批量通过' : '批量驳回'" width="480px">
      <ElAlert
        :type="auditDialog.approved ? 'success' : 'warning'"
        :closable="false"
        show-icon
        :title="auditDialog.approved ? '通过后该产品对所有 C 端用户可检索' : '驳回后该产品不再参与检索，需填写原因'"
      />
      <div class="mt-3 text-sm" style="color: var(--el-text-color-regular)">
        已选 {{ auditDialog.ids.length }} 条
      </div>
      <ElInput
        v-model="auditDialog.review_comment"
        class="mt-2"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        :placeholder="auditDialog.approved ? '审核意见（可选）' : '请填写驳回原因'"
      />
      <template #footer>
        <ElButton @click="auditDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="auditSubmitting" @click="handleSubmitAudit">确定</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import ProductAPI, {
  type ProductAuditParams,
  type ProductForm,
  type ProductTable,
} from "@/api/module_market/product";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import {
  cleanEmptyArrayParams,
  renderTableOperationCell,
  resolveStatusColumns,
  type StatusType,
  type TableOperationAction,
} from "@utils";

defineOptions({ name: "MarketProduct", inheritAttrs: false });

// ── 状态与来源映射（本模块不依赖字典表，避免新增菜单还要配字典） ──
const auditStatusMap: Record<string, { type: StatusType; text: string }> = {
  pending: { type: "warning", text: "待审核" },
  approved: { type: "success", text: "已通过" },
  rejected: { type: "danger", text: "已驳回" },
};
const auditStatusOptions: OptionType[] = [
  { value: "pending", label: "待审核" },
  { value: "approved", label: "已通过" },
  { value: "rejected", label: "已驳回" },
];
const searchForm = ref<{ name?: string; manufacturer?: string; audit_status?: string }>({
  name: undefined,
  manufacturer: undefined,
  audit_status: undefined,
});
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "产品名称", key: "name", type: "input", placeholder: "请输入产品名称", clearable: true, span: 6 },
  { label: "生产企业", key: "manufacturer", type: "input", placeholder: "请输入生产企业", clearable: true, span: 6 },
  {
    label: "审核状态",
    key: "audit_status",
    type: "select",
    props: { placeholder: "请选择审核状态", options: auditStatusOptions, clearable: true },
    span: 6,
  },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedRows, selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<ProductTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onEdit: (id: number) => void handleOpenDialog("update", id),
  onDelete: (id: number, name: string) => void deleteRow(id, name),
  onAudit: (id: number, approved: boolean) => {
    auditDialog.value.approved = approved;
    auditDialog.value.ids = [id];
    auditDialog.value.review_comment = "";
    auditDialog.value.visible = true;
  },
};

function buildRowActions(row: ProductTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:product:query", run: () => opCtx.onDetail(row.id!) },
    { key: "edit", label: "编辑", artType: "edit", perm: "module_market:product:update", run: () => opCtx.onEdit(row.id!) },
  ];
  // 已通过的不再给「通过」、已驳回的不再给「驳回」，避免无意义的状态回写
  if (row.audit_status !== "approved") {
    actions.push({
      key: "approve",
      label: "通过",
      artType: "add",
      perm: "module_market:product:audit",
      run: () => opCtx.onAudit(row.id!, true),
    });
  }
  if (row.audit_status !== "rejected") {
    actions.push({
      key: "reject",
      label: "驳回",
      artType: "more",
      perm: "module_market:product:audit",
      run: () => opCtx.onAudit(row.id!, false),
    });
  }
  actions.push({
    key: "delete",
    label: "删除",
    artType: "delete",
    perm: "module_market:product:delete",
    run: () => opCtx.onDelete(row.id!, row.name ?? ""),
  });
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshUpdate, refreshRemove } =
  useTable({
    core: {
      apiFn: ProductAPI.listProduct,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<ProductTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "name", label: "产品名称", minWidth: 160, showOverflowTooltip: true },
        { prop: "spec", label: "产品规格", minWidth: 140, showOverflowTooltip: true },
        { prop: "manufacturer", label: "生产企业", minWidth: 180, showOverflowTooltip: true },
        { prop: "audit_status", label: "审核状态", width: 100, status: auditStatusMap },
        { prop: "created_by.name", label: "提交人", width: 120, showOverflowTooltip: true },
        { prop: "review_comment", label: "审核意见", minWidth: 140, showOverflowTooltip: true },
        { prop: "created_time", label: "创建时间", width: 168, showOverflowTooltip: true },
        {
          prop: "operation",
          label: "操作",
          width: 230,
          fixed: "right",
          align: "center",
          formatter: (row: ProductTable) =>
            renderTableOperationCell(buildRowActions(row), {
              wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle",
            }),
        },
      ]),
    },
  });

const detailFormData = ref<Partial<ProductTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "产品名称", prop: "name" },
  { label: "产品规格", prop: "spec" },
  { label: "生产企业", prop: "manufacturer" },
  { label: "审核状态", prop: "audit_status", tag: { map: auditStatusMap } },
  { label: "审核意见", prop: "review_comment" },
  { label: "审核时间", prop: "reviewed_at" },
  { label: "提交人", prop: "created_by.name" },
  { label: "创建时间", prop: "created_time" },
];

const initialFormData: ProductForm = { id: undefined, name: undefined, spec: undefined, manufacturer: undefined };
const formData = ref<ProductForm>({ ...initialFormData });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const rules = reactive({
  name: [{ required: true, message: "请输入产品名称", trigger: "blur" }],
});

const formItems = computed<FormItem[]>(() => [
  {
    label: "产品名称",
    key: "name",
    type: "input",
    span: 24,
    props: { placeholder: "请输入产品名称（如 一心坦）", maxlength: 128 },
  },
  {
    label: "产品规格",
    key: "spec",
    type: "input",
    span: 24,
    props: { placeholder: "如 100mg*28片（可空）", maxlength: 128 },
  },
  {
    label: "生产企业",
    key: "manufacturer",
    type: "input",
    span: 24,
    props: { placeholder: "如 上海现代制药股份有限公司（可空）", maxlength: 255 },
  },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<ProductForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  detailApi: ProductAPI.detailProduct,
  createApi: ProductAPI.createProduct,
  updateApi: ProductAPI.updateProduct,
  titles: { create: "新增产品", update: "修改产品", detail: "产品详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
  onUpdateSuccess: refreshUpdate,
});

// ── 审核（单条 / 批量共用） ──
const auditDialog = ref<{ visible: boolean; approved: boolean; ids: number[]; review_comment: string }>({
  visible: false,
  approved: true,
  ids: [],
  review_comment: "",
});
const auditSubmitting = ref(false);

function handleOpenAudit(approved: boolean) {
  if (selectedIds.value.length === 0) return;
  auditDialog.value = { visible: true, approved, ids: [...selectedIds.value], review_comment: "" };
}

async function handleSubmitAudit() {
  const body: ProductAuditParams = {
    ids: auditDialog.value.ids,
    approved: auditDialog.value.approved,
    review_comment: auditDialog.value.review_comment || undefined,
  };
  if (!body.approved && !body.review_comment) {
    ElMessage.warning("驳回必须填写审核意见");
    return;
  }
  auditSubmitting.value = true;
  try {
    const res = await ProductAPI.auditProduct(body);
    ElMessage.success(res.data.msg || "审核完成");
    auditDialog.value.visible = false;
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshUpdate();
  } finally {
    auditSubmitting.value = false;
  }
}

async function handleSearch(params: { name?: string; manufacturer?: string; audit_status?: string }) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { name: undefined, manufacturer: undefined, audit_status: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number, name: string) {
  try {
    await confirmDelete(`确定删除产品「${name}」吗？`);
    await ProductAPI.deleteProduct([id]);
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
    await ProductAPI.deleteProduct(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}
</script>
