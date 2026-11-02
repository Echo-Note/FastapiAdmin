<script setup lang="ts">
import type { NoticeForm, NoticeItem } from '@/api/module_system/notice'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NoticeAPI } from '@/api/module_system/notice'
import { useAccess } from '@/composables/useAccess'
import { useI18nNavTitle } from '@/composables/useI18nNavTitle'
import { useNoticeDismiss } from '@/composables/useNoticeDismiss'

definePage({ name: 'work-notices', style: { navigationBarTitleText: '通知公告', enablePullDownRefresh: true } })
useI18nNavTitle('notices.title')

const { t } = useI18n()
const toast = useToast()
const dialog = useGlobalDialog()
const { isSuperuser } = useAccess()
const { dismiss } = useNoticeDismiss()
/** 从首页/任务大厅点条幅进来时带的公告 id，加载完后直接打开它的详情 */
const pendingDetailId = ref<number>()

const list = ref<NoticeItem[]>([])
const loading = ref(false)
const failed = ref(false)
const keyword = ref('')

const detail = ref<NoticeItem | null>(null)
const showDetail = ref(false)

const showForm = ref(false)
const formTitle = ref('')
const currentId = ref<number>()
const submitting = ref(false)
const formData = reactive<NoticeForm>({ notice_title: '', notice_content: '', notice_type: '1', status: 0, description: '' })

const NOTICE_TYPE_OPTIONS = [
  { value: '1', labelKey: 'notices.notice' },
  { value: '2', labelKey: 'notices.announce' },
]
const STATUS_OPTIONS = [
  { value: 0, labelKey: 'common.status.draft' },
  { value: 1, labelKey: 'common.status.published' },
  { value: 2, labelKey: 'common.status.archived' },
]

/** available 一次返回全部已发布公告，量级很小，只在本地按标题过滤，不做分页 */
const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw)
    return list.value
  return list.value.filter(item => (item.notice_title ?? '').toLowerCase().includes(kw))
})

/** 有公告但被关键词筛空 —— 空态要区分「没有公告」与「没搜到」 */
const isFilteredOut = computed(() => list.value.length > 0 && filteredList.value.length === 0)

/** 正文按换行切段渲染为纯文本，不走 v-html */
const detailParagraphs = computed(() =>
  (detail.value?.notice_content ?? '')
    .split(/\n+/)
    .map(p => p.trim())
    .filter(Boolean),
)

function typeLabel(type?: string) {
  return type === '2' ? t('notices.announce') : t('notices.notice')
}

function typeClass(type?: string) {
  return type === '2' ? 'notice-chip--announce' : 'notice-chip--notice'
}

function timeText(item: NoticeItem) {
  return (item.created_time ?? '').slice(0, 16)
}

async function loadList() {
  loading.value = true
  failed.value = false
  try {
    list.value = (await NoticeAPI.getAvailable(50)) ?? []
  }
  catch {
    list.value = []
    failed.value = true
  }
  finally {
    loading.value = false
    uni.stopPullDownRefresh()
  }
}

function openDetail(item: NoticeItem) {
  detail.value = item
  showDetail.value = true
  // 看过就收起首页/任务大厅的条幅（同一条公告不再打扰）
  dismiss(item.id)
}

function resetForm() {
  Object.assign(formData, { notice_title: '', notice_content: '', notice_type: '1', status: 0, description: '' })
}
function openCreate() {
  formTitle.value = t('notices.createTitle')
  currentId.value = undefined
  resetForm()
  showForm.value = true
}
async function openEdit(item: NoticeItem) {
  if (!item.id)
    return
  formTitle.value = t('notices.editTitle')
  currentId.value = item.id
  try {
    const res = await NoticeAPI.getDetail(item.id)
    Object.assign(formData, {
      notice_title: res.notice_title || '',
      notice_content: res.notice_content || '',
      notice_type: res.notice_type || '1',
      status: res.status ?? 0,
      description: res.description || '',
    })
    showForm.value = true
  }
  catch { toast.error(t('notices.detailFailed')) }
}
async function handleSubmit() {
  submitting.value = true
  try {
    if (currentId.value) {
      await NoticeAPI.update(currentId.value, formData)
      toast.success(t('common.updateSuccess'))
    }
    else {
      await NoticeAPI.create(formData)
      toast.success(t('common.createSuccess'))
    }
    showForm.value = false
    await loadList()
  }
  catch { toast.error(t('common.operationFailed')) }
  finally { submitting.value = false }
}
function handleDelete(item: NoticeItem) {
  if (!item.id)
    return
  dialog.confirm({
    title: t('common.title'),
    msg: t('common.deleteConfirm'),
    success: async ({ action }) => {
      if (action === 'confirm') {
        try {
          await NoticeAPI.remove([item.id!])
          toast.success(t('common.deleteSuccess'))
          await loadList()
        }
        catch { toast.error(t('common.deleteFailed')) }
      }
    },
  })
}

