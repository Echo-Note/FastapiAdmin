<!-- 采集表单数据只读预览：按 form_data 结构分区渲染，图片/附件给缩略图与下载链接，底部保留原始 JSON -->
<template>
  <div class="fa-form-data-viewer">
    <template v-if="sections.length">
      <div v-for="section in sections" :key="section.code" class="viewer-section">
        <div class="viewer-section__title">{{ section.name }}</div>

        <!-- 多行子表：值为「对象数组」且没有全部命中 URL 时按表格渲染 -->
        <ElTable v-for="table in section.tables" :key="table.key" :data="table.rows" size="small" border class="mb-2">
          <ElTableColumn
            v-for="col in table.columns"
            :key="col"
            :label="col"
            min-width="120"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <template v-if="imageList(row[col]).length">
                <ElImage
                  v-for="(url, i) in imageList(row[col])"
                  :key="`${url}-${i}`"
                  :src="url"
                  :preview-src-list="imageList(row[col])"
                  :initial-index="i"
                  fit="cover"
                  preview-teleported
                  class="viewer-thumb"
                />
              </template>
              <template v-else-if="fileList(row[col]).length">
                <a v-for="(url, i) in fileList(row[col])" :key="`${url}-${i}`" :href="url" target="_blank" rel="noopener">
                  {{ fileName(url) }}
                </a>
              </template>
              <span v-else>{{ displayText(row[col]) }}</span>
            </template>
          </ElTableColumn>
        </ElTable>

        <!-- 单值字段：图片/附件给缩略图与链接，其余按文本/对象渲染 -->
        <div v-for="field in section.fields" :key="field.key" class="viewer-field">
          <div class="viewer-field__label">{{ field.label }}</div>
          <div class="viewer-field__value">
            <template v-if="imageList(field.value).length">
              <ElImage
                v-for="(url, i) in imageList(field.value)"
                :key="`${url}-${i}`"
                :src="url"
                :preview-src-list="imageList(field.value)"
                :initial-index="i"
                fit="cover"
                preview-teleported
                class="viewer-thumb"
              />
            </template>
            <template v-else-if="fileList(field.value).length">
              <div v-for="(url, i) in fileList(field.value)" :key="`${url}-${i}`">
                <a :href="url" target="_blank" rel="noopener">{{ fileName(url) }}</a>
              </div>
            </template>
            <pre v-else-if="isObject(field.value)" class="viewer-json">{{ displayText(field.value) }}</pre>
            <span v-else>{{ displayText(field.value) }}</span>
          </div>
        </div>

        <div v-if="!section.fields.length && !section.tables.length" class="viewer-empty">（本节无数据）</div>
      </div>
    </template>
    <div v-else class="viewer-empty">暂无采集数据</div>

    <ElCollapse v-if="sections.length" class="mt-2">
      <ElCollapseItem title="原始 JSON（排查用）" name="raw">
        <pre class="viewer-json">{{ rawText }}</pre>
      </ElCollapseItem>
    </ElCollapse>
  </div>
</template>

<script setup lang="ts">
/**
 * 采集表单数据（`form_data`）只读预览。
 *
 * 不依赖 `form_schema`：成果详情接口不返回任务 schema，因此按数据结构推断渲染形态——
 * 图片/附件按 URL 拓展名识别并渲染缩略图（点击大图预览），对象数组按子表渲染，
 * 其余按文本渲染，最后保留原始 JSON 供排查。
 *
 * 值形态兼容：单值字符串（历史数据）与字符串数组（2026-11 起多图/多附件）都按数组处理。
 */
const props = defineProps<{
  /** 按分节 code 嵌套的表单数据：{分节code: {字段名: 值}} */
  formData?: Record<string, any> | null;
  /** 分节 code → 中文名（不传则直接显示 code） */
  sectionNames?: Record<string, string>;
}>();

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$/i;

interface ViewerField {
  key: string;
  label: string;
  value: any;
}
interface ViewerTable {
  key: string;
  rows: Record<string, any>[];
  columns: string[];
}
interface ViewerSection {
  code: string;
  name: string;
  fields: ViewerField[];
  tables: ViewerTable[];
}

const isObject = (v: any) => v !== null && typeof v === "object" && !Array.isArray(v);
const isUrl = (v: any) => typeof v === "string" && /^(https?:\/\/|\/)/i.test(v);

/** 归一成数组：字符串 → 包一层；null/undefined → 空数组 */
function asList(value: any): any[] {
  if (value === null || value === undefined || value === "") return [];
  return Array.isArray(value) ? value : [value];
}

/** 图片 URL 列表（兼容历史单字符串） */
function imageList(value: any): string[] {
  return asList(value).filter((v) => isUrl(v) && IMAGE_EXT.test(String(v)));
}

/** 非图片的附件 URL 列表 */
function fileList(value: any): string[] {
  return asList(value).filter((v) => isUrl(v) && !IMAGE_EXT.test(String(v)));
}

/** 取 URL 里的文件名做链接文案 */
function fileName(url: string): string {
  const clean = String(url).split("?")[0] ?? "";
  return clean.split("/").filter(Boolean).pop() || clean;
}

/** 通用文本化：数组用「、」连接，对象走 JSON */
function displayText(value: any): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map((v) => displayText(v)).join("、");
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

const rawText = computed(() => JSON.stringify(props.formData ?? {}, null, 2));

const sections = computed<ViewerSection[]>(() => {
  const data = props.formData ?? {};
  return Object.entries(data).map(([code, raw]) => {
    const fields: ViewerField[] = [];
    const tables: ViewerTable[] = [];
    if (isObject(raw)) {
      for (const [key, value] of Object.entries(raw as Record<string, any>)) {
        // 对象数组 = 多行子表；其余都按单值字段
        if (Array.isArray(value) && value.some((row) => isObject(row))) {
          const rows = value.filter((row) => isObject(row)) as Record<string, any>[];
          const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
          tables.push({ key, rows, columns });
        } else {
          fields.push({ key, label: key, value });
        }
      }
    }
    return { code, name: props.sectionNames?.[code] ?? code, fields, tables };
  });
});
</script>

<style scoped lang="scss">
.fa-form-data-viewer {
  max-height: 60vh;
  overflow-y: auto;
}

.viewer-section {
  padding: 10px 12px;
  margin-bottom: 14px;
  border: 1px solid var(--fa-card-border, var(--el-border-color-lighter));
  border-radius: 8px;
}

.viewer-section__title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.viewer-field {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
  line-height: 22px;
}

.viewer-field__label {
  flex: 0 0 120px;
  color: var(--el-text-color-secondary);
}

.viewer-field__value {
  flex: 1;
  min-width: 0;
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.viewer-thumb {
  width: 72px;
  height: 72px;
  margin: 0 6px 6px 0;
  cursor: zoom-in;
  border-radius: 6px;
}

.viewer-json {
  margin: 0;
  font-size: 12px;
  word-break: break-all;
  white-space: pre-wrap;
}

.viewer-empty {
  padding: 8px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
