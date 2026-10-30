<script setup lang="ts">
import type { FormSchema, FormSchemaColumn, FormSchemaField, TaskItemDetail } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { taskDisplayName } from '@/constants'
import { useUserStore } from '@/store/userStore'
import { pcaTextArr } from 'element-china-area-data'

definePage({ name: 'market-submission-form', style: { navigationBarTitleText: '提交成果' } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()
const userStore = useUserStore()

const assignmentId = ref<number>()
const taskNo = ref('')
const formLoading = ref(false)
const formSchema = ref<FormSchema>([])

/** 三级任务（含任务专属采集字段，对齐后端 TaskItemOutSchema） */
const taskItems = ref<TaskItemDetail[]>([])

const period = ref(currentMonth())

/** 当前月份（提交月份默认值，如 2026-03） */
function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

/** 当前登录用户姓名（执行人自动填充，name 优先回退 username） */
function currentUserName() {
  return userStore.userInfo?.name ?? userStore.userInfo?.username ?? ''
}

/**
 * 完整采集表单分节：三级任务分节已自包含（含继承自模板的通用分节）。
 *  同模板下多个任务都复制了执行信息/管理核实等通用分节，按分节 code 去重只渲染一次；
 *  模板 form_schema 仅作旧数据兜底（分节 code 未被任务覆盖时补充）。
 */
interface SectionView {
  code: string
  name: string
  required?: boolean
  fields: Record<string, FormSchemaField>
}
const allSections = computed<SectionView[]>(() => {
  const sections: SectionView[] = []
  const seen = new Set<string>()
  const push = (s: { code: string, name: string, required?: boolean, fields?: Record<string, FormSchemaField> }) => {
    if (!s.code || seen.has(s.code))
      return
    seen.add(s.code)
    sections.push({ code: s.code, name: s.name, required: s.required, fields: s.fields ?? {} })
  }
  for (const task of taskItems.value) {
    for (const s of task.config?.form_schema ?? [])
      push(s)
  }
  for (const s of formSchema.value)
    push(s)
  return sections
})

/** 表单数据：按分节 code 嵌套 {分节code: {字段名: 值}}，多行子表字段值为行数组 */
const formData = reactive<Record<string, Record<string, any>>>({})

function sectionData(sectionCode: string): Record<string, any> {
  if (!formData[sectionCode])
    formData[sectionCode] = {}
  return formData[sectionCode]!
}

/** 多行子表空行：按子列定义初始化 */
function tableEmptyRow(field: FormSchemaField): Record<string, any> {
  const row: Record<string, any> = {}
  for (const col of field.columns ?? [])
    row[col.name] = ''
  return row
}

function rowsOf(sectionCode: string, fieldName: string): Record<string, any>[] {
  const v = formData[sectionCode]?.[fieldName]
  return Array.isArray(v) ? v : []
}

function addTableRow(sectionCode: string, fieldName: string, field: FormSchemaField) {
  sectionData(sectionCode)[fieldName].push(tableEmptyRow(field))
}

function removeTableRow(sectionCode: string, fieldName: string, index: number) {
  const rows = rowsOf(sectionCode, fieldName)
  if (rows.length <= 1)
    return
  rows.splice(index, 1)
}

/** 动态下拉字段选择器 */
const activeField = ref<FormSchemaField | null>(null)
const activeSectionCode = ref('')
const activeFieldName = ref('')
const showFieldPicker = ref(false)
const fieldPickerColumns = computed(() => [(activeField.value?.options ?? []).map(o => ({ value: o.value, label: o.label }))])

/** 执行日期选择器（date 字段复用同一实例）：modelValue 为毫秒时间戳 */
const datePickerVisible = ref(false)
const datePickerValue = ref<number>(Date.now())
const activeDateSectionCode = ref('')
const activeDateFieldName = ref('')

/** 区域选择器（region 字段复用同一实例）：省市区三级联动，options 使用 pcaTextArr */
const regionPickerVisible = ref(false)
const activeRegionSectionCode = ref('')
const activeRegionFieldName = ref('')

const submitting = ref(false)

function isRequired(field: FormSchemaField) {
  return field.required === true || field.autofill === 'current_user'
}

/** 动态字段是否使用选择器（select / radio） */
function usePicker(field: FormSchemaField) {
  return field.type === 'select' || field.type === 'radio' || !!field.options?.length
}

function openFieldPicker(sectionCode: string, name: string, field: FormSchemaField) {
  if (!field.options?.length)
    return
  activeField.value = field
  activeSectionCode.value = sectionCode
  activeFieldName.value = name
  showFieldPicker.value = true
}

function onFieldPickerConfirm(e: { value: Array<string | number> }) {
  if (activeSectionCode.value && activeFieldName.value)
    sectionData(activeSectionCode.value)[activeFieldName.value] = e.value[0]
  showFieldPicker.value = false
}

/** 打开日期选择器：有值回显，无值默认今天 */
function openDatePicker(sectionCode: string, name: string) {
  activeDateSectionCode.value = sectionCode
  activeDateFieldName.value = name
  const v = sectionData(sectionCode)[name]
  const ts = typeof v === 'string' && v ? parseDateStr(v) : null
  datePickerValue.value = ts ?? Date.now()
  datePickerVisible.value = true
}

/** 确认日期：时间戳转 YYYY-MM-DD 写入表单 */
function onDateConfirm(e: { value: number | string }) {
  const ts = typeof e.value === 'number' ? e.value : Number(e.value)
  if (activeDateSectionCode.value && activeDateFieldName.value && !Number.isNaN(ts))
    sectionData(activeDateSectionCode.value)[activeDateFieldName.value] = formatDateStr(ts)
  datePickerVisible.value = false
}

/** 打开区域选择器 */
function openRegionPicker(sectionCode: string, name: string) {
  activeRegionSectionCode.value = sectionCode
  activeRegionFieldName.value = name
  regionPickerVisible.value = true
}

/** 确认区域：selectedOptions 取完整路径（省/市/区），以 / 拼接写回表单 */
function onRegionConfirm(e: { value: string | number, selectedOptions: Array<{ label?: string }> }) {
  const path = (e.selectedOptions ?? []).map(o => o.label ?? '').filter(Boolean).join('/')
  if (activeRegionSectionCode.value && activeRegionFieldName.value && path)
    sectionData(activeRegionSectionCode.value)[activeRegionFieldName.value] = path
  regionPickerVisible.value = false
}

/** 时间戳 → YYYY-MM-DD */
function formatDateStr(ts: number): string {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** YYYY-MM-DD → 时间戳（非法返回 null） */
function parseDateStr(str: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str)
  if (!m)
    return null
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime()
}

function fieldLabel(field: FormSchemaField) {
  return field.label || ''
}

/** 选择类字段（date/region）占位文案，如「请选择执行日期」「请选择区域」 */
function selectPlaceholder(field: FormSchemaField): string {
  return field.placeholder || `请选择${fieldLabel(field)}`
}

function fieldValueText(sectionCode: string, name: string, field: FormSchemaField) {
  const v = sectionData(sectionCode)[name]
  if (v === undefined || v === null || v === '')
    return ''
  if (usePicker(field)) {
    const opt = field.options?.find(o => String(o.value) === String(v))
    return opt?.label ?? String(v)
  }
  return String(v)
}

/** 当前正在上传的字段（分节.字段名，防止重复上传） */
const uploadingField = ref('')

/** 解析上传响应，返回 file_url，失败提示并返回 null */
function parseUploadUrl(result: UniApp.UploadFileSuccessCallbackResult): string | null {
  try {
    const parsed = JSON.parse(result.data) as { code: number, msg?: string, data?: { file_url?: string } }
    if (parsed.code === 0 && parsed.data?.file_url)
      return parsed.data.file_url
    toast.error(parsed.msg || '上传失败')
  }
  catch {
    toast.error('上传失败')
  }
  return null
}

/** 选择并上传图片（image 字段） */
function chooseAndUploadImage(sectionCode: string, name: string) {
  const key = `${sectionCode}.${name}`
  if (uploadingField.value)
    return
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    success: async (res) => {
      const filePath = res.tempFilePaths?.[0]
      if (!filePath)
        return
      uploadingField.value = key
      try {
        const result = await MarketAPI.uploadFile(filePath)
        const url = parseUploadUrl(result)
        if (url)
          sectionData(sectionCode)[name] = url
      }
      catch {
        toast.error('上传失败')
      }
      finally {
        uploadingField.value = ''
      }
    },
  })
}

