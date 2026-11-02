/**
 * 导航单一真值表 —— C 端入口可见性的唯一来源。
 *
 * 背景：小程序里混着 C 端（执行任务）与运营/开发（运营仪表盘、工单、AI）三类功能。
 * 产品口径是「能不删就不删，按角色/权限展示」，所以**页面全部保留**，只有这份表决定
 * 谁在什么地方看得到入口。新增入口只改这里，不要在各页面里散写 `v-if`。
 *
 * 权限只控制**入口可见性**：真实越权由后端 RBAC / 本人数据过滤兜底，前端不承担鉴权职责。
 */

/** 入口可见范围：`all` = 所有登录用户；`superuser` = 仅超管 */
export type NavVisibility = 'all' | 'superuser'

/** 入口色调（图标底色与前景色，跟随 wot 设计令牌） */
export type NavTone = 'primary' | 'green' | 'orange' | 'cyan' | 'purple'

export interface NavEntry {
  /** 路由名，必须与页面 `definePage({ name })` 一致；`dialog` 类入口用语义 key */
  name: string
  /** 打开弹窗而非跳页（目前只有「修改密码」内嵌在「我的」页） */
  dialog?: 'password'
  /** 「我的」页里的分组：我的服务 / 账号 */
  section?: 'service' | 'account'
  /** i18n 标题键 */
  titleKey: string
  /** wd-icon 图标名 */
  icon: string
  tone: NavTone
  visibleTo: NavVisibility
}

export interface NavGroup {
  /** i18n 分组标题键 */
  titleKey: string
  tone: NavTone
  items: NavEntry[]
}

/** 底部 TabBar（所有角色一致，顺序即展示顺序；首页为默认落地页） */
export const TABBAR_ITEMS: NavEntry[] = [
  { name: 'home', titleKey: 'common.tab.home', icon: 'home', tone: 'primary', visibleTo: 'all' },
  { name: 'market-task-hall', titleKey: 'common.tab.taskHall', icon: 'store', tone: 'primary', visibleTo: 'all' },
  { name: 'market-work-desk', titleKey: 'common.tab.workDesk', icon: 'ordered-list', tone: 'green', visibleTo: 'all' },
  { name: 'mine', titleKey: 'common.tab.mine', icon: 'user', tone: 'primary', visibleTo: 'all' },
]

/** 「我的」页功能列表（C 端可见） */
export const MINE_ENTRIES: NavEntry[] = [
  { name: 'feedback', titleKey: 'common.nav.feedback', icon: 'edit', tone: 'primary', visibleTo: 'all', section: 'service' },
  { name: 'work-notices', titleKey: 'common.nav.notices', icon: 'notification', tone: 'green', visibleTo: 'all', section: 'service' },
  { name: 'profile', titleKey: 'common.profile', icon: 'user', tone: 'primary', visibleTo: 'all', section: 'account' },
  { name: 'password', titleKey: 'account.password', icon: 'lock', tone: 'primary', visibleTo: 'all', dialog: 'password', section: 'account' },
  { name: 'setting', titleKey: 'common.settings', icon: 'settings', tone: 'primary', visibleTo: 'all', section: 'account' },
  { name: 'about', titleKey: 'common.aboutUs', icon: 'info-circle', tone: 'primary', visibleTo: 'all', section: 'account' },
]

/**
 * 超管专属入口（运营 / 开发调试）——C 端用户完全看不到。
 * 这些页面全部保留在小程序包里，只是没有入口。
 */
export const SUPERUSER_ENTRIES: NavEntry[] = [
  { name: 'ops-dashboard', titleKey: 'common.nav.dashboard', icon: 'dashboard', tone: 'orange', visibleTo: 'superuser' },
  { name: 'work-tickets', titleKey: 'common.nav.tickets', icon: 'message', tone: 'orange', visibleTo: 'superuser' },
  { name: 'work-chat', titleKey: 'common.nav.aiChat', icon: 'interaction', tone: 'cyan', visibleTo: 'superuser' },
  { name: 'work-ai-models', titleKey: 'common.nav.aiModels', icon: 'robot', tone: 'purple', visibleTo: 'superuser' },
]

/** 超管「全部功能」页的分组（原工作台聚合页内容，按权限过滤后渲染） */
export const ALL_FEATURES_GROUPS: NavGroup[] = [
  {
    titleKey: 'work.businessCenter',
    tone: 'orange',
    items: [
      { name: 'work-notices', titleKey: 'common.nav.notices', icon: 'notification', tone: 'green', visibleTo: 'all' },
      { name: 'work-tickets', titleKey: 'common.nav.tickets', icon: 'message', tone: 'orange', visibleTo: 'superuser' },
    ],
  },
  {
    titleKey: 'work.opsTools',
    tone: 'purple',
    items: [
      { name: 'ops-dashboard', titleKey: 'common.nav.dashboard', icon: 'dashboard', tone: 'orange', visibleTo: 'superuser' },
      { name: 'work-chat', titleKey: 'common.nav.aiChat', icon: 'interaction', tone: 'cyan', visibleTo: 'superuser' },
      { name: 'work-ai-models', titleKey: 'common.nav.aiModels', icon: 'robot', tone: 'purple', visibleTo: 'superuser' },
    ],
  },
]

/** 入口色调 → 图标底色 / 前景色（UnoCSS 原子类与 wot CSS 变量） */
export const NAV_TONE_STYLE: Record<NavTone, { soft: string, color: string }> = {
  primary: { soft: 'wot-bg-primary-1', color: 'var(--wot-primary-6)' },
  green: { soft: 'wot-bg-green-1', color: 'var(--wot-green-6)' },
  orange: { soft: 'wot-bg-orange-1', color: 'var(--wot-orange-6)' },
  cyan: { soft: 'wot-bg-cyan-1', color: 'var(--wot-cyan-6)' },
  purple: { soft: 'wot-bg-purple-1', color: 'var(--wot-purple-6)' },
}
