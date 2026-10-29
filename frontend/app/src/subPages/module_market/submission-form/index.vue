<script setup lang="ts">
import type { FormSchema, FormSchemaField, TaskItemConfig } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'

definePage({ name: 'market-submission-form', style: { navigationBarTitleText: '提交成果' } })

const { t } = useI18n()
const toast = useToast()
const router = useRouter()

const assignmentId = ref<number>()
const taskNo = ref('')
const formLoading = ref(false)
const formSchema = ref<FormSchema>([])

/** 三级任务（含任务专属采集字段） */
interface TaskItemView {
  code: string
  name: string
  config?: TaskItemConfig | null
}
const taskItems = ref<TaskItemView[]>([])

const period = ref(currentMonth())

/** 当前月份（提交月份默认值，如 2026-03） */
function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

/** 完整采集表单分节：三级任务分节已自包含（含继承自模板的通用分节）。
 *  同模板下多个任务都复制了执行信息/管理核实等通用分节，按分节 code 去重只渲染一次；
 *  模板 form_schema 仅作旧数据兜底（分节 code 未被任务覆盖时补充）。 */
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

const submitting = ref(false)

function isRequired(field: FormSchemaField) {
  return field.required === true
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

function fieldLabel(field: FormSchemaField) {
  return field.label || ''
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
  for (const section of allSections.value) {
    const sec = sectionData(section.code)
    for (const [fieldName, field] of Object.entries(section.fields)) {
      if (field.type === 'table')
        sec[fieldName] = [tableEmptyRow(field)]
      else
        sec[fieldName] = field.type === 'number' ? undefined : ''
    }
  }
}

/** 校验必填：单值必填字段 + 多行子表的必填列 */
function validate(): boolean {
  for (const section of allSections.value) {
    for (const [name, field] of Object.entries(section.fields)) {
      if (field.type === 'table') {
        for (const row of rowsOf(section.code, name)) {
          for (const col of field.columns ?? []) {
            if (col.required && (row[col.name] === undefined || row[col.name] === null || row[col.name] === '')) {
              toast.warning(`${section.name}·${field.label} 的「${col.label}」为必填项`)
              return false
            }
          }
        }
        continue
      }
      const v = sectionData(section.code)[name]
      if (isRequired(field) && (v === undefined || v === null || v === '')) {
        toast.warning(`${fieldLabel(field)} 为必填项`)
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

/** 从「我的任务」现取分派实例以获取 form_schema 与三级任务 */
async function loadAssignment() {
  formLoading.value = true
  try {
    const res = await MarketAPI.getMyAssignments({ page_no: 1, page_size: 100 })
    const list = (res as any).items as Array<{ id?: number; task_no?: string; task?: { name?: string; template?: { config?: { form_schema?: FormSchema } | null; items?: TaskItemView[] | null } | null } | null }> ?? []
    const found = list.find(i => String(i.id) === String(assignmentId.value))
    formSchema.value = found?.task?.template?.config?.form_schema ?? []
    taskItems.value = found?.task?.template?.items ?? []
    taskNo.value = found?.task?.name ?? found?.task_no ?? ''
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
      <wd-cell-group border custom-class="rounded-2! overflow-hidden">
        <wd-cell :title="taskNo || '提交成果'" :value="t('market.submitResult')" />
      </wd-cell-group>

      <view class="mt-3 rounded-2 bg-white p-4">
        <wd-loading v-if="formLoading" class="my-4 block" />
        <wd-form v-if="!formLoading" :model="formData" label-position="left">
          <wd-form-item :label="t('market.period')" required border>
            <wd-input v-model="period" :placeholder="t('market.period')" />
          </wd-form-item>

          <!-- 采集字段：模板通用分节 + 三级任务分节，按分节分组渲染 -->
          <template v-for="section in allSections" :key="section.code">
            <view class="mt-3 mb-1 flex items-center gap-2">
              <view class="h-3 w-1 rounded-full bg-blue-500" />
              <text class="text-sm font-semibold text-gray-800">{{ section.name }}{{ section.required ? '（必填）' : '' }}</text>
            </view>

            <template v-for="(field, fieldName) in section.fields" :key="fieldName">
              <!-- 多行子表字段：按子列渲染行，可增删行 -->
              <view v-if="field.type === 'table'" class="mb-2">
                <view v-for="(row, rowIndex) in rowsOf(section.code, fieldName)" :key="rowIndex" class="mb-2 rounded-lg bg-gray-50 p-2">
                  <view class="mb-1 flex items-center justify-between">
                    <text class="text-xs text-gray-500">{{ field.label }} #{{ rowIndex + 1 }}</text>
                    <text v-if="rowsOf(section.code, fieldName).length > 1" class="text-xs text-red-500" @click="removeTableRow(section.code, fieldName, rowIndex)">删除行</text>
                  </view>
                  <view v-for="col in field.columns ?? []" :key="col.name" class="mb-2 flex items-center gap-2">
                    <text class="w-20 shrink-0 text-xs text-gray-600">{{ col.label }}</text>
                    <input v-model="row[col.name]" class="flex-1 rounded bg-white px-2 py-1 text-sm" :placeholder="col.label || ''">
                  </view>
                </view>
                <view class="text-center">
                  <text class="text-xs text-blue-500" @click="addTableRow(section.code, fieldName, field)">+ 添加一行</text>
                </view>
              </view>

              <wd-form-item v-else :label="fieldLabel(field)" border :required="isRequired(field)">
                <view v-if="usePicker(field)" class="flex-1" @click="openFieldPicker(section.code, fieldName, field)">
                  <wd-cell :value="fieldValueText(section.code, fieldName, field)" is-link :border="false" />
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
                  <view v-else class="flex h-24 items-center justify-center rounded-2 bg-gray-50 text-sm text-gray-400">
                    {{ uploadingField === `${section.code}.${fieldName}` ? '上传中…' : '点击上传图片' }}
                  </view>
                </view>
                <view v-else-if="field.type === 'file'" class="flex-1" @click="chooseAndUploadFile(section.code, fieldName)">
                  <view class="flex h-12 items-center justify-between rounded-2 bg-gray-50 px-3 text-sm">
                    <text class="text-gray-600">{{ formData[section.code][fieldName] ? '已上传，点击重新上传' : '点击上传文件' }}</text>
                    <text class="text-gray-400">{{ uploadingField === `${section.code}.${fieldName}` ? '上传中…' : '' }}</text>
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
      </view>

      <view class="mt-4">
        <wd-button block type="primary" :loading="submitting" @click="handleSubmit">
          {{ t('market.submit') }}
        </wd-button>
      </view>
      <wd-gap height="100rpx" safe-area-bottom />
    </view>
  </view>
</template>
