import { ref } from 'vue'
import { Storage } from '@/utils/storage'

/**
 * 公告条幅的「已读即收起」记录。
 *
 * 为什么要本地存：公告本身没有「谁读过」的接口（上游已读能力还在 PR 里），
 * 但产品要求「点开看过之后，首页和任务大厅的条幅都收起来」。所以按公告 id 记在本地：
 * 同一条公告看过就不再打扰，运营发了新公告（新 id）条幅会重新出现。
 */
const STORAGE_KEY = 'notice_dismissed_ids'
/** 只保留最近 N 条，避免长期使用后 storage 无限增长 */
const MAX_KEEP = 50

function readDismissed(): number[] {
  try {
    const stored = Storage.get<number[]>(STORAGE_KEY)
    return Array.isArray(stored) ? stored.filter(id => typeof id === 'number') : []
  }
  catch {
    return []
  }
}

const dismissedIds = ref<Set<number>>(new Set(readDismissed()))

export function useNoticeDismiss() {
  function isDismissed(id?: number | null) {
    return id != null && dismissedIds.value.has(id)
  }

  /** 标记某条公告已看（点开详情 / 手动关闭条幅时调用） */
  function dismiss(id?: number | null) {
    if (id == null || dismissedIds.value.has(id))
      return
    dismissedIds.value = new Set([...dismissedIds.value, id])
    Storage.set(STORAGE_KEY, [...dismissedIds.value].slice(-MAX_KEEP))
  }

  return { isDismissed, dismiss }
}
