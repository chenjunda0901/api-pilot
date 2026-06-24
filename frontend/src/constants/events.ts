/**
 * 全局事件总线事件名常量
 * 所有 eventBus.emit / eventBus.on / eventBus.off 调用必须使用此处定义的事件名
 */
export const EVENTS = {
  /** 场景开始运行 */
  SCENE_RUNNING: 'scene:running',
  /** 场景执行完成 */
  SCENE_COMPLETE: 'scene:complete',
  /** 页面加载完成 */
  PAGE_LOADED: 'page:loaded',
  /** 关闭所有右键菜单 */
  CTX_CLOSE_ALL: 'ctx:close-all',
  /** 新建接口 */
  NEW_API: 'newApi',
  /** 导入接口 */
  IMPORT_API: 'importApi',
  /** 导入到指定目录 */
  IMPORT_TO_CATEGORY: 'importToCategory',
} as const

/**
 * localStorage / sessionStorage 键名常量
 */
export const STORAGE_KEYS = {
  // 主题
  THEME: 'api_pilot_theme',
  COMPACT: 'api_pilot_compact',
  // 环境
  ENV: 'api_pilot_env',
  // 标签页
  TABS: 'api_pilot_tabs',
  TABS_ACTIVE: 'api_pilot_tabs_active',
  TABS_CLEARED: 'api_pilot_tabs_cleared',
  // 侧边栏
  SIDEBAR_COLLAPSED: 'api_pilot_sidebar_collapsed',
  TREE_WIDTH: 'api_pilot_tree_width',
  // 搜索
  SEARCH_RECENT: 'api_pilot_search_recent',
  // 认证
  REFRESH_TOKEN: 'refresh_token',
  ACCESS_TOKEN: 'access_token',
  USER: 'user',
  // 项目
  LAST_PROJECT_ID: 'last_project_id',
  // 会话
  NEW_API_CATEGORY: 'new_api_category',
  LOGIN_REDIRECT_HASH: 'api_pilot_login_redirect_hash',
  LOGIN_REDIRECT: 'login_redirect',
  EXTRACT_RULES: 'extract_rules',
  NEW_API_DRAFT_NAME: 'new_api_draft_name',
  API_PILOT_LOCALE: 'api-pilot-locale',
} as const

/**
 * 路由路径常量
 * 路由定义在 router/index.ts 中，此处的路径用于 router.push/replace
 */
export const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  DASHBOARD: '/dashboard',
  PROJECT_APIS: (pid: number | string) => `/projects/${pid}/apis`,
  PROJECT_API_DETAIL: (pid: number | string, apiId: number | string) => `/projects/${pid}/apis/detail/${apiId}`,
  PROJECT_API_NEW: (pid: number | string) => `/projects/${pid}/apis/detail/new`,
  PROJECT_API_CASE: (pid: number | string, caseId: number | string) => `/projects/${pid}/apis/case/${caseId}`,
  PROJECT_SCENES: (pid: number | string) => `/projects/${pid}/scenes`,
  PROJECT_REPORTS: (pid: number | string) => `/projects/${pid}/reports`,
  PROJECT_REPORT_DETAIL: (pid: number | string, reportId: number | string) => `/projects/${pid}/reports/${reportId}`,
  PROJECT_MOCK_RULES: (pid: number | string) => `/projects/${pid}/mock-rules`,
  PROJECT_SETTINGS: (pid: number | string) => `/projects/${pid}/settings`,
  PROJECT_RECYCLE_BIN: (pid: number | string) => `/projects/${pid}/recycle-bin`,
} as const