/** 选择并上传文件（file 字段） */
function chooseAndUploadFile(sectionCode: string, name: string) {
  const key = `${sectionCode}.${name}`
  if (uploadingField.value)
    return
  uni.chooseFile({
    count: 1,
    success: async (res) => {
      const tempFiles = res.tempFiles as any
      const filePath = Array.isArray(tempFiles) ? tempFiles[0]?.path : tempFiles?.path
      if (!filePath)
        return
      uploadingField.value = key
      try {
        const result = await MarketAPI.uploadFile(filePath)
        const url = parseUploadUrl(result)
        if (url)
          sectionData(sectionCode)[name] = url
      }
      catch {
        toast.error('上传失败')
      }
      finally {
        uploadingField.value = ''
      }
    },
  })
}

/** 初始化表单数据：按分节嵌套，多行子表字段初始化为首行 */
function initFormData() {
  const executorName = currentUserName()
  for (const section of allSections.value) {
    const sec = sectionData(section.code)
    for (const [fieldName, field] of Object.entries(section.fields)) {
      if (field.type === 'table')
        sec[fieldName] = [tableEmptyRow(field)]
      else if (field.autofill === 'current_user')
        sec[fieldName] = executorName
      else
        sec[fieldName] = field.type === 'number' ? undefined : ''
    }
  }
}

