/**
 * API Pilot Theme Manager
 * 提供主题切换的底层工具函数，与 composables/useTheme.ts 共享同一 localStorage key。
 *
 * 职责：
 *   - 主题持久化（localStorage）
 *   - DOM 应用（html.dark class + color-scheme）
 *   - 系统偏好检测
 *
 * 注意：组件中推荐使用 composables/useTheme.ts 获取响应式状态。
 */

const THEME_STORAGE_KEY = 'api_pilot_theme'
export type Theme = 'light' | 'dark'

/**
 * 将字符串规范化为合法主题值，非法值返回 null
 */
function normalizeTheme(theme: string | null | undefined): Theme | null {
  if (theme === 'light' || theme === 'dark') return theme
  return null
}

/**
 * 从 localStorage 读取已保存的主题，无有效值时回退到 'light'
 */
export function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'light'
  try {
    return normalizeTheme(localStorage.getItem(THEME_STORAGE_KEY)) ?? 'light'
  } catch {
    return 'light'
  }
}

/**
 * 将主题应用到 DOM：
 *   - 切换 html.dark class
 *   - 设置 color-scheme 属性（影响原生控件）
 *   - 持久化到 localStorage
 */
export function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    /* localStorage 可能不可用（隐私模式/配额满） */
  }
}

/**
 * 切换主题并返回新主题值
 */
export function toggleTheme(): Theme {
  const next = getStoredTheme() === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  return next
}

/**
 * 当前是否为暗色主题
 */
export function isDarkTheme(): boolean {
  return getStoredTheme() === 'dark'
}

/**
 * 检测系统暗色偏好
 */
export function getSystemThemePreference(): Theme {
  if (typeof window === 'undefined') return 'light'
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

/**
 * 应用启动时的主题初始化：
 *   1. 优先读取 localStorage 中保存的偏好
 *   2. 无保存值时跟随系统偏好
 *   3. 首次加载禁用过渡动画，防止闪烁
 */
export function initTheme(): Theme {
  // 首次加载时临时禁用过渡，避免主题切换时的闪烁
  disableTransition()

  let theme: Theme
  try {
    const stored = normalizeTheme(localStorage.getItem(THEME_STORAGE_KEY))
    if (stored) {
      theme = stored
    } else {
      theme = getSystemThemePreference()
    }
  } catch {
    theme = 'light'
  }

  applyTheme(theme)

  // 等待下一帧后恢复过渡，确保初始渲染完成
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      enableTransition()
    })
  })

  return theme
}

/**
 * 临时禁用所有 CSS 过渡（防止页面加载时的主题闪烁）
 */
function disableTransition(): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.style.setProperty('--theme-transition', 'none')
}

/**
 * 恢复 CSS 过渡
 */
function enableTransition(): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.style.setProperty('--theme-transition', 'background-color 250ms cubic-bezier(0.4, 0, 0.2, 1), color 250ms cubic-bezier(0.4, 0, 0.2, 1), border-color 250ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 250ms cubic-bezier(0.4, 0, 0.2, 1), fill 250ms cubic-bezier(0.4, 0, 0.2, 1), stroke 250ms cubic-bezier(0.4, 0, 0.2, 1), opacity 250ms cubic-bezier(0.4, 0, 0.2, 1)')
}
