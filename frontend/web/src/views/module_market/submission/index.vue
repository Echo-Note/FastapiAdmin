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
      <FaFormDataViewer :form-data="detailData.form_data" :schema="detailData.form_schema" />
    </ElDialog>

    <!-- 审核对话框 -->
    <ElDialog v-model="reviewVisible" title="成果审核" width="720px" :close-on-click-modal="false">
      <FaDescriptions :column="4" :data="reviewData" :items="reviewSummaryItems">
        <template #subjectType="{ row }"><component :is="dictTag('market_subject_type', row?.subject_type)" /></template>
        <template #statusTag="{ row }"><component :is="dictTag('market_submission_status', row?.status)" /></template>
      </FaDescriptions>
      <ElDivider content-position="left">采集数据</ElDivider>
      <FaFormDataViewer :form-data="reviewData.form_data" :schema="reviewData.form_schema" />
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
import { ElMessage, ElMessageBox } from "element-plus";
import SubmissionAPI, { type SubmissionReviewResult, type SubmissionTable } from "@/api/module_market/submission";
import UserAPI from "@/api/module_system/user";
import ProjectAPI from "@/api/module_market/project";
import TaskTemplateAPI from "@/api/module_market/task-template";
import TaskItemAPI, { type TaskItemTable } from "@/api/module_market/task-item";
import { useDictStore } from "@stores";
import StatusTag from "@/components/display/fa-status-tag/index.vue";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";

defineOptions({ name: "MarketSubmission", inheritAttrs: false });

const dictStore = useDictStore();
const route = useRoute();
const router = useRouter();

/** 深链：运营工作台「待办队列」点进来时带 ?status=PENDING，直接只看待审核 */
const initialStatus = typeof route.query.status === "string" ? route.query.status : undefined;

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

const searchForm = ref<{
  archive_no?: string;
  project_id?: number;
  template_id?: number;
  item_id?: number;
  user_id?: number;
  period?: string;
  status?: string;
}>({ status: initialStatus });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const userOptions = ref<OptionType[]>([]);
const userMap = ref<Record<number, string>>({});
const projectOptions = ref<OptionType[]>([]);
const templateOptions = ref<OptionType[]>([]);
const itemOptions = ref<Array<OptionType & { templateId?: number }>>([]);

