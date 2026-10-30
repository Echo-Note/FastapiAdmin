<script setup lang="ts">
import type { FormSchema, FormSchemaColumn, FormSchemaField, ProductCandidate, TaskItemDetail } from '@/api/module_market'
import { onLoad } from '@dcloudio/uni-app'
import { pcaTextArr } from 'element-china-area-data'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { MarketAPI } from '@/api/module_market'
import { taskDisplayName } from '@/constants'
import { useUserStore } from '@/store/userStore'

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

/**
 * 取值目标：单值字段（rowIndex=null）与子表某行的某一列（rowIndex 有值）共用同一套改写器，
 * 避免 select/date/region 三套选择器各写一遍「单值 vs 列」分支。
 */
interface ValueTarget {
  sectionCode: string
  /** 子表字段名（单值字段与写入键同名） */
  fieldName: string
  /** 写入的具体键：单值字段=字段名；子表列=列名 */
  key: string
  /** 子表行下标，null 表示单值字段 */
  rowIndex: number | null
}

function singleTarget(sectionCode: string, name: string): ValueTarget {
  return { sectionCode, fieldName: name, key: name, rowIndex: null }
}

function columnTarget(sectionCode: string, fieldName: string, rowIndex: number, key: string): ValueTarget {
  return { sectionCode, fieldName, key, rowIndex }
}

function targetValue(target: ValueTarget | null): any {
  if (!target)
    return ''
  if (target.rowIndex === null)
    return sectionData(target.sectionCode)[target.key]
  return rowsOf(target.sectionCode, target.fieldName)[target.rowIndex]?.[target.key] ?? ''
}

function setTargetValue(target: ValueTarget | null, value: any) {
  if (!target)
    return
  if (target.rowIndex === null) {
    sectionData(target.sectionCode)[target.key] = value
    return
  }
  const row = rowsOf(target.sectionCode, target.fieldName)[target.rowIndex]
  if (row)
    row[target.key] = value
}

/** 选项选择器：单值字段（select/radio）与子表 select/radio 列共用 */
const optionTarget = ref<ValueTarget | null>(null)
const optionItems = ref<{ label: string, value: string }[]>([])
const optionPickerVisible = ref(false)
const optionPickerColumns = computed(() => [optionItems.value.map(o => ({ value: o.value, label: o.label }))])

function openOptionPicker(target: ValueTarget, options: { label: string, value: string }[] = []) {
  if (!options.length)
    return
  optionTarget.value = target
  optionItems.value = options
  optionPickerVisible.value = true
}

function onOptionConfirm(e: { value: Array<string | number> }) {
  setTargetValue(optionTarget.value, e.value[0])
  optionPickerVisible.value = false
}

/** 日期选择器：单值 date 字段与子表 date 列共用（modelValue 为毫秒时间戳） */
const dateTarget = ref<ValueTarget | null>(null)
const datePickerVisible = ref(false)
const datePickerValue = ref<number>(Date.now())

/** 打开日期选择器：有值回显，无值默认今天 */
function openDatePicker(target: ValueTarget) {
  dateTarget.value = target
  const v = targetValue(target)
  const ts = typeof v === 'string' && v ? parseDateStr(v) : null
  datePickerValue.value = ts ?? Date.now()
  datePickerVisible.value = true
}

/** 确认日期：时间戳转 YYYY-MM-DD 写入目标 */
function onDateConfirm(e: { value: number | string }) {
  const ts = typeof e.value === 'number' ? e.value : Number(e.value)
  if (!Number.isNaN(ts))
    setTargetValue(dateTarget.value, formatDateStr(ts))
  datePickerVisible.value = false
}

/** 区域选择器（region 字段）：省市区三级联动，options 使用 pcaTextArr */
const regionTarget = ref<ValueTarget | null>(null)
const regionPickerVisible = ref(false)

function openRegionPicker(target: ValueTarget) {
  regionTarget.value = target
  regionPickerVisible.value = true
}