/** 是否空值 */
function isBlank(v: any): boolean {
  return v === undefined || v === null || v === ''
}

/** 单值必填字段缺失提示：按字段类型 / 自动填充语义措辞 */
function requiredHint(field: FormSchemaField): string {
  const label = fieldLabel(field)
  if (field.autofill === 'current_user' || field.type === 'date' || field.type === 'region' || field.type === 'select' || field.type === 'radio' || field.type === 'checkbox')
    return `请选择「${label}」`
  return `请填写「${label}」`
}

/** 子表必填列缺失提示：按列类型措辞 */
function columnRequiredHint(col: FormSchemaColumn): string {
  if (col.type === 'date' || col.type === 'select' || col.type === 'radio' || col.type === 'checkbox')
    return `请选择「${col.label}」`
  return `请填写「${col.label}」`
}

/** 校验必填：单值必填字段（含自动填充）+ 多行子表的必填列 */
function validate(): boolean {
  for (const section of allSections.value) {
    for (const [name, field] of Object.entries(section.fields)) {
      if (field.type === 'table') {
        for (const row of rowsOf(section.code, name)) {
          for (const col of field.columns ?? []) {
            if (col.required && isBlank(row[col.name])) {
              toast.warning(`「${section.name}·${field.label}」${columnRequiredHint(col)}`)
              return false
            }
          }
        }
        continue
      }
      if (isRequired(field) && isBlank(sectionData(section.code)[name])) {
        toast.warning(requiredHint(field))
        return false
      }
    }
  }
  return true
}

/** 构造提交载荷：{ assignment_id, period, form_data }，form_data 按分节嵌套；机构信息由后端从 form_data 归集 */
function buildPayload() {
  return {
    assignment_id: assignmentId.value,
    period: period.value,
    form_data: JSON.parse(JSON.stringify(formData)),
  }
}

async function handleSubmit() {
  if (!validate())
    return
  submitting.value = true
  try {
    await MarketAPI.createSubmission(buildPayload())
    toast.success(t('market.submitSuccess'))
    setTimeout(() => router.replace({ name: 'market-my-task' }), 300)
  }
  catch {
    toast.error(t('common.operationFailed'))
  }
  finally {
    submitting.value = false
  }
}

