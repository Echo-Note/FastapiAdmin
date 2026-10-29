<!-- 月度报告：列表 + 手动生成 + 详情（按项目×二级模板×月份汇总） -->
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
            :perm-create="['module_market:report:create']"
            create-text="生成报告"
            @add="openGenerateDialog"
          />
        </template>
      </FaTableHeader>

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

    <!-- 生成报告对话框 -->
    <ElDialog v-model="generateVisible" title="生成报告" width="520px" :close-on-click-modal="false">
      <FaForm
        ref="generateFormRef"
        v-model="generateForm"
        :items="generateFormItems"
        :rules="generateRules"
        label-suffix=":"
        :label-width="100"
        label-position="right"
        :span="24"
        :gutter="16"
      />
      <template #footer>
        <ElButton @click="generateVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="generateSubmitting" @click="handleGenerateSubmit">生成</ElButton>
      </template>
    </ElDialog>

    <!-- 详情对话框 -->
    <ElDialog v-model="detailVisible" title="报告详情" width="720px">
      <FaDescriptions :column="4" :data="detailData" :items="detailItems">
        <template #templateName="{ value }">{{ value ?? "全项目汇总" }}</template>
      </FaDescriptions>
      <ElDivider content-position="left">汇总数据</ElDivider>
      <pre class="form-data-pre">{{ formattedSummary }}</pre>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import ReportAPI, { type ReportTable } from "@/api/module_market/report";
import ProjectAPI from "@/api/module_market/project";
import TaskTemplateAPI from "@/api/module_market/task-template";
import { useDictStore } from "@stores";
import type { SearchFormItem } from "@/components/forms/fa-search-bar/index.vue";
import type FaSearchBar from "@/components/forms/fa-search-bar/index.vue";
import type { FormItem } from "@/components/forms/fa-form/index.vue";
import FaForm from "@/components/forms/fa-form/index.vue";
import { renderTableOperationCell, resolveStatusColumns, cleanEmptyArrayParams, type TableOperationAction, type StatusType } from "@utils";
import { useFormDraft } from "@/hooks/core/useFormDraft";

defineOptions({ name: "MarketReport", inheritAttrs: false });

const dictStore = useDictStore();

// ── 字典：报告状态 ──
const reportStatusMap = computed<Record<string, { type: StatusType; text: string }>>(() =>
  Object.fromEntries(
    (dictStore.getDictData["market_report_status"] ?? []).map((d) => [
      d.dict_value!,
      { type: (d.list_class as StatusType) ?? "info", text: d.dict_label ?? d.dict_value! },
    ])
  )
);
const statusOptions = computed<OptionType[]>(() =>
  (dictStore.getDictArray("market_report_status") ?? []).map((d) => ({ value: d.dict_value, label: d.dict_label }))
);

const searchForm = ref<{ project_id?: number; template_id?: number; period?: string; status?: string }>({ project_id: undefined, template_id: undefined, period: undefined, status: undefined });
const showSearchBar = ref(true);
const searchBarRef = ref<InstanceType<typeof FaSearchBar> | null>(null);

const projectOptions = ref<OptionType[]>([]);
const templateOptions = ref<OptionType[]>([]);

