import { ref, onUnmounted } from 'vue'

/**
 * 页面加载状态管理
 *
 * 功能：
 * 1. 首次加载时显示 loading 状态
 * 2. 支持手动控制 loading（用于异步操作）
 * 3. 超时保护：最长 5 秒自动隐藏
 */
export function useAppLoading() {
  const pageLoading = ref(false)
  let loadingTimer: ReturnType<typeof setTimeout> | null = null
  let timeoutTimer: ReturnType<typeof setTimeout> | null = null
  let isFirstLoad = true
  let loadCount = 0

  function showLoading() {
    loadCount++
    pageLoading.value = true

    // 清除之前的定时器
    if (loadingTimer) { clearTimeout(loadingTimer); loadingTimer = null }
    if (timeoutTimer) { clearTimeout(timeoutTimer); timeoutTimer = null }

    // 超时保护：5 秒后自动隐藏
    timeoutTimer = setTimeout(() => {
      pageLoading.value = false
      timeoutTimer = null
    }, 5000)

    // 首次加载延迟隐藏
    if (isFirstLoad) {
      isFirstLoad = false
      loadingTimer = setTimeout(() => {
        pageLoading.value = false
        loadingTimer = null
        if (timeoutTimer) { clearTimeout(timeoutTimer); timeoutTimer = null }
      }, 800)
    }
  }

  function hideLoading() {
    loadCount = Math.max(0, loadCount - 1)
    if (loadCount === 0) {
      pageLoading.value = false
    }
    if (loadingTimer) { clearTimeout(loadingTimer); loadingTimer = null }
    if (timeoutTimer) { clearTimeout(timeoutTimer); timeoutTimer = null }
  }

  onUnmounted(() => {
    if (loadingTimer) clearTimeout(loadingTimer)
    if (timeoutTimer) clearTimeout(timeoutTimer)
  })

  return { pageLoading, showLoading, hideLoading, isFirstLoad }
}