/** 直接取分派单详情：按任务粒度渲染该任务（三级任务 item / 叶子模板 template）的采集分节 */
async function loadAssignment() {
  formLoading.value = true
  try {
    const detail = await MarketAPI.getAssignmentDetail(assignmentId.value!)
    const task = detail.task
    const template = task?.template
    formSchema.value = template?.config?.form_schema ?? []
    // 三级任务粒度：仅渲染该任务的专属采集分节（自包含）；叶子模板无三级任务，回退模板分节
    taskItems.value = task?.item ? [task.item] : []
    taskNo.value = taskDisplayName(task)
  }
  catch {
    formSchema.value = []
    taskItems.value = []
    toast.error(t('common.loadFailed'))
  }
  finally {
    formLoading.value = false
  }
  initFormData()
}

onLoad((query) => {
  assignmentId.value = Number(query?.assignment_id)
  taskNo.value = query?.task_no ?? ''
  loadAssignment()
})
</script>

<template>
  <view class="page-wraper">
    <view class="px-3 py-3">
      <!-- 任务名头部 -->
      <view class="hero-card rounded-3 px-5 py-5 text-white">
        <view class="text-2.5" style="opacity: 0.85">
          {{ t('market.submitResult') }}
        </view>
        <view class="mt-2 text-4.5 font-semibold leading-snug">
          {{ taskNo || '—' }}
        </view>
      </view>

      <view class="wot-bg-filled-oppo mt-3 rounded-3 px-4 py-4">
        <wd-loading v-if="formLoading" class="my-4 block" />
        <wd-form v-if="!formLoading" :model="formData" label-position="left">
          <wd-form-item :label="t('market.period')" border>
            <view class="flex-1 flex items-center">
              <text class="text-3.5" style="color: var(--wot-text-auxiliary)">{{ period }}</text>
            </view>
          </wd-form-item>

          <!-- 采集字段：模板通用分节 + 三级任务分节，按分节分组渲染 -->
          <template v-for="section in allSections" :key="section.code">
            <view class="mb-1 mt-4 flex items-center gap-2">
              <view class="wot-bg-primary-6 h-3.5 w-1 rounded-full" />
              <text class="text-4 font-semibold" style="color: var(--wot-text-main)">
                {{ section.name }}{{ section.required ? '（必填）' : '' }}
              </text>
            </view>

            <template v-for="(field, fieldName) in section.fields" :key="fieldName">
              <!-- 多行子表字段：按子列渲染行，可增删行 -->
              <view v-if="field.type === 'table'" class="mb-2">
                <view
                  v-for="(row, rowIndex) in rowsOf(section.code, fieldName)"
                  :key="rowIndex"
                  class="wot-bg-filled-oppo mb-2 rounded-2 p-3"
                  style="border: 1rpx solid var(--wot-border-main)"
                >
                  <view class="mb-2 flex items-center justify-between">
                    <text class="text-3 font-medium" style="color: var(--wot-text-main)">
                      {{ field.label }} #{{ rowIndex + 1 }}
                    </text>
                    <text
                      v-if="rowsOf(section.code, fieldName).length > 1"
                      class="wot-text-error-main text-2.5"
                      @click="removeTableRow(section.code, fieldName, rowIndex)"
                    >
                      删除行
                    </text>
                  </view>
                  <view v-for="col in field.columns ?? []" :key="col.name" class="mb-2 last:mb-0">
                    <view class="mb-1 text-2.5" style="color: var(--wot-text-auxiliary)">
                      {{ col.label }}{{ col.required ? ' *' : '' }}
                    </view>
                    <wd-input v-model="row[col.name]" :placeholder="col.placeholder || col.label" />
                  </view>
                </view>
                <view class="py-1 text-center">
                  <wd-button size="small" type="primary" plain @click="addTableRow(section.code, fieldName, field)">
                    + {{ field.label }}
                  </wd-button>
                </view>
              </view>

              <wd-form-item v-else :label="fieldLabel(field)" border :required="isRequired(field)">
                <!-- 自动填充字段（执行人）：只读展示，弱化样式 -->
                <view v-if="field.autofill === 'current_user'" class="flex-1 flex items-center">
                  <text class="text-3.5" style="color: var(--wot-text-auxiliary)">
                    {{ fieldValueText(section.code, fieldName, field) }}
                  </text>
                </view>

                <!-- 选择类字段（select/radio/checkbox 带 options）：下拉/单选选择 -->
                <view v-else-if="usePicker(field)" class="flex-1" @click="openFieldPicker(section.code, fieldName, field)">
                  <wd-cell :value="fieldValueText(section.code, fieldName, field)" is-link :border="false" />
                </view>

                <!-- 日期字段：点击唤起日期选择器 -->
                <view v-else-if="field.type === 'date'" class="flex-1" @click="openDatePicker(section.code, fieldName)">
                  <wd-cell
                    :value="formData[section.code][fieldName] || ''"
                    :placeholder="selectPlaceholder(field)"
                    is-link
                    :border="false"
                  />
                </view>

                <!-- 区域字段：点击唤起省市区三级联动 -->
                <view v-else-if="field.type === 'region'" class="flex-1" @click="openRegionPicker(section.code, fieldName)">
                  <wd-cell
                    :value="formData[section.code][fieldName] || ''"
                    :placeholder="selectPlaceholder(field)"
                    is-link
                    :border="false"
                  />
                </view>

                <wd-input
                  v-else-if="field.type === 'textarea'"
                  v-model="formData[section.code][fieldName]"
                  type="textarea"
                  :placeholder="field.placeholder || fieldLabel(field)"
                />
                <view v-else-if="field.type === 'image'" class="flex-1" @click="chooseAndUploadImage(section.code, fieldName)">
                  <image
                    v-if="formData[section.code][fieldName]"
                    :src="formData[section.code][fieldName]"
                    mode="aspectFill"
                    class="h-40 w-40 rounded-2 object-cover"
                  />
                  <view
                    v-else
                    class="h-24 flex flex-col items-center justify-center border rounded-2 border-dashed text-2.5"
                    style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                  >
                    <view class="text-4">
                      +
                    </view>
                    <view class="mt-1">
                      {{ uploadingField === `${section.code}.${fieldName}` ? '上传中…' : '点击上传图片' }}
                    </view>
                  </view>
                </view>
                <view v-else-if="field.type === 'file'" class="flex-1" @click="chooseAndUploadFile(section.code, fieldName)">
                  <view
                    class="h-12 flex items-center justify-between border rounded-2 border-dashed px-3 text-2.5"
                    style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                  >
                    <text>{{ formData[section.code][fieldName] ? '已上传，点击重新上传' : '点击上传文件' }}</text>
                    <text style="color: var(--wot-text-auxiliary)">
                      {{ uploadingField === `${section.code}.${fieldName}` ? '上传中…' : '' }}
                    </text>
                  </view>
                </view>
                <wd-input
                  v-else
                  v-model="formData[section.code][fieldName]"
                  :type="field.type === 'number' ? 'number' : 'text'"
                  :placeholder="field.placeholder || fieldLabel(field)"
                />
              </wd-form-item>
            </template>
          </template>
        </wd-form>
        <wd-picker :visible="showFieldPicker" :columns="fieldPickerColumns" @confirm="onFieldPickerConfirm" @cancel="showFieldPicker = false" />
        <wd-datetime-picker
          v-model="datePickerValue"
          v-model:visible="datePickerVisible"
          type="date"
          title="选择日期"
          @confirm="onDateConfirm"
        />
        <wd-cascader
          v-model:visible="regionPickerVisible"
          :options="pcaTextArr"
          text-key="label"
          title="选择区域"
          @confirm="onRegionConfirm"
        />
      </view>

      <view class="mt-5">
        <wd-button block type="primary" size="large" :loading="submitting" @click="handleSubmit">
          {{ t('market.submit') }}
        </wd-button>
      </view>
      <wd-gap height="120rpx" safe-area-bottom />
    </view>
  </view>
</template>

<style lang="scss" scoped>
.hero-card {
  background: linear-gradient(135deg, var(--wot-primary-6), var(--wot-primary-4));
  box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.16);
}
</style>
