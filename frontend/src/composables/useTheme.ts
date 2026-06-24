/**
 * 主题管理 composable
 *
 * 提供亮色/暗色主题切换、紧凑模式切换，自动持久化到 localStorage。
 * 全局单例 —— 所有组件共享同一 theme 状态。
 *
 * 底层逻辑委托给 utils/theme.ts，本模块仅负责：
 *   - 响应式状态封装（ref + computed）
 *   - 系统主题偏好监听（prefers-color-scheme）
 *   - 紧凑模式管理
 *
 * @example
 * ```ts
 * const { theme, toggleTheme, isDark, isCompact, toggleCompact } = useTheme()
 * ```
 */
import { ref, watch, onMounted, onUnmounted, computed, type Ref } from 'vue'
import {
  applyTheme as applyThemeToDom,
  getSystemThemePreference,
  type Theme,
} from '@/utils/theme'

export type { Theme }

// ── 模块级单例状态 ──────────────────────────────────────────────
const STORAGE_KEY = 'api_pilot_theme'
const COMPACT_KEY = 'api_pilot_compact'

const theme = ref<Theme>('light')
const isCompact = ref(false)

// 系统主题偏好监听器（模块级，只注册一次）
let mediaQuery: MediaQueryList | null = null
let mediaListener: ((e: MediaQueryListEvent) => void) | null = null
let listenerRefCount = 0

/**
 * 主题 composable 入口
 *
 * @returns theme         - 当前主题值 ('light' | 'dark')
 * @returns isDark        - 是否为暗色主题（只读 computed）
 * @returns isCompact     - 是否为紧凑模式（只读）
 * @returns toggleTheme   - 切换亮/暗主题
 * @returns setTheme      - 设置指定主题
 * @returns toggleCompact - 切换紧凑模式
 */
export function useTheme() {
  // ── 立即初始化（支持组件上下文外的测试环境）────────────────────
  initThemeState()
  initCompactState()

  // ── 内部方法 ──────────────────────────────────────────────────

  /**
   * 将当前 theme.value 应用到 DOM 并持久化
   */
  function applyTheme(): void {
    applyThemeToDom(theme.value)
  }

  /**
   * 初始化主题状态：
   *   1. 从 localStorage 读取已保存的偏好
   *   2. 无保存值时跟随系统偏好
   *   3. 注册系统主题变化监听
   *
   * 注意：如果 main.ts 已经调用过 initTheme()，这里仅同步状态并注册监听
   */
  function initThemeState(): void {
    // 从 localStorage 同步最新状态（main.ts 可能已初始化）
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
      if (saved === 'light' || saved === 'dark') {
        theme.value = saved
      } else {
        // 无保存值时跟随系统偏好
        theme.value = getSystemThemePreference()
      }
      applyTheme()
    } catch {
      theme.value = 'light'
    }

    // 注册系统主题偏好监听
    setupSystemThemeListener()
  }

  /**
   * 监听系统主题偏好变化（prefers-color-scheme）
   * 仅当用户未手动设置过主题时跟随系统
   */
  function setupSystemThemeListener(): void {
    if (typeof window === 'undefined') return
    // 清理旧的监听器，避免重复注册
    cleanupSystemThemeListener()
    try {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaListener = (e: MediaQueryListEvent) => {
        // 仅当 localStorage 中无保存值时跟随系统变化
        const hasUserPreference = localStorage.getItem(STORAGE_KEY) === 'light' ||
                                  localStorage.getItem(STORAGE_KEY) === 'dark'
        if (!hasUserPreference) {
          theme.value = e.matches ? 'dark' : 'light'
          applyTheme()
        }
      }
      mediaQuery.addEventListener('change', mediaListener)
    } catch {
      /* matchMedia 可能不支持 */
    }
  }

  /**
   * 清理系统主题监听器
   */
  function cleanupSystemThemeListener(): void {
    if (mediaQuery && mediaListener) {
      mediaQuery.removeEventListener('change', mediaListener)
      mediaQuery = null
      mediaListener = null
    }
  }

  /**
   * 初始化紧凑模式状态
   */
  function initCompactState(): void {
    try {
      const saved = localStorage.getItem(COMPACT_KEY)
      if (saved === 'true') {
        isCompact.value = true
        document.documentElement.classList.add('compact')
      } else {
        isCompact.value = false
        document.documentElement.classList.remove('compact')
      }
    } catch {
      /* localStorage 可能不可用 */
    }
  }

  // ── 公开方法 ──────────────────────────────────────────────────

  /**
   * 切换亮/暗主题
   */
  function toggleTheme(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    try { localStorage.setItem(STORAGE_KEY, theme.value) } catch { /* ignore */ }
    applyTheme()
  }

  /**
   * 设置指定主题
   *
   * @param t - 目标主题 ('light' | 'dark')
   */
  function setTheme(t: Theme): void {
    theme.value = t
    try { localStorage.setItem(STORAGE_KEY, theme.value) } catch { /* ignore */ }
    applyTheme()
  }

  /**
   * 切换紧凑模式
   */
  function toggleCompact(): void {
    isCompact.value = !isCompact.value
    try {
      localStorage.setItem(COMPACT_KEY, String(isCompact.value))
    } catch {
      /* localStorage 可能不可用 */
    }
    document.documentElement.classList.toggle('compact', isCompact.value)
  }

  // ── 响应式监听 ────────────────────────────────────────────────

  // 监听主题变化并自动应用到 DOM + 持久化
  watch(theme, (t) => {
    applyThemeToDom(t)
  })

  // ── 生命周期 ──────────────────────────────────────────────────

  onMounted(() => {
    listenerRefCount++
    initThemeState()
    initCompactState()
  })

  onUnmounted(() => {
    listenerRefCount--
    if (listenerRefCount <= 0) {
      cleanupSystemThemeListener()
      listenerRefCount = 0
    }
  })

  // ── 返回值 ────────────────────────────────────────────────────

  const isDark = computed(() => theme.value === 'dark')

  return {
    theme,
    isDark,
    isCompact: isCompact as unknown as Readonly<Ref<boolean>>,
    toggleTheme,
    setTheme,
    toggleCompact,
  }
}

/**
 * 获取当前是否为暗色主题（只读 computed）
 *
 * @deprecated 推荐使用 useTheme().isDark
 * @returns 只读的 isDark 响应式引用
 */
export function isDarkComputed(): Readonly<Ref<boolean>> {
  return computed(() => theme.value === 'dark')
}