/** 确认区域：selectedOptions 取完整路径（省/市/区），以 / 拼接写回目标 */
function onRegionConfirm(e: { value: string | number, selectedOptions: Array<{ label?: string }> }) {
  const path = (e.selectedOptions ?? []).map(o => o.label ?? '').filter(Boolean).join('/')
  if (path)
    setTargetValue(regionTarget.value, path)
  regionPickerVisible.value = false
}

const submitting = ref(false)

function isRequired(field: FormSchemaField) {
  return field.required === true || field.autofill === 'current_user'
}

/** 动态字段是否使用选择器（select / radio） */
function usePicker(field: FormSchemaField) {
  return field.type === 'select' || field.type === 'radio' || !!field.options?.length
}

/** 子表列是否使用选项选择器 */
function useColumnPicker(col: FormSchemaColumn) {
  return col.type === 'select' || col.type === 'radio' || !!col.options?.length
}

/** 子表列值的展示文案（select 列展示选项 label） */
function columnValueText(col: FormSchemaColumn, value: any) {
  if (value === undefined || value === null || value === '')
    return ''
  if (useColumnPicker(col))
    return col.options?.find(o => String(o.value) === String(value))?.label ?? String(value)
  return String(value)
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

/**
 * 产品库联想：产品名称列（product_role=name）停顿 500ms 或失焦后检索产品库。
 * 命中 1 条直接回填同行的规格与生产企业；命中多条（同名多厂商/多规格）弹半屏列表让用户选。
 * 未命中则保留用户手填的内容，提交时后端会把库里没有的产品自动入库为待审。
 */
interface ProductCellContext {
  row: Record<string, any>
  columns: FormSchemaColumn[]
  /** 产品名称列的键（检索关键词的来源） */
  nameKey: string
}

/** 构造产品列上下文（模板里对 product_role=name 的列调用） */
function productCell(row: Record<string, any>, columns: FormSchemaColumn[], nameKey: string): ProductCellContext {
  return { row, columns, nameKey }
}

/** 该列是否是产品名称列（带 product_role=name 才启用联想） */
function isProductNameColumn(col: FormSchemaColumn) {
  return col.product_role === 'name'
}

const PRODUCT_SEARCH_DEBOUNCE = 500

const productCandidates = ref<ProductCandidate[]>([])
const productPickerVisible = ref(false)
/** 正在检索的行 / 刚匹配成功的行：按行对象身份判断，避免所有行共用同一条提示 */
const productSearchingRow = ref<Record<string, any> | null>(null)
const productMatchedRow = ref<Record<string, any> | null>(null)
let productTarget: ProductCellContext | null = null
let productTimer: ReturnType<typeof setTimeout> | null = null
// 检索序号：丢弃过期响应（用户连续输入时只认最后一次）
let productSearchSeq = 0

/** 子表里产品库某角色对应的列名（如 spec → product_spec） */
function productColumnName(columns: FormSchemaColumn[], role: 'spec' | 'manufacturer'): string | null {
  return columns.find(c => c.product_role === role)?.name ?? null
}

/** 用候选回填同行的规格/生产企业（候选里为空的值不覆盖用户已填内容） */
function fillProductRow(ctx: ProductCellContext, candidate: ProductCandidate) {
  const specKey = productColumnName(ctx.columns, 'spec')
  const manufacturerKey = productColumnName(ctx.columns, 'manufacturer')
  if (specKey && candidate.spec)
    ctx.row[specKey] = candidate.spec
  if (manufacturerKey && candidate.manufacturer)
    ctx.row[manufacturerKey] = candidate.manufacturer
}

/** 检索产品库：single 命中直接回填，多命中交给用户选择 */
async function searchProductLibrary(ctx: ProductCellContext, keyword: string, autoFill: boolean) {
  const kw = (keyword ?? '').trim()
  if (!kw) {
    productCandidates.value = []
    return
  }
  const seq = ++productSearchSeq
  productSearchingRow.value = ctx.row
  try {
    const list = await MarketAPI.searchProducts(kw)
    if (seq !== productSearchSeq)
      return
    const matched = (list ?? []).filter(item => item.name === kw)
    const candidates = matched.length ? matched : (list ?? [])
    if (!candidates.length) {
      productMatchedRow.value = null
      return
    }
    if (autoFill && candidates.length === 1) {
      fillProductRow(ctx, candidates[0]!)
      productMatchedRow.value = ctx.row
      toast.success('已从产品库填充规格与生产企业')
      return
    }
    productMatchedRow.value = null
    productTarget = ctx
    productCandidates.value = candidates
    productPickerVisible.value = true
  }
  catch {
    // 检索失败不打扰用户，继续手填即可
  }
  finally {
    if (seq === productSearchSeq)
      productSearchingRow.value = null
  }
}

/** 产品名称输入：重置 500ms 防抖后检索 */
function onProductNameInput(ctx: ProductCellContext) {
  if (productTimer)
    clearTimeout(productTimer)
  productTimer = setTimeout(() => {
    productTimer = null
    void searchProductLibrary(ctx, String(ctx.row[ctx.nameKey] ?? ''), true)
  }, PRODUCT_SEARCH_DEBOUNCE)
}

/** 产品名称失焦：立刻检索（与停顿检索合并为同一入口） */
function onProductNameBlur(ctx: ProductCellContext, value: any) {
  if (productTimer) {
    clearTimeout(productTimer)
    productTimer = null
  }
  void searchProductLibrary(ctx, String(value ?? ''), true)
}

/** 产品名称列旁的「库」按钮：立即检索并总是列出候选（便于同名多厂商时手动挑） */
function onProductNameSearchTap(ctx: ProductCellContext, value: any) {
  if (productTimer) {
    clearTimeout(productTimer)
    productTimer = null
  }
  void searchProductLibrary(ctx, String(value ?? ''), false)
}

/** 弹窗选中候选：回填并关闭 */
function onProductCandidatePick(candidate: ProductCandidate) {
  if (productTarget)
    fillProductRow(productTarget, candidate)
  productPickerVisible.value = false
  productCandidates.value = []
  productTarget = null
  toast.success('已填充规格与生产企业')
}

/** 当前正在上传的目标（防止重复上传） */
const uploadingKey = ref('')

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

/** 单个图片/附件字段最多保存的份数（微信 chooseImage 单次上限也是 9） */
const MAX_UPLOAD_COUNT = 9

/**
 * 归一成 URL 数组：历史数据是单个字符串（`"url"`），2026-11 起多图/多附件存字符串数组。
 * 渲染与校验都走这里，因此老成果也能照常显示。
 */
function asUrlList(value: any): string[] {
  if (value === null || value === undefined || value === '')
    return []
  if (Array.isArray(value))
    return value.filter((v): v is string => typeof v === 'string' && !!v)
  return typeof value === 'string' ? [value] : []
}

/** 该字段还能再传几份 */
function remainingSlots(value: any): number {
  return Math.max(0, MAX_UPLOAD_COUNT - asUrlList(value).length)
}

/** 追加一份 URL 到目标（保留已有图片/附件，多图是累加而不是覆盖） */
function appendUrl(target: ValueTarget, url: string) {
  setTargetValue(target, [...asUrlList(targetValue(target)), url])
}

/** 删除目标里第 index 份图片/附件 */
function removeUrlAt(target: ValueTarget, index: number) {
  const list = asUrlList(targetValue(target))
  list.splice(index, 1)
  setTargetValue(target, list)
}

/** 上传单个文件并追加到目标（单值字段与子表列共用） */
async function uploadInto(target: ValueTarget, filePath: string, key: string) {
  uploadingKey.value = key
  try {
    const result = await MarketAPI.uploadFile(filePath)
    const url = parseUploadUrl(result)
    if (url)
      appendUrl(target, url)
  }
  catch {
    toast.error('上传失败')
  }
  finally {
    uploadingKey.value = ''
  }
}

/** 顺序上传多个文件（并发会让 uploadingKey 互相覆盖，故串行） */
async function uploadMany(target: ValueTarget, filePaths: string[], key: string) {
  for (const filePath of filePaths)
    await uploadInto(target, filePath, key)
}

/** 选择并上传图片（image 字段 / 子表 image 列）：支持多选，最多累计 9 张 */
function chooseAndUploadImage(target: ValueTarget, key: string) {
  if (uploadingKey.value)
    return
  const remaining = remainingSlots(targetValue(target))
  if (remaining <= 0) {
    toast.warning(`最多上传 ${MAX_UPLOAD_COUNT} 张图片`)
    return
  }
  uni.chooseImage({
    count: remaining,
    sizeType: ['compressed'],
    success: (res) => {
      // 各端类型声明不一致（string | string[]），统一成数组再过滤空值
      const picked = res.tempFilePaths ?? []
      const filePaths = (Array.isArray(picked) ? picked : [picked]).filter(Boolean) as string[]
      if (filePaths.length)
        void uploadMany(target, filePaths, key)
    },
  })
}

/** 选择并上传文件（file 字段 / 子表 file 列）：逐个追加，最多累计 9 份 */
function chooseAndUploadFile(target: ValueTarget, key: string) {
  if (uploadingKey.value)
    return
  if (remainingSlots(targetValue(target)) <= 0) {
    toast.warning(`最多上传 ${MAX_UPLOAD_COUNT} 个附件`)
    return
  }
  uni.chooseFile({
    count: 1,
    success: (res) => {
      const tempFiles = res.tempFiles as any
      const filePath = Array.isArray(tempFiles) ? tempFiles[0]?.path : tempFiles?.path
      if (filePath)
        void uploadInto(target, filePath, key)
    },
  })
}

/** 附件展示名：取路径最后一段 */
function fileNameOf(url: string): string {
  const clean = String(url).split('?')[0] ?? ''
  return clean.split('/').filter(Boolean).pop() || clean
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

/**
 * 本地草稿自动保存：用户填了一半刷新页面 / 退出小程序后再进来，已填内容还在。
 *
 * 不占用后端成果状态（提交即 PENDING），草稿只存在本机 storage，按分派维度隔离；
 * 提交成功后清掉。读取失败（数据损坏/结构变更）时静默丢弃，不影响正常填写。
 */
const DRAFT_STORAGE_PREFIX = 'market-submission-draft:'
/** 草稿恢复完成前不写存储，避免用初始空值覆盖已保存内容 */
const draftReady = ref(false)
let draftTimer: ReturnType<typeof setTimeout> | null = null

function draftStorageKey(): string | null {
  return assignmentId.value ? `${DRAFT_STORAGE_PREFIX}${assignmentId.value}` : null
}

/** 恢复本地草稿：按分节/字段覆盖已初始化的表单（只覆盖草稿里确实存在的键） */
function restoreDraft() {
  const key = draftStorageKey()
  if (!key)
    return
  try {
    const raw = uni.getStorageSync(key)
    if (!raw)
      return
    const saved = JSON.parse(typeof raw === 'string' ? raw : JSON.stringify(raw)) as Record<string, Record<string, any>>
    for (const [sectionCode, fields] of Object.entries(saved ?? {})) {
      if (!fields || typeof fields !== 'object')
        continue
      Object.assign(sectionData(sectionCode), fields)
    }
    toast.success('已恢复上次未提交的内容')
  }
  catch {
    // 草稿损坏就当没有，不影响填写
    uni.removeStorageSync(key)
  }
}

/** 落盘当前表单内容（失败静默，草稿不影响主流程） */
function persistDraft() {
  const key = draftStorageKey()
  if (!key || !draftReady.value)
    return
  try {
    uni.setStorageSync(key, JSON.stringify(formData))
  }
  catch {
    // 存储满了/不可用时忽略
  }
}

function clearDraft() {
  const key = draftStorageKey()
  if (key)
    uni.removeStorageSync(key)
  draftReady.value = false
}

/** 表单变更后 800ms 防抖落盘 */
watch(
  formData,
  () => {
    if (!draftReady.value)
      return
    if (draftTimer)
      clearTimeout(draftTimer)
    draftTimer = setTimeout(() => {
      draftTimer = null
      persistDraft()
    }, 800)
  },
  { deep: true },
)

/** 是否空值 */
function isBlank(v: any): boolean {
  if (v === undefined || v === null || v === '')
    return true
  // 多图/多附件：空数组同样视为未填
  return Array.isArray(v) && v.length === 0
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
    // 已提交成功：本地草稿没有保留价值，清掉避免下次进来看到旧内容
    clearDraft()
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
  restoreDraft()
  draftReady.value = true
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
            <view class="flex flex-1 items-center">
              <text class="text-3.5" style="color: var(--wot-text-auxiliary)">
                {{ period }}
              </text>
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

                    <!-- 选项类列（select/radio 带 options）：唤起选项选择器 -->
                    <wd-cell
                      v-if="useColumnPicker(col)"
                      :value="columnValueText(col, row[col.name])"
                      :placeholder="`请选择${col.label}`"
                      is-link
                      :border="false"
                      @click="openOptionPicker(columnTarget(section.code, fieldName, rowIndex, col.name), col.options)"
                    />
                    <!-- 日期列：唤起日期选择器 -->
                    <wd-cell
                      v-else-if="col.type === 'date'"
                      :value="row[col.name] || ''"
                      :placeholder="`请选择${col.label}`"
                      is-link
                      :border="false"
                      @click="openDatePicker(columnTarget(section.code, fieldName, rowIndex, col.name))"
                    />
                    <!-- 图片列：上传后回显缩略图 -->
                    <view v-else-if="col.type === 'image'" class="flex flex-wrap items-start gap-2">
                      <view
                        v-for="(url, imgIndex) in asUrlList(row[col.name])"
                        :key="`${url}-${imgIndex}`"
                        class="relative"
                      >
                        <image :src="url" mode="aspectFill" class="h-24 w-24 rounded-2 object-cover" />
                        <view
                          class="absolute right-0 top-0 h-5 w-5 flex items-center justify-center rounded-full text-3 text-white"
                          style="background: rgba(0, 0, 0, 0.55)"
                          @click.stop="removeUrlAt(columnTarget(section.code, fieldName, rowIndex, col.name), imgIndex)"
                        >
                          ×
                        </view>
                      </view>
                      <view
                        v-if="remainingSlots(row[col.name]) > 0"
                        class="h-24 w-24 flex flex-col items-center justify-center border rounded-2 border-dashed text-2.5"
                        style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                        @click="chooseAndUploadImage(columnTarget(section.code, fieldName, rowIndex, col.name), `${section.code}.${fieldName}.${rowIndex}.${col.name}`)"
                      >
                        <view class="text-4">
                          +
                        </view>
                        <view class="mt-1">
                          {{ uploadingKey === `${section.code}.${fieldName}.${rowIndex}.${col.name}` ? '上传中…' : `已 ${asUrlList(row[col.name]).length}/${MAX_UPLOAD_COUNT}` }}
                        </view>
                      </view>
                    </view>
                    <!-- 文件列 -->
                    <view v-else-if="col.type === 'file'" class="flex flex-col gap-1">
                      <view
                        v-for="(url, fileIndex) in asUrlList(row[col.name])"
                        :key="`${url}-${fileIndex}`"
                        class="flex items-center justify-between rounded-2 px-2 py-1 text-2.5"
                        style="border: 1rpx solid var(--wot-border-main)"
                      >
                        <text class="flex-1 truncate" style="color: var(--wot-text-main)">
                          {{ fileNameOf(url) }}
                        </text>
                        <text class="wot-text-error-main ml-2" @click.stop="removeUrlAt(columnTarget(section.code, fieldName, rowIndex, col.name), fileIndex)">
                          删除
                        </text>
                      </view>
                      <view
                        v-if="remainingSlots(row[col.name]) > 0"
                        class="h-10 flex items-center justify-center border rounded-2 border-dashed text-2.5"
                        style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                        @click="chooseAndUploadFile(columnTarget(section.code, fieldName, rowIndex, col.name), `${section.code}.${fieldName}.${rowIndex}.${col.name}`)"
                      >
                        {{ uploadingKey === `${section.code}.${fieldName}.${rowIndex}.${col.name}` ? '上传中…' : `+ 添加附件（${asUrlList(row[col.name]).length}/${MAX_UPLOAD_COUNT}）` }}
                      </view>
                    </view>
                    <!-- 数字列：数字键盘 -->
                    <wd-input
                      v-else-if="col.type === 'number'"
                      v-model="row[col.name]"
                      type="number"
                      :placeholder="col.placeholder || `请输入${col.label}`"
                    />
                    <!-- 备注类列：多行 -->
                    <wd-input
                      v-else-if="col.type === 'textarea'"
                      v-model="row[col.name]"
                      type="textarea"
                      :placeholder="col.placeholder || `请输入${col.label}`"
                    />
                    <!-- 产品名称列：输入即联想产品库，命中后回填规格与生产企业 -->
                    <view v-else-if="isProductNameColumn(col)">
                      <wd-input
                        v-model="row[col.name]"
                        :placeholder="col.placeholder || `请输入${col.label}（可联想产品库）`"
                        @input="onProductNameInput(productCell(row, field.columns ?? [], col.name))"
                        @blur="onProductNameBlur(productCell(row, field.columns ?? [], col.name), row[col.name])"
                      />
                      <view class="mt-1 flex items-center justify-between text-2.5">
                        <text style="color: var(--wot-text-auxiliary)">
                          {{
                            productMatchedRow === row
                              ? '已从产品库填充规格与生产企业'
                              : productSearchingRow === row
                                ? '正在查询产品库…'
                                : '输入产品名称可自动带出规格与生产企业'
                          }}
                        </text>
                        <text
                          style="color: var(--wot-primary-6)"
                          @click="onProductNameSearchTap(productCell(row, field.columns ?? [], col.name), row[col.name])"
                        >
                          查产品库
                        </text>
                      </view>
                    </view>
                    <!-- 其余文本列 -->
                    <wd-input v-else v-model="row[col.name]" :placeholder="col.placeholder || `请输入${col.label}`" />
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
                <view v-if="field.autofill === 'current_user'" class="flex flex-1 items-center">
                  <text class="text-3.5" style="color: var(--wot-text-auxiliary)">
                    {{ fieldValueText(section.code, fieldName, field) }}
                  </text>
                </view>

                <!-- 选择类字段（select/radio/checkbox 带 options）：下拉/单选选择 -->
                <view v-else-if="usePicker(field)" class="flex-1" @click="openOptionPicker(singleTarget(section.code, fieldName), field.options)">
                  <wd-cell :value="fieldValueText(section.code, fieldName, field)" is-link :border="false" />
                </view>

                <!-- 日期字段：点击唤起日期选择器 -->
                <view v-else-if="field.type === 'date'" class="flex-1" @click="openDatePicker(singleTarget(section.code, fieldName))">
                  <wd-cell
                    :value="formData[section.code][fieldName] || ''"
                    :placeholder="selectPlaceholder(field)"
                    is-link
                    :border="false"
                  />
                </view>

                <!-- 区域字段：点击唤起省市区三级联动 -->
                <view v-else-if="field.type === 'region'" class="flex-1" @click="openRegionPicker(singleTarget(section.code, fieldName))">
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
                <view v-else-if="field.type === 'image'" class="flex-1">
                  <view class="flex flex-wrap items-start gap-2">
                    <view
                      v-for="(url, imgIndex) in asUrlList(formData[section.code][fieldName])"
                      :key="`${url}-${imgIndex}`"
                      class="relative"
                    >
                      <image :src="url" mode="aspectFill" class="h-40 w-40 rounded-2 object-cover" />
                      <view
                        class="absolute right-0 top-0 h-6 w-6 flex items-center justify-center rounded-full text-3 text-white"
                        style="background: rgba(0, 0, 0, 0.55)"
                        @click.stop="removeUrlAt(singleTarget(section.code, fieldName), imgIndex)"
                      >
                        ×
                      </view>
                    </view>
                    <view
                      v-if="remainingSlots(formData[section.code][fieldName]) > 0"
                      class="h-40 w-40 flex flex-col items-center justify-center border rounded-2 border-dashed text-2.5"
                      style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                      @click="chooseAndUploadImage(singleTarget(section.code, fieldName), `${section.code}.${fieldName}`)"
                    >
                      <view class="text-4">
                        +
                      </view>
                      <view class="mt-1">
                        {{ uploadingKey === `${section.code}.${fieldName}` ? '上传中…' : `点击上传图片（${asUrlList(formData[section.code][fieldName]).length}/${MAX_UPLOAD_COUNT}）` }}
                      </view>
                    </view>
                  </view>
                </view>
                <view v-else-if="field.type === 'file'" class="flex flex-1 flex-col gap-1">
                  <view
                    v-for="(url, fileIndex) in asUrlList(formData[section.code][fieldName])"
                    :key="`${url}-${fileIndex}`"
                    class="flex items-center justify-between rounded-2 px-3 py-2 text-3"
                    style="border: 1rpx solid var(--wot-border-main)"
                  >
                    <text class="flex-1 truncate" style="color: var(--wot-text-main)">
                      {{ fileNameOf(url) }}
                    </text>
                    <text class="wot-text-error-main ml-2 text-2.5" @click.stop="removeUrlAt(singleTarget(section.code, fieldName), fileIndex)">
                      删除
                    </text>
                  </view>
                  <view
                    v-if="remainingSlots(formData[section.code][fieldName]) > 0"
                    class="h-12 flex items-center justify-center border rounded-2 border-dashed text-2.5"
                    style="border-color: var(--wot-primary-3); color: var(--wot-primary-6)"
                    @click="chooseAndUploadFile(singleTarget(section.code, fieldName), `${section.code}.${fieldName}`)"
                  >
                    {{ uploadingKey === `${section.code}.${fieldName}` ? '上传中…' : `+ 添加附件（${asUrlList(formData[section.code][fieldName]).length}/${MAX_UPLOAD_COUNT}）` }}
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
        <wd-picker
          :visible="optionPickerVisible"
          :columns="optionPickerColumns"
          @confirm="onOptionConfirm"
          @cancel="optionPickerVisible = false"
        />
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
        <!-- 产品库候选：同名多厂商/多规格时由用户选择 -->
        <wd-popup
          v-model="productPickerVisible"
          position="bottom"
          round
          custom-style="max-height: 70vh; overflow-y: auto;"
          @close="productPickerVisible = false"
        >
          <view class="px-4 py-3">
            <view class="mb-2 flex items-center justify-between">
              <text class="text-3.5 font-semibold" style="color: var(--wot-text-main)">
                选择产品（{{ productCandidates.length }} 条匹配）
              </text>
              <text class="text-2.5" style="color: var(--wot-text-auxiliary)" @click="productPickerVisible = false">
                取消
              </text>
            </view>
            <view
              v-for="item in productCandidates"
              :key="item.id"
              class="mb-2 rounded-2 p-3"
              style="border: 1rpx solid var(--wot-border-main)"
              @click="onProductCandidatePick(item)"
            >
              <view class="text-3 font-medium" style="color: var(--wot-text-main)">
                {{ item.name }}
              </view>
              <view class="mt-1 text-2.5" style="color: var(--wot-text-auxiliary)">
                规格：{{ item.spec || '—' }} · 生产企业：{{ item.manufacturer || '—' }}
              </view>
            </view>
            <view v-if="!productCandidates.length" class="py-6 text-center text-2.5" style="color: var(--wot-text-auxiliary)">
              没有匹配的产品，按手填内容提交即可（系统会自动入库待运营审核）
            </view>
          </view>
        </wd-popup>
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