onLoad((query) => {
  pendingDetailId.value = query?.id ? Number(query.id) : undefined
  loadList().then(() => {
    // 深链进来：列表加载完成后直接弹出该公告详情
    if (pendingDetailId.value == null)
      return
    const target = list.value.find(item => item.id === pendingDetailId.value)
    if (target)
      openDetail(target)
    pendingDetailId.value = undefined
  })
})
onPullDownRefresh(() => loadList())
</script>

<template>
  <view class="page-wraper">
    <!-- 搜索 + 只读提示：C 端只有读取权限，写入口仅超管可见 -->
    <view class="notice-head">
      <wd-search
        v-model="keyword"
        :placeholder="t('notices.searchPlaceholder')"
        variant="light"
        hide-cancel
      />
      <view class="notice-head__meta">
        <text class="notice-head__tip">
          {{ t('notices.readOnlyTip') }}
        </text>
        <text class="notice-head__count">
          {{ t('notices.count', { count: filteredList.length }) }}
        </text>
      </view>
    </view>

    <SkeletonPage v-if="loading && list.length === 0" :rows="5" class="mt-1" />

    <!-- 失败态：说清是「加载失败」并给重试，不能退化成「暂无公告」 -->
    <view v-else-if="failed" class="notice-state">
      <wd-icon name="exclamation-circle" size="32px" color="var(--wot-warning-main)" />
      <wd-text :text="t('common.loadFailed')" class="wot-text-text-secondary text-3" />
      <wd-button size="small" round @click="loadList">
        {{ t('common.retry') }}
      </wd-button>
    </view>

    <view v-else-if="list.length === 0" class="notice-state">
      <wd-empty :tip="t('notices.empty')" />
    </view>

    <view v-else-if="isFilteredOut" class="notice-state">
      <wd-empty :tip="t('notices.emptyWithFilter')" />
    </view>

    <view v-else class="notice-list">
      <view
        v-for="item in filteredList"
        :key="item.id"
        class="notice-card"
        hover-class="notice-card--pressed"
        @click="openDetail(item)"
      >
        <view class="min-w-0 flex-1">
          <view class="notice-card__title">
            {{ item.notice_title }}
          </view>
          <view class="notice-card__meta">
            <text class="notice-chip" :class="typeClass(item.notice_type)">
              {{ typeLabel(item.notice_type) }}
            </text>
            <text class="notice-card__time">
              {{ timeText(item) }}
            </text>
          </view>
        </view>
        <!-- 写入口仅超管可见，普通用户点卡片只读 -->
        <view v-if="isSuperuser" class="flex shrink-0 items-center">
          <view class="notice-card__action" hover-class="notice-card__action--pressed" @click.stop="openEdit(item)">
            <wd-icon name="edit" size="18px" color="var(--wot-primary-6)" />
          </view>
          <view class="notice-card__action" hover-class="notice-card__action--pressed" @click.stop="handleDelete(item)">
            <wd-icon name="delete" size="18px" color="var(--wot-danger-main)" />
          </view>
        </view>
      </view>
    </view>

    <wd-gap height="160rpx" safe-area-bottom />

    <!-- 新建：仅超管 -->
    <wd-fab v-if="isSuperuser" position="right-bottom" :expandable="false" :gap="{ bottom: 40 }" @click="openCreate" />

    <!-- 公告详情（只读）：居中弹窗，不是底部抽屉 -->
    <wd-popup v-model="showDetail" position="center" custom-style="width: 82%; border-radius: 24rpx; overflow: hidden;" @close="showDetail = false">
      <view class="notice-detail">
        <view class="notice-detail__head">
          <view class="notice-detail__title">
            {{ detail?.notice_title }}
          </view>
          <view class="notice-card__meta">
            <text class="notice-chip" :class="typeClass(detail?.notice_type)">
              {{ typeLabel(detail?.notice_type) }}
            </text>
            <text class="notice-card__time">
              {{ detail ? timeText(detail) : '' }}
            </text>
          </view>
        </view>
        <scroll-view scroll-y class="notice-detail__body">
          <text v-for="(paragraph, index) in detailParagraphs" :key="index" class="notice-detail__paragraph">
            {{ paragraph }}
          </text>
          <text v-if="detailParagraphs.length === 0" class="notice-detail__paragraph notice-detail__paragraph--empty">
            {{ t('notices.empty') }}
          </text>
        </scroll-view>
        <view class="notice-detail__footer">
          <wd-button type="primary" size="small" round custom-class="notice-detail__btn" @click="showDetail = false">
            {{ t('common.confirm') }}
          </wd-button>
        </view>
      </view>
    </wd-popup>

    <!-- 表单弹窗：仅超管入口可达 -->
    <wd-popup v-model="showForm" position="bottom" round custom-style="max-height: 80vh; overflow-y: auto;" @close="showForm = false">
      <view class="p-xl">
        <wd-navbar :title="formTitle" left-arrow @click-left="showForm = false" />
        <wd-form :model="formData" class="mt-lg">
          <wd-form-item :label="t('notices.formTitle')" prop="notice_title" border>
            <wd-input v-model="formData.notice_title" :placeholder="t('common.placeholder')" />
          </wd-form-item>
          <wd-form-item :label="t('notices.content')" prop="notice_content" border>
            <wd-textarea v-model="formData.notice_content" :placeholder="t('notices.contentPlaceholder')" />
          </wd-form-item>
          <wd-form-item :label="t('notices.type')" border>
            <wd-radio-group v-model="formData.notice_type" direction="horizontal">
              <wd-radio v-for="opt in NOTICE_TYPE_OPTIONS" :key="opt.value" :value="opt.value">
                {{ t(opt.labelKey) }}
              </wd-radio>
            </wd-radio-group>
          </wd-form-item>
          <wd-form-item :label="t('common.field.status')" border>
            <wd-radio-group v-model="formData.status" direction="horizontal">
              <wd-radio v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
                {{ t(opt.labelKey) }}
              </wd-radio>
            </wd-radio-group>
          </wd-form-item>
          <wd-form-item :label="t('common.field.remark')" border>
            <wd-textarea v-model="formData.description" :placeholder="t('common.placeholder')" />
          </wd-form-item>
        </wd-form>
        <view class="mt-xl flex gap-3">
          <wd-button block variant="plain" @click="showForm = false">
            {{ t('common.cancel') }}
          </wd-button>
          <wd-button block type="primary" :loading="submitting" @click="handleSubmit">
            {{ t('common.save') }}
          </wd-button>
        </view>
      </view>
    </wd-popup>
  </view>
