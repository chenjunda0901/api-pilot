import { createApp } from "vue"
import { logger } from "./utils/logger"
import pinia from "./stores"
import router from "./router"
import i18n from "./i18n"
import App from "./App.vue"
import "./styles/tokens.css"
import "element-plus/dist/index.css"
import "./styles/base.css"
import "./styles/utilities.css"
import "./styles/animations.css"
import "./styles/global.css"
import "./styles/page-layout.css"
import "./styles/element-plus-override.css"
import "./styles/responsive.css"
import "./styles/dark-mode.css"
import { initTheme } from "./utils/theme"
// 注册 ECharts 亮/暗主题（必须在使用 echarts.init 之前导入）
import "./utils/echartsTheme"
// 初始化全局网络检测器
import { initGlobalNetworkDetector } from "./composables/useNetworkDetector"

// Monaco Editor Web Worker 配置（必须在 monaco-editor 动态导入之前设置）
// 使用 Vite 的 ?worker 导入语法，Vite 会自动打包为独立 chunk 并正确处理 MIME 类型
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'

;(self as unknown as { MonacoEnvironment: unknown }).MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === 'json') {
      return new JsonWorker()
    }
    return new EditorWorker()
  },
}

// Initialize theme before mounting app
initTheme()

// 初始化全局网络检测器
initGlobalNetworkDetector()

const app = createApp(App)

app.use(i18n)

// Global error handler
app.config.errorHandler = (err) => {
  logger.error('[Global Error]', err)
}

// 全局未捕获 Promise rejection 处理器（Vue errorHandler 不捕获 Promise）
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason
  if (reason instanceof Error) {
    logger.error('[Unhandled Rejection]', reason.message, reason.stack)
  } else {
    logger.error('[Unhandled Rejection]', String(reason))
  }
})

/** 已知的 Element Plus 内部无害警告关键词列表 */
const EP_INTERNAL_WARN_PATTERNS = [
  'Invalid prop: validation failed for prop "role"',
  'Invalid prop: custom validator check failed for prop "role"',
  'Expected one of ["dialog", "grid", "group", "listbox", "menu", "navigation", "tooltip", "tree"], got value "button"',
  'Runtime directive used on component with non-element root node',
  'The directives will not function as intended',
  'Failed to resolve component: BodyEditor',
  'Failed to resolve component: ResponsePanel',
  'Invalid prop: type check failed for prop "apiId"',
  // Vue 组件无法继承 attrs 的无害警告（fragment 组件接收 class 等属性）
  'Extraneous non-props attributes',
]

function isEpInternalWarning(msg: string): boolean {
  return EP_INTERNAL_WARN_PATTERNS.some((pattern) => msg.includes(pattern))
}

// Global warn handler — 过滤 Element Plus 内部已知无害警告
app.config.warnHandler = (msg, _instance, _trace) => {
  if (isEpInternalWarning(msg)) {
    // 静默忽略已知的 EP 内部警告
    return
  }
  if (import.meta.env.DEV) {
    logger.warn('[Vue Warn]', msg)
  }
}

app.use(pinia)
app.use(router)

// 全局指令
import { vRipple } from "./directives/ripple"
app.directive('ripple', vRipple)

app.mount("#app")