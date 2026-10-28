<!-- 成果审核：列表 + 详情 + 通过/驳回 -->
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
      <FaTableHeader v-model:columns="columnChecks" v-model:showSearchBar="showSearchBar" :loading="loading" @refresh="refreshData" />

      <FaTable
        ref="faTableRef"
        :loading="loading"
        :data="data"
        :columns="columns"
        :pagination="pagination"
        @pagination:size-change="handleSizeChange"
        @pagination:current-change="handleCurrentChange"
      />
    </ElCard>

    <!-- 详情对话框 -->
    <ElDialog v-model="detailVisible" title="成果详情" width="720px">
      <FaDescriptions :column="4" :data="detailData" :items="detailItems" max-height="60vh">
        <template #subjectType="{ row }"><component :is="dictTag('market_subject_type', row?.subject_type)" /></template>
        <template #statusTag="{ row }"><component :is="dictTag('market_submission_status', row?.status)" /></template>
      </FaDescriptions>
      <ElDivider content-position="left">采集数据</ElDivider>
      <pre class="form-data-pre">{{ formattedFormData }}</pre>
    </ElDialog>

    <!-- 审核对话框 -->
    <ElDialog v-model="reviewVisible" title="成果审核" width="720px" :close-on-click-modal="false">
      <FaDescriptions :column="4" :data="reviewData" :items="reviewSummaryItems">
        <template #subjectType="{ row }"><component :is="dictTag('market_subject_type', row?.subject_type)" /></template>
        <template #statusTag="{ row }"><component :is="dictTag('market_submission_status', row?.status)" /></template>
      </FaDescriptions>
      <ElDivider content-position="left">采集数据</ElDivider>
      <pre class="form-data-pre">{{ formattedReviewFormData }}</pre>
      <ElDivider content-position="left">审核意见</ElDivider>
      <FaForm
        ref="reviewFormRef"
        v-model="reviewForm"
        :items="reviewFormItems"
        :rules="reviewRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="reviewVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="reviewSubmitting" @click="handleReviewSubmit">提交审核</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import { h } from "vue";
import SubmissionAPI, { type SubmissionTable } from "@/api/module_market/submission";
import UserAPI from "@/api/module_system/user";
import { useDictStore } from "@stores";
import StatusTag from "@/components/display/fa-status-tag/index.vue";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketSubmission", inheritAttrs: false });

const dictStore = useDictStore();

const statusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_submission_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

/** 用字典渲染状态标签（实时查 dict_label + list_class，避免字典异步加载导致空 map 快照） */
function dictTag(dictType: string, val?: unknown) {
  const strVal = typeof val === "string" ? val : undefined;
  if (!strVal) return "—";
  const item = dictStore.getDictLabel(dictType, strVal);
  if (typeof item === "string") return h(StatusTag, { type: "info" as StatusType, label: item });
  return h(StatusTag, { type: (item.list_class as StatusType) ?? "info", label: item.dict_label ?? strVal });
}

