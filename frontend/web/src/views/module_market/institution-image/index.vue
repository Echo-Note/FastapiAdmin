<!-- 机构图片归集：图片预览 + 机构筛选 + 按机构归集查看 -->
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
        <FaDescriptions :column="4" :data="detailFormData" :items="detailItems" max-height="70vh">
          <template #submission_id="{ value }">
            <span v-if="value != null">#{{ value }}</span>
            <span v-else>—</span>
          </template>
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
import InstitutionImageAPI, { type InstitutionImageForm, type InstitutionImageTable } from "@/api/module_market/institution-image";
import InstitutionAPI from "@/api/module_market/institution";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { ElImage } from "element-plus";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction } from "@utils";

defineOptions({ name: "MarketInstitutionImage", inheritAttrs: false });

// ── 机构选项（筛选 + 表单共用） ──
const institutionOptions = ref<OptionType[]>([]);

const searchForm = ref<{ institution_id?: number; category?: string; period?: string }>({ institution_id: undefined, category: undefined, period: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "所属机构", key: "institution_id", type: "select", props: { placeholder: "请选择机构", options: institutionOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "图片分类", key: "category", type: "input", placeholder: "如 门头照/内景照/打卡照", clearable: true, span: 6 },
  { label: "提交月份", key: "period", type: "input", placeholder: "如 2026-03", clearable: true, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);
const { selectedIds, batchDeleting, onTableSelectionChange } = useTableSelection<InstitutionImageTable>();

const opCtx = {
  onDetail: (id: number) => void handleOpenDialog("detail", id),
  onDelete: deleteRow,
};

function buildRowActions(row: InstitutionImageTable): TableOperationAction[] {
  return [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:institution:query", run: () => opCtx.onDetail(row.id!) },
    { key: "delete", label: "删除", artType: "delete", perm: "module_market:institution:delete", run: () => opCtx.onDelete(row.id!) },
  ];
}

/** 图片预览单元格（ElImage 缩略图 + 点击放大预览） */
function renderImageCell(row: InstitutionImageTable) {
  return h(ElImage, {
    src: row.image_url ?? "",
    fit: "cover",
    class: "institution-image-cell",
    style: "width: 56px; height: 56px; border-radius: 6px;",
    "preview-src-list": row.image_url ? [row.image_url] : [],
    "preview-teleported": true,
    "hide-on-click-modal": true,
  });
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData, refreshCreate, refreshRemove } =
  useTable({
    core: {
      apiFn: InstitutionImageAPI.listImage,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<InstitutionImageTable>(() => [
        { type: "selection", width: 48, fixed: "left" },
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "image_url", label: "图片", width: 90, align: "center", formatter: (row: InstitutionImageTable) => renderImageCell(row) },
        { prop: "institution", label: "所属机构", minWidth: 160, showOverflowTooltip: true, formatter: (row: InstitutionImageTable) => row.institution?.name ?? "—" },
        { prop: "category", label: "图片分类", width: 120, showOverflowTooltip: true },
        { prop: "period", label: "提交月份", width: 100, showOverflowTooltip: true },
        { prop: "submission_id", label: "来源成果", width: 100, formatter: (row: InstitutionImageTable) => (row.submission_id != null ? `#${row.submission_id}` : "—") },
        { prop: "created_time", label: "上传时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 140, fixed: "right", align: "center", formatter: (row: InstitutionImageTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailFormData = ref<Partial<InstitutionImageTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "所属机构", prop: "institution.name" },
  { label: "图片分类", prop: "category" },
  { label: "提交月份", prop: "period" },
  { label: "来源成果", prop: "submission_id", slot: "submission_id" },
  { label: "上传时间", prop: "created_time" },
];

const formData = ref<InstitutionImageForm>({ id: undefined, institution_id: undefined, submission_id: undefined, image_url: undefined, category: undefined, period: undefined });
const { dialogVisible } = useCrudDialog();
const dataFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const formRenderKey = ref(0);

const initialFormData: InstitutionImageForm = { id: undefined, institution_id: undefined, submission_id: undefined, image_url: undefined, category: undefined, period: undefined };

const rules = reactive({
  institution_id: [{ required: true, message: "请选择所属机构", trigger: "change" }],
  image_url: [{ required: true, message: "请上传图片", trigger: "change" }],
});

const formItems = computed<FormItem[]>(() => [
  { label: "所属机构", key: "institution_id", type: "select", span: 24, props: { placeholder: "请选择机构", options: institutionOptions.value, filterable: true } },
  { label: "图片", key: "image_url", type: "imageupload", span: 24, props: { accept: "image/*", maxFileSize: 10, showTip: true, tipText: "支持 image/* 格式，文件大小不超过 10MB", style: { width: "160px", height: "160px" } } },
  { label: "图片分类", key: "category", type: "input", span: 24, props: { placeholder: "如 门头照 / 内景照 / 打卡照", maxlength: 64 } },
  { label: "提交月份", key: "period", type: "input", span: 24, props: { placeholder: "如 2026-03", maxlength: 16 } },
]);

const { submitLoading, handleCloseDialog, handleOpenDialog, handleSubmit } = useCrudForm<InstitutionImageForm>({
  formData,
  initialFormData,
  dialogVisible,
  dataFormRef,
  formRenderKey,
  cacheKey: "institution-image",
  detailApi: InstitutionImageAPI.detailImage,
  createApi: InstitutionImageAPI.createImage,
  titles: { create: "新增机构图片", detail: "机构图片详情" },
  detailFormData,
  onCreateSuccess: refreshCreate,
});

async function handleAdd() {
  await handleOpenDialog("create");
}

async function handleSearch(params: { institution_id?: number; category?: string; period?: string }) {
  const cleaned = cleanEmptyArrayParams({ ...params }) as { institution_id?: number; category?: string; period?: string };
  replaceSearchParams(cleaned as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { institution_id: undefined, category: undefined, period: undefined };
  await resetSearchParams();
}

async function deleteRow(id: number) {
  try {
    await confirmDelete("确定删除该图片吗？");
    await InstitutionImageAPI.deleteImage([id]);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return;
  try {
    await confirmBatchDelete(selectedIds.value.length, selectedIds.value.map((id) => String(id)));
    batchDeleting.value = true;
    await InstitutionImageAPI.deleteImage(selectedIds.value);
    faTableRef.value?.elTableRef?.clearSelection();
    await refreshRemove();
  } catch {
    // 用户取消
  } finally {
    batchDeleting.value = false;
  }
}

async function loadInstitutions() {
  try {
    const res = await InstitutionAPI.listInstitution({ page_no: 1, page_size: 100 });
    institutionOptions.value = (res.data.data?.items ?? []).map((i) => ({ value: i.id!, label: i.name ?? "" }));
  } catch {
    institutionOptions.value = [];
  }
}

onMounted(() => loadInstitutions());
</script>

<style scoped>
:deep(.institution-image-cell .el-image__inner) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