/** 任务（三级任务）按当前选中的模板缩小可选范围，没选模板则列全部 */
const templateItemOptions = computed<OptionType[]>(() => {
  const templateId = searchForm.value.template_id;
  if (!templateId) return itemOptions.value;
  return itemOptions.value.filter((item) => item.templateId === templateId);
});
const searchItems = computed<SearchFormItem[]>(() => [
  { label: "档案号", key: "archive_no", type: "input", props: { placeholder: "请输入档案号", clearable: true }, span: 6 },
  { label: "项目", key: "project_id", type: "select", props: { placeholder: "请选择项目", options: projectOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "任务模板", key: "template_id", type: "select", props: { placeholder: "请选择任务模板", options: templateOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "任务", key: "item_id", type: "select", props: { placeholder: "请选择任务", options: templateItemOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "提交人", key: "user_id", type: "select", props: { placeholder: "请选择提交人", options: userOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "提交月份", key: "period", type: "date", props: { type: "month", format: "YYYY-MM", placeholder: "请选择提交月份" }, span: 6 },
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
      apiParams: { page_no: 1, page_size: 10, ...(initialStatus ? { status: initialStatus } : {}) },
      columnsFactory: () => [
        { type: "globalIndex", width: 56, label: "序号", fixed: "left" },
        { prop: "project_name", label: "项目", minWidth: 110, showOverflowTooltip: true, formatter: (row: SubmissionTable) => row.task?.project_name ?? "—" },
        { prop: "category_name", label: "分类", minWidth: 130, showOverflowTooltip: true, formatter: (row: SubmissionTable) => row.task?.category_name ?? "—" },
        { prop: "template_name", label: "任务模板", minWidth: 130, showOverflowTooltip: true, formatter: (row: SubmissionTable) => row.task?.template_name ?? "—" },
        { prop: "item_name", label: "任务", minWidth: 130, showOverflowTooltip: true, formatter: (row: SubmissionTable) => row.task?.item_name ?? "—" },
        { prop: "task_no", label: "任务编号", width: 110, formatter: (row: SubmissionTable) => row.task?.task_no ?? "—" },
        // 采集对象合并「机构名 / 受访对象名」，非机构对象不再整列为空
        { prop: "subject_name", label: "采集对象", minWidth: 150, showOverflowTooltip: true, formatter: (row: SubmissionTable) => row.institution?.name ?? row.subject_name ?? "—" },
        { prop: "subject_type", label: "对象类型", width: 100, formatter: (row: SubmissionTable) => dictTag("market_subject_type", row.subject_type) },
        { prop: "region", label: "区域", width: 150, showOverflowTooltip: true },
        { prop: "user_id", label: "提交人", width: 110, formatter: (row: SubmissionTable) => userMap.value[row.user_id!] ?? `#${row.user_id}` },
        { prop: "archive_no", label: "档案号", width: 110, showOverflowTooltip: true },
        { prop: "period", label: "提交月份", width: 100 },
        { prop: "status", label: "状态", width: 92, formatter: (row: SubmissionTable) => dictTag("market_submission_status", row.status) },
        { prop: "created_time", label: "提交时间", width: 168, showOverflowTooltip: true },
        // 列设置里可打开：驳回重提的版本号、一期恒空的 AI 预检
        { prop: "version", label: "版本", width: 70, align: "center", visible: false },
        { prop: "ai_check_status", label: "AI 校验", width: 100, visible: false, formatter: (row: SubmissionTable) => row.ai_check_status ?? "—" },
        { prop: "operation", label: "操作", width: 140, fixed: "right", align: "center", formatter: (row: SubmissionTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ],
    },
  });

// ── 详情 ──
const detailVisible = ref(false);
const detailData = ref<Partial<SubmissionTable>>({});

const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "项目", prop: "task.project_name" },
  { label: "分类", prop: "task.category_name" },
  { label: "任务模板", prop: "task.template_name" },
  { label: "任务", prop: "task.item_name" },
  { label: "任务编号", prop: "task.task_no" },
  { label: "采集对象", prop: "subject_name" },
  { label: "对象类型", prop: "subject_type", slot: "subjectType" },
  { label: "区域", prop: "region" },
  { label: "档案号", prop: "archive_no" },
  { label: "提交人", prop: "user_id" },
  { label: "提交月份", prop: "period" },
  { label: "状态", prop: "status", slot: "statusTag" },
  { label: "版本", prop: "version" },
  { label: "AI 校验状态", prop: "ai_check_status" },
  { label: "提交时间", prop: "created_time" },
  { label: "审核人", prop: "reviewer_id" },
  { label: "审核时间", prop: "reviewed_at" },
  { label: "审核意见", prop: "review_comment", span: 4 },
];

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
  { label: "项目", prop: "task.project_name" },
  { label: "分类", prop: "task.category_name" },
  { label: "任务模板", prop: "task.template_name" },
  { label: "任务", prop: "task.item_name" },
  { label: "任务编号", prop: "task.task_no" },
  { label: "采集对象", prop: "subject_name" },
  { label: "对象类型", prop: "subject_type", slot: "subjectType" },
  { label: "区域", prop: "region" },
  { label: "档案号", prop: "archive_no" },
  { label: "提交人", prop: "user_id" },
  { label: "提交月份", prop: "period" },
  { label: "状态", prop: "status", slot: "statusTag" },
  { label: "版本", prop: "version" },
  { label: "提交时间", prop: "created_time" },
];

const reviewFormItems: FormItem[] = [
  { label: "审核结论", key: "approved", type: "radiogroup", span: 24, props: { options: [{ label: "通过", value: true }, { label: "驳回", value: false }] } },
  { label: "审核意见", key: "review_comment", type: "input", span: 24, props: { type: "textarea", rows: 3, maxlength: 200, showWordLimit: true, placeholder: "请填写审核意见（驳回时建议填写原因）" } },
];

const reviewRules = reactive({ approved: [{ required: true, message: "请选择审核结论", trigger: "change" }] });

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

  // 二次提醒：通过即自动归集结算，这一步会真的产生结算单与实发金额，不能误点
  if (reviewForm.value.approved) {
    try {
      await ElMessageBox.confirm(
        `审核通过后将立即归集结算：按任务单价 × 本月已通过成果数，计入该用户「${reviewData.value.period ?? "本月"}」的应发金额，并受其当月发放额度封顶。确定通过吗？`,
        "确认通过并归集结算",
        { type: "warning", confirmButtonText: "通过并归集", cancelButtonText: "再看看" },
      );
    } catch {
      return; // 用户取消，不提交审核
    }
  }

  reviewSubmitting.value = true;
  let outcome: SubmissionReviewResult | undefined;
  try {
    const res = await SubmissionAPI.reviewSubmission(reviewData.value.id, {
      approved: reviewForm.value.approved,
      review_comment: reviewForm.value.review_comment,
    });
    outcome = res.data.data;
    reviewVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    reviewSubmitting.value = false;
  }
  if (outcome) await showReviewOutcome(outcome);
}

/** 归集结果提示：给出本次归集的应发/实发/滚存，可一键跳去结算单；归集失败只提示原因（审核已生效） */
async function showReviewOutcome(outcome: SubmissionReviewResult) {
  if (outcome.warning) {
    ElMessage.warning(outcome.warning);
    return;
  }
  const notice = outcome.settlement;
  if (!notice) return;
  const amount = (value?: number) => Number(value ?? 0).toFixed(2);
  try {
    await ElMessageBox.alert(
      `<div style="line-height:1.9;font-size:13px">
        <div>结算月份：<b>${notice.period}</b></div>
        <div>本任务应发：<b>￥${amount(notice.payable)}</b></div>
        <div>该用户当月实发：<b>￥${amount(notice.paid)}</b>（当月发放额度 ￥${amount(notice.limit)}）</div>
        <div>滚入下月津贴：<b>￥${amount(notice.rollover)}</b></div>
      </div>`,
      "归集结算完成",
      {
        dangerouslyUseHTMLString: true,
        type: "success",
        confirmButtonText: "查看结算单",
        showCancelButton: true,
        cancelButtonText: "关闭",
      },
    );
    await router.push({ path: "/market/settlement", query: { task_id: String(notice.task_id ?? "") } });
  } catch {
    // 点「关闭」不跳转
  }
}

async function loadOptions() {
  const [userRes, projectRes, templateRes, items] = await Promise.all([
    UserAPI.listUser({ page_no: 1, page_size: 100 }),
    ProjectAPI.listProject({ page_no: 1, page_size: 100 }),
    TaskTemplateAPI.listTemplate({ page_no: 1, page_size: 100 }),
    loadAllTaskItems(),
  ]);
  userOptions.value = userRes.data.data.items.map((u) => ({ value: u.id!, label: `${u.name ?? u.username ?? ""}` }));
  userMap.value = Object.fromEntries(userRes.data.data.items.map((u) => [u.id!, u.name ?? u.username ?? ""]));
  projectOptions.value = projectRes.data.data.items.map((p) => ({ value: p.id!, label: p.name ?? `#${p.id}` }));
  templateOptions.value = templateRes.data.data.items.map((t) => ({ value: t.id!, label: t.name ?? `#${t.id}` }));
  // 任务选项记住所属模板，供「选了模板只列该模板的任务」过滤
  itemOptions.value = items.map((i) => ({ value: i.id!, label: i.name ?? `#${i.id}`, templateId: i.template_id }));
}

/** 三级任务可能超过一页（page_size 上限 100），按 has_next 取完，避免下拉漏项 */
async function loadAllTaskItems() {
  const all: Array<TaskItemTable> = [];
  for (let pageNo = 1; pageNo <= 10; pageNo += 1) {
    const res = await TaskItemAPI.listItem({ page_no: pageNo, page_size: 100 });
    all.push(...res.data.data.items);
    if (!res.data.data.has_next) break;
  }
  return all;
}

onMounted(async () => {
  await dictStore.getDict(["market_submission_status", "market_subject_type"]);
  await loadOptions();
});

// 首次进入由 useTable 的 immediate 自动取数，initialStatus 已写进 apiParams；
// 页面被 KeepAlive 缓存后，再用不同 ?status= 点进来不会重挂载，这里跟上 URL 变化
watch(
  () => route.query.status,
  async (next) => {
    const status = typeof next === "string" ? next : undefined;
    if (!status || status === searchForm.value.status) return;
    searchForm.value.status = status;
    replaceSearchParams({ status });
    await getData();
  }
);

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { status: undefined };
  await resetSearchParams();
}

// 切换模板时清掉不再可选的「任务」，避免选出模板+任务的矛盾组合
watch(
  () => searchForm.value.template_id,
  (templateId) => {
    if (!templateId || !searchForm.value.item_id) return;
    if (!templateItemOptions.value.some((item) => item.value === searchForm.value.item_id)) {
      searchForm.value.item_id = undefined;
    }
  }
);
</script>

<style scoped>
</style>
