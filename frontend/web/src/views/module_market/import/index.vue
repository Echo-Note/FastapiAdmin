<!-- 成果导入：结算单导入（对内/对外自动识别）+ 报告附件关联 -->
<template>
  <div class="fa-full-height import-center">
    <ElTabs v-model="activeTab" class="import-tabs">
      <!-- 结算单导入 -->
      <ElTabPane label="结算单导入" name="settlement">
        <ElCard shadow="never" class="import-card">
          <ElForm :model="settlementForm" label-position="right" label-width="96px" class="import-form">
            <ElFormItem label="结算周期" required>
              <ElInput v-model="settlementForm.period" placeholder="自然月，如 2026-10" clearable class="period-input" />
            </ElFormItem>
            <ElFormItem label="结算单文件" required>
              <ElUpload
                v-model:file-list="settlementFileList"
                class="w-full"
                drag
                multiple
                accept=".xlsx"
                :auto-upload="false"
                :limit="10"
                :on-exceed="handleSettlementExceed"
              >
                <ElIcon class="el-icon--upload"><UploadFilled /></ElIcon>
                <div class="el-upload__text">将对内 / 对外结算单拖到此处，或 <em>点击选择</em>（可多选）</div>
                <template #tip>
                  <div class="el-upload__tip">支持 .xlsx，文件名需符合约定（对内：`序号.地区-省平台项目结算单-地区姓名.xlsx`；对外：`公司名-产品-服务项目结算单.xlsx`），系统自动识别。</div>
                </template>
              </ElUpload>
            </ElFormItem>
            <ElFormItem>
              <ElButton type="primary" :loading="settlementSubmitting" :disabled="!settlementFileList.length" @click="handleSettlementImport">
                开始导入
              </ElButton>
            </ElFormItem>
          </ElForm>

          <!-- 导入结果 -->
          <template v-if="settlementResult">
            <ElDivider content-position="left">导入结果</ElDivider>
            <div class="stat-grid">
              <div v-for="item in statItems" :key="item.label" class="stat-item">
                <div class="stat-value">{{ settlementResult[item.key] ?? 0 }}</div>
                <div class="stat-label">{{ item.label }}</div>
              </div>
            </div>
            <ElAlert v-if="settlementResult.errors.length" :title="`跳过 ${settlementResult.errors.length} 条`" type="warning" :closable="false" class="result-alert">
              <ul class="error-list">
                <li v-for="(err, i) in settlementResult.errors" :key="i">{{ err }}</li>
              </ul>
            </ElAlert>
          </template>
        </ElCard>
      </ElTabPane>

      <!-- 报告附件关联 -->
      <ElTabPane label="报告附件关联" name="report">
        <ElCard shadow="never" class="import-card">
          <ElForm :model="reportForm" label-position="right" label-width="96px" class="import-form">
            <ElFormItem label="服务项目号" required>
              <ElInputNumber v-model="reportForm.serviceNo" :min="1" :max="37" :step="1" controls-position="right" class="service-input" />
            </ElFormItem>
            <ElFormItem label="报告周期" required>
              <ElInput v-model="reportForm.period" placeholder="自然月，如 2026-10" clearable class="period-input" />
            </ElFormItem>
            <ElFormItem label="报告文件" required>
              <ElUpload
                v-model:file-list="reportFileList"
                class="w-full"
                drag
                accept=".pptx"
                :auto-upload="false"
                :limit="1"
                :on-exceed="handleReportExceed"
              >
                <ElIcon class="el-icon--upload"><UploadFilled /></ElIcon>
                <div class="el-upload__text">将分析报告拖到此处，或 <em>点击选择</em>（单份 pptx）</div>
                <template #tip>
                  <div class="el-upload__tip">支持 .pptx，将作为对应服务项目报告的附件关联。</div>
                </template>
              </ElUpload>
            </ElFormItem>
            <ElFormItem>
              <ElButton type="primary" :loading="reportSubmitting" :disabled="!reportFileList.length" @click="handleReportLink">
                关联附件
              </ElButton>
            </ElFormItem>
          </ElForm>
        </ElCard>
      </ElTabPane>
    </ElTabs>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import type { UploadRawFile, UploadUserFile } from "element-plus";
import ImportAPI, { type ImportResult } from "@/api/module_market/import";

defineOptions({ name: "MarketImport", inheritAttrs: false });

/** 当前自然月（结算周期默认值） */
function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const activeTab = ref("settlement");

// ── 结算单导入 ──
const settlementForm = ref<{ period: string }>({ period: currentMonth() });
const settlementFileList = ref<UploadUserFile[]>([]);
const settlementSubmitting = ref(false);
const settlementResult = ref<ImportResult | null>(null);

const statItems: { label: string; key: keyof ImportResult }[] = [
  { label: "新增公司", key: "company_created" },
  { label: "新增用户", key: "user_created" },
  { label: "新增任务", key: "task_created" },
  { label: "新增分派", key: "assignment_created" },
  { label: "新增结算", key: "settlement_created" },
  { label: "新增报告", key: "report_created" },
];

function handleSettlementExceed() {
  ElMessage.warning("单次最多上传 10 个结算单文件");
}

async function handleSettlementImport() {
  if (!settlementForm.value.period.trim()) {
    ElMessage.warning("请填写结算周期");
    return;
  }
  const files = settlementFileList.value.map((f) => f.raw).filter((f): f is UploadRawFile => Boolean(f));
  if (!files.length) {
    ElMessage.warning("请选择结算单文件");
    return;
  }
  settlementSubmitting.value = true;
  try {
    const res = await ImportAPI.importSettlement(files, settlementForm.value.period.trim());
    settlementResult.value = res.data.data;
    settlementFileList.value = [];
    ElMessage.success("结算单导入完成");
  } catch {
    // 错误已由拦截器提示
  } finally {
    settlementSubmitting.value = false;
  }
}

// ── 报告附件关联 ──
const reportForm = ref<{ serviceNo: number; period: string }>({ serviceNo: 1, period: currentMonth() });
const reportFileList = ref<UploadUserFile[]>([]);
const reportSubmitting = ref(false);

function handleReportExceed() {
  ElMessage.warning("每次仅可关联一份报告附件");
}

async function handleReportLink() {
  if (!reportForm.value.serviceNo || !reportForm.value.period.trim()) {
    ElMessage.warning("请填写服务项目号与报告周期");
    return;
  }
  const file = reportFileList.value[0]?.raw as File | undefined;
  if (!file) {
    ElMessage.warning("请选择报告文件");
    return;
  }
  reportSubmitting.value = true;
  try {
    await ImportAPI.linkReport(file, reportForm.value.serviceNo, reportForm.value.period.trim());
    reportFileList.value = [];
    ElMessage.success("报告附件关联成功");
  } catch {
    // 错误已由拦截器提示
  } finally {
    reportSubmitting.value = false;
  }
}
</script>

<style scoped>
.import-center {
  padding: 16px;
  overflow: auto;
}

.import-tabs {
  max-width: 880px;
}

.import-card {
  border-radius: 8px;
}

.import-form {
  max-width: 640px;
}

.period-input,
.service-input {
  max-width: 240px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
  padding: 16px 8px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.stat-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--el-color-primary);
  line-height: 1.2;
}

.stat-label {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.result-alert {
  margin-top: 4px;
}

.error-list {
  margin: 8px 0 0;
  padding-left: 18px;
  max-height: 200px;
  overflow: auto;
  line-height: 1.7;
  font-size: 12px;
}
</style>