const searchItems = computed<SearchFormItem[]>(() => [
  { label: "项目", key: "project_id", type: "select", props: { placeholder: "请选择项目", options: projectOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "二级模板", key: "template_id", type: "select", props: { placeholder: "请选择模板", options: templateOptions.value, filterable: true, clearable: true }, span: 6 },
  { label: "月份", key: "period", type: "input", placeholder: "如 2026-03", clearable: true, span: 6 },
  { label: "状态", key: "status", type: "select", props: { placeholder: "请选择状态", options: statusOptions.value, clearable: true }, span: 6 },
]);

const faTableRef = ref<{ elTableRef?: { clearSelection: () => void } } | null>(null);

const opCtx = {
  onDetail: (id: number) => void openDetail(id),
};

function buildRowActions(row: ReportTable): TableOperationAction[] {
  return [{ key: "detail", label: "详情", artType: "view", perm: "module_market:report:query", run: () => opCtx.onDetail(row.id!) }];
}

const { columns, columnChecks, data, loading, pagination, getData, replaceSearchParams, resetSearchParams, handleSizeChange, handleCurrentChange, refreshData } =
  useTable({
    core: {
      apiFn: ReportAPI.listReport,
      apiParams: { page_no: 1, page_size: 10 },
      columnsFactory: resolveStatusColumns<ReportTable>(() => [
        { type: "globalIndex", width: 56, label: "序号" },
        { prop: "project", label: "项目", minWidth: 150, formatter: (row: ReportTable) => row.project?.name ?? "—" },
        { prop: "template", label: "二级模板", minWidth: 150, formatter: (row: ReportTable) => row.template?.name ?? "全项目汇总" },
        { prop: "period", label: "月份", width: 90 },
        { prop: "status", label: "状态", width: 92, status: reportStatusMap.value },
        { prop: "attachment", label: "附件", minWidth: 140, showOverflowTooltip: true, formatter: (row: ReportTable) => row.attachment ?? "—" },
        { prop: "created_time", label: "生成时间", width: 168, showOverflowTooltip: true },
        { prop: "operation", label: "操作", width: 90, fixed: "right", align: "center", formatter: (row: ReportTable) => renderTableOperationCell(buildRowActions(row), { wrapperClass: "inline-flex flex-wrap items-center justify-end gap-1 align-middle" }) },
      ]),
    },
  });

const detailVisible = ref(false);
const detailData = ref<Partial<ReportTable>>({});
const detailItems: import("@/components/display/fa-descriptions/index.vue").DescriptionsItem[] = [
  { label: "项目", prop: "project.name" },
  { label: "二级模板", prop: "template.name", slot: "templateName" },
  { label: "月份", prop: "period" },
  { label: "状态", prop: "status", tag: { map: reportStatusMap.value } },
  { label: "附件", prop: "attachment" },
  { label: "生成时间", prop: "created_time" },
];

const formattedSummary = computed(() => (detailData.value.summary ? JSON.stringify(detailData.value.summary, null, 2) : "—"));

async function openDetail(id: number) {
  const res = await ReportAPI.detailReport(id);
  detailData.value = res.data.data;
  detailVisible.value = true;
}

// ── 生成报告 ──
const generateVisible = ref(false);
const generateSubmitting = ref(false);
const generateFormRef = ref<InstanceType<typeof FaForm> | null>(null);
const generateForm = ref<{ project_id?: number; template_id?: number; period?: string }>({ project_id: undefined, template_id: undefined, period: undefined });

const generateFormItems = computed<FormItem[]>(() => [
  { label: "项目", key: "project_id", type: "select", span: 24, props: { placeholder: "请选择项目", options: projectOptions.value, filterable: true } },
  { label: "二级模板", key: "template_id", type: "select", span: 24, props: { placeholder: "留空则汇总整个项目", options: templateOptions.value, filterable: true, clearable: true } },
  { label: "月份", key: "period", type: "input", span: 24, props: { placeholder: "自然月，如 2026-03", maxlength: 16 } },
]);

const generateRules = reactive({
  project_id: [{ required: true, message: "请选择项目", trigger: "change" }],
  period: [{ required: true, message: "请输入月份", trigger: "blur" }],
});

const generateDraft = useFormDraft({
  key: "report",
  dialogVisible: generateVisible,
  form: generateForm,
  blank: () => ({ project_id: undefined, template_id: undefined, period: undefined }),
});

function openGenerateDialog() {
  generateDraft.openCreate();
}

async function handleGenerateSubmit() {
  if (!generateFormRef.value) return;
  try {
    await generateFormRef.value.validate();
  } catch {
    return;
  }
  if (!generateForm.value.project_id || !generateForm.value.period) return;
  generateSubmitting.value = true;
  try {
    await ReportAPI.generateReport({ project_id: generateForm.value.project_id, template_id: generateForm.value.template_id, period: generateForm.value.period });
    generateDraft.done();
    generateVisible.value = false;
    await refreshData();
  } catch {
    // 错误已由拦截器提示
  } finally {
    generateSubmitting.value = false;
  }
}

async function loadOptions() {
  const [projectRes, templateRes] = await Promise.all([
    ProjectAPI.listProject({ page_no: 1, page_size: 100 }),
    TaskTemplateAPI.listTemplate({ page_no: 1, page_size: 100 }),
  ]);
  projectOptions.value = projectRes.data.data.items.map((p) => ({ value: p.id!, label: p.name ?? p.code ?? "" }));
  templateOptions.value = templateRes.data.data.items.map((t) => ({ value: t.id!, label: t.name ?? t.code ?? "" }));
}

onMounted(async () => {
  await dictStore.getDict(["market_report_status"]);
  await loadOptions();
});

async function handleSearch(params: Record<string, unknown>) {
  replaceSearchParams(cleanEmptyArrayParams({ ...params }) as Record<string, unknown>);
  await getData();
}

async function onResetSearch() {
  searchForm.value = { project_id: undefined, template_id: undefined, period: undefined, status: undefined };
  await resetSearchParams();
}
</script>

<style scoped>
.form-data-pre {
  margin: 0;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  max-height: 300px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
