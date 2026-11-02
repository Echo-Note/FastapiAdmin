/**
 * CommonUtil 工具方法
 * 提供 deepClone / isString / isObj / isDef / deepMerge 等工具方法
 */
export const CommonUtil = {
  isString(val: unknown): val is string {
    return typeof val === 'string'
  },

  isObj(val: unknown): val is Record<string, any> {
    return val !== null && typeof val === 'object' && !Array.isArray(val)
  },

  isDef(val: unknown): boolean {
    return val !== undefined && val !== null
  },

  /**
   * 深拷贝
   * 优先使用原生 structuredClone（支持 Date/Map/Set/循环引用等），
   * 失败时（如 Vue reactive Proxy 无法被 structuredClone 序列化）回退 JSON 深拷贝。
   */
  /**
   * 金额展示：千分位 + 固定小数位，非数字按 0 处理。
   *
   * 不走 `toLocaleString`：部分小程序运行时的 ICU 被裁剪，分隔符会丢失，
   * 金额是 C 端最敏感的信息，宁可自己格式化。
   */
  formatMoney(value?: number | string | null, decimals = 0): string {
    const num = Number(value ?? 0)
    const fixed = (Number.isFinite(num) ? num : 0).toFixed(decimals)
    const [int, dec] = fixed.split('.')
    const withSeparator = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return dec ? `${withSeparator}.${dec}` : withSeparator
  },

  deepClone<T>(obj: T): T {
    if (typeof structuredClone === 'function') {
      try {
        return structuredClone(obj)
      }
      catch {
        // structuredClone 无法克隆 Vue reactive Proxy（Pinia $state）等对象，回退 JSON
      }
    }
    return JSON.parse(JSON.stringify(obj)) as T
  },

  deepMerge<T extends Record<string, any>>(target: T, source: Record<string, any>): T {
    const result = { ...target } as Record<string, any>
    for (const key of Object.keys(source)) {
      if (CommonUtil.isObj(source[key]) && CommonUtil.isObj(result[key])) {
        result[key] = CommonUtil.deepMerge(result[key], source[key])
      }
      else {
        result[key] = source[key]
      }
    }
    return result as T
  },
}