const searchForm = ref<{ assignment_id?: number; user_id?: number; status?: string }>({ assignment_id: undefined, user_id: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "分派ID", key: "assignment_id", type: "number", props: { placeholder: "请输入分派ID", controlsPosition: "right" }, span: 6 },
  { label: "用户", key: "user_id", type: "select", props: { placeholder: "请选择用户", options: userOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

function buildRowActions(row: SubmissionTable): TableOperationAction[] {
  const actions: TableOperationAction[] = [
    { key: "detail", label: "详情", artType: "view", perm: "module_market:submission:query", run: () => void openDetail(row.id!) },
  ];
  if (row.status === "PENDING") {
    actions.push({ key: "review", label: "审核", artType: "edit", perm: "module_market:submission:review", run: () => void openReview(row.id!) });
  }
  return actions;
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: SubmissionAPI.listSubmission,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: () => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "institution", label: "机构", minWidth: 150, formatter: (row: SubmissionTable) => row.institution?.name ?? row.subject_name ?? "—" },
        { prop: "subject_type", label: "对象类型", width: 100, formatter: (row: SubmissionTable) => dictTag("market_subject_type", row.subject_type) },
        { prop: "user_id", label: "用户", minWidth: 120, formatter: (row: SubmissionTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "region", label: "区域", width: 110, showOverflowTooltip: true },
        { prop: "archive_no", label: "档案号", width: 120, showOverflowTooltip: true },
        { prop: "period", label: "提交月份", width: 100 },
        { prop: "status", label: "状态", width: 92, formatter: (row: SubmissionTable) => dictTag("market_submission_status", row.status) },
        { prop: "version", label: "版本", width: 70, align: "center" },
        { prop: "ai_check_status", label: "AI 校验", width: 100, formatter: (row: SubmissionTable) => row.ai_check_status ?? "—" },
        { prop: "created_time", label: "提交时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 140, fixed: "right", align: "center", formatter: (row: SubmissionTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ],
    },
  });

// ── 详情 ──
const detailVisible = ref(false);
const detailData = ref<Partial<SubmissionTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "机构", prop: "institution.name" },
  { label: "对象名称", prop: "subject_name" },
  { label: "对象类型", prop: "subject_type", slot: "subjectType" },
  { label: "区域", prop: "region" },
  { label: "档案号", prop: "archive_no" },
  { label: "提交月份", prop: "period" },
  { label: "状态", prop: "status", slot: "statusTag" },
  { label: "版本", prop: "version" },
  { label: "AI 校验状态", prop: "ai_check_status" },
  { label: "提交时间", prop: "created_time" },
  { label: "审核人", prop: "reviewer_id" },
  { label: "审核时间", prop: "reviewed_at" },
  { label: "审核意见", prop: "review_comment", span: 4 },
];

const formattedFormData = computed(() => (detailData.value.form_data ? JSON.stringify(detailData.value.form_data, null, 2) : "—"));

async function openDetail(id: number) {
  const res = await SubmissionAPI.detailSubmission(id);
  detailData.value = res.data.data;
  detailVisible.value = true;
}

// ── 审核 ──
const reviewVisible = ref(false);
const reviewSubmitting = ref(false);
const reviewData = ref<Partial<SubmissionTable>>({});
const reviewFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const reviewForm = ref<{ approved: boolean; review_comment?: string }>({ approved: true, review_comment: undefined });

const reviewSummaryItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "机构", prop: "institution.name" },
  { label: "对象名称", prop: "subject_name" },
  { label: "对象类型", prop: "subject_type", slot: "subjectType" },
  { label: "区域", prop: "region" },
  { label: "档案号", prop: "archive_no" },
  { label: "提交月份", prop: "period" },
  { label: "状态", prop: "status", slot: "statusTag" },
  { label: "版本", prop: "version" },
  { label: "AI 校验", prop: "ai_check_status" },
  { label: "提交时间", prop: "created_time" },
];

const reviewFormItems: FormItem[] = [
  { label: "审核结论", key: "approved", type: "radiogroup", span: 24, props: { options: [{ label: "通过", value: true }, { label: "驳回", value: false }] } },
  { label: "审核意见", key: "review_comment", type: "input", span: 24, props: { type: "textarea", rows: 3, maxlength: 200, showWordLimit: true, placeholder: "请填写审核意见（驳回时建议填写原因）" } },
];

const reviewRules = reactive({ approved: [{ required: true, message: "请选择审核结论", trigger: "change" }] });

const formattedReviewFormData = computed(() => (reviewData.value.form_data ? JSON.stringify(reviewData.value.form_data, null, 2) : "—"));

async function openReview(id: number) {
  const res = await SubmissionAPI.detailSubmission(id);
  reviewData.value = res.data.data;
  reviewForm.value = { approved: true, review_comment: undefined };
  reviewVisible.value = true;
}

async function handleReviewSubmit() {
  if (!reviewFormRef.value || !reviewData.value.id) return;
  try {
    await reviewFormRef.value.validate();
  } catch {
    return;
  }
  reviewSubmitting.value = true;
  try {
    await SubmissionAPI.reviewSubmission(reviewData.value.id, { approved: reviewForm.value.approved, review_comment: reviewForm.value.review_comment });
    reviewVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    reviewSubmitting.value = false;
  }
}

async function loadOptions() {
  const userRes = await UserAPI.listUser({ page_no: 1, page_size: 100 });
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
}

onMounted(async () => {
  await dictStore.getDict(["market_submission_status", "market_subject_type"]);
  await loadOptions();
});

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { assignment_id: undefined, user_id: undefined, status: undefined };
  await resetSearchParams();
}
</script>

<style scoped>
.form-data-pre {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  max-height: 260px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