</template>

<style lang="scss" scoped>
.notice-head {
  padding: 16rpx 0 8rpx;

  &__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16rpx;
    padding: 8rpx 24rpx 0;
  }

  &__tip {
    flex: 1;
    min-width: 0;
    font-size: 22rpx;
    line-height: 1.5;
    color: var(--wot-text-auxiliary);
  }

  &__count {
    flex-shrink: 0;
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
    font-variant-numeric: tabular-nums;
  }
}

.notice-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
  margin-top: 80rpx;
  padding: 0 24rpx;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding: 8rpx 24rpx 0;
}

/* 列表卡片：单一表面 + 内部细线分层，与任务大厅保持同一套写法 */
.notice-card {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 28rpx;
  border-radius: 20rpx;
  background: var(--wot-filled-oppo);
  transition: opacity 0.15s ease;

  &--pressed {
    opacity: 0.72;
  }

  &__title {
    font-size: 30rpx;
    font-weight: 600;
    line-height: 1.4;
    color: var(--wot-text-main);
    /* 长标题最多两行，避免把类型与时间挤出卡片 */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-top: 14rpx;
  }

  &__time {
    font-size: 22rpx;
    color: var(--wot-text-auxiliary);
    font-variant-numeric: tabular-nums;
  }

  &__action {
    padding: 16rpx;
    border-radius: 12rpx;

    &--pressed {
      background: var(--wot-filled-content);
    }
  }
}

.notice-chip {
  padding: 4rpx 14rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;

  &--notice {
    color: var(--wot-primary-6);
    background: var(--wot-filled-content);
  }

  &--announce {
    color: var(--wot-warning-main);
    background: var(--wot-warning-surface);
  }
}

/* 居中弹窗里的公告详情：头/正文/底部三段，正文自己滚动 */
.notice-detail {
  display: flex;
  flex-direction: column;
  max-height: 70vh;
  padding: 0 28rpx;

  &__head {
    padding: 32rpx 0 20rpx;
    border-bottom: 1rpx solid var(--wot-border-light);
  }

  &__title {
    font-size: 34rpx;
    font-weight: 600;
    line-height: 1.4;
    color: var(--wot-text-main);
  }

  &__body {
    flex: 1;
    min-height: 0;
    max-height: 46vh;
    padding: 24rpx 0;
  }

  &__footer {
    display: flex;
    justify-content: center;
    padding: 8rpx 0 28rpx;
  }

  &__btn {
    min-width: 220rpx;
  }

  &__paragraph {
    display: block;
    margin-bottom: 16rpx;
    font-size: 28rpx;
    line-height: 1.75;
    color: var(--wot-text-secondary);
    white-space: pre-wrap;
    word-break: break-word;

    &--empty {
      color: var(--wot-text-auxiliary);
    }
  }
}
</style>
