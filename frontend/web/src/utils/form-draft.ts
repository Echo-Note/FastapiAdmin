/**
 * 创建表单草稿缓存（localStorage）。
 *
 * 用于「新建/新增/添加」表单：用户填了一半误关窗口，再次打开时恢复已填写内容。
 * 仅缓存创建态表单，编辑态表单由详情接口回填、不缓存。
 *
 * 存储键统一加 ``market-form-draft:`` 前缀，与业务数据隔离。
 */

const PREFIX = "market-form-draft:";

/** 读取创建表单草稿，无草稿或解析失败返回 null */
export function loadFormDraft<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(`${PREFIX}${key}`);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

/** 保存创建表单草稿（剔除 id，避免把编辑态带入新建） */
export function saveFormDraft(key: string, data: Record<string, unknown>): void {
  try {
    const { id: _id, ...rest } = data;
    void _id;
    localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(rest));
  } catch {
    // 存储不可用/超限时静默忽略，不影响主流程
  }
}

/** 清除创建表单草稿（提交成功后调用） */
export function clearFormDraft(key: string): void {
  try {
    localStorage.removeItem(`${PREFIX}${key}`);
  } catch {
    // 忽略
  }
}

/**
 * 创建表单草稿帮助器（供手写表单页面使用）。
 *
 * 内置「提交成功后跳过本次关闭保存」标志，避免提交后残留草稿：
 * - ``restore``：打开新增表单时调用，恢复上次草稿；
 * - ``persist``：关闭新增表单时调用（重置前），保存草稿；
 * - ``done``：提交成功后调用，清除草稿并标记跳过本次关闭保存。
 */
export function createFormDraft(key: string) {
  let submitted = false;
  return {
    restore<T extends Record<string, unknown>>(form: T): void {
      const draft = loadFormDraft<Record<string, unknown>>(key);
      if (draft) Object.assign(form, draft);
      submitted = false;
    },
    persist(form: Record<string, unknown>): void {
      if (submitted) {
        submitted = false;
        return;
      }
      saveFormDraft(key, form);
    },
    done(): void {
      submitted = true;
      clearFormDraft(key);
    },
  };
}
