import type { AlovaGenerics, Method } from 'alova'
import type { MarketPageResult } from '@/api/module_market'
import { usePagination } from 'alova/client'
import { computed, ref } from 'vue'

export interface MarketListPageParams {
  page_no: number
  page_size: number
}

export interface MarketListPageOptions<AG extends AlovaGenerics = AlovaGenerics> {
  fetcher: (params: MarketListPageParams) => Method<AG>
  pageSize?: number
  onError?: (error: unknown) => void
}

/**
 * market 域列表分页逻辑（基于 alova usePagination 封装）。
 *
 * 与 useListPage 的差异：后端 PageResultSchema 返回字段为 `items`（而非 `list`），
 * 本组合式函数据此读取 `items`，避免列表恒为空。
 */
export function useMarketListPage<T, AG extends AlovaGenerics = AlovaGenerics>(options: MarketListPageOptions<AG>) {
  const { fetcher, pageSize = 10, onError } = options

  const pageParams = ref<MarketListPageParams>({ page_no: 1, page_size: pageSize })

  const {
    data,
    total,
    loading,
    error,
    send,
    refresh,
    reload: reloadPagination,
    onError: onPageError,
  } = usePagination<AG, T[], any[]>(
    (pageNo: number, pageSizeNo: number) => {
      const method = fetcher({ page_no: pageNo, page_size: pageSizeNo })
      method.config.cacheFor = 0
      return method
    },
    {
      initialPage: 1,
      initialPageSize: pageSize,
      immediate: false,
      watchingStates: [],
      preloadNextPage: false,
      preloadPreviousPage: false,
      data: res => (res as MarketPageResult<T>).items ?? [],
      total: res => (res as MarketPageResult<T>).total ?? 0,
    },
  )

  onPageError(({ error: e }) => {
    onError?.(e)
  })

  async function loadData() {
    try {
      await send(pageParams.value.page_no, pageParams.value.page_size)
    }
    catch {
      // 错误已由 onPageError → onError 统一处理
    }
    finally {
      uni.stopPullDownRefresh()
    }
  }

  async function refreshData() {
    try {
      await refresh(pageParams.value.page_no)
    }
    catch {}
    finally {
      uni.stopPullDownRefresh()
    }
  }

  async function reload() {
    pageParams.value.page_no = 1
    try {
      await reloadPagination()
    }
    catch {}
    finally {
      uni.stopPullDownRefresh()
    }
  }

  async function loadNext() {
    pageParams.value.page_no += 1
    await loadData()
  }

  async function toFirst() {
    pageParams.value.page_no = 1
    await loadData()
  }

  return {
    list: computed<T[]>(() => data.value ?? []),
    total: computed<number>(() => total.value ?? 0),
    loading,
    error,
    pageParams,
    loadData,
    refreshData,
    reload,
    loadNext,
    toFirst,
  }
}
