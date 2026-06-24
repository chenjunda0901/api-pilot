import { defineStore } from 'pinia'
import { ref } from 'vue'
import { setMemoryToken } from '../api/request'
import { logger } from '../utils/logger'
import { STORAGE_KEYS } from '../constants/events'

/** 待登录后自动重试的请求（Promise 模式） */
type PendingRetry = {
  resolve: () => void
  reject: (err: unknown) => void
}

export const useHintBarStore = defineStore('hintBar', () => {
  const visible = ref(false)
  const actionName = ref('')
  /** 待重试队列，登录成功后依次 resolve 触发重发 */
  const pendingRetries = ref<PendingRetry[]>([])
  /** 登录子窗口引用 */
  let loginWindow: Window | null = null
  /** 轮询登录状态定时器 */
  let pollTimer: ReturnType<typeof setInterval> | null = null

  function show(name: string) {
    actionName.value = name
    visible.value = true
  }

  function dismiss() {
    visible.value = false
    actionName.value = ''
  }

  /**
   * 注册一个待重试请求。调用方 await waitUntilLoggedIn() 即可在登录成功后继续。
   * 如果用户拒绝登录（关闭提示栏），Promise 永远不会 resolve，
   * 但由于 401 场景下原始请求已失败，调用方会自然走 catch 分支。
   */
  function waitUntilLoggedIn(): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      pendingRetries.value.push({ resolve, reject })
    })
  }

  /**
   * 用新窗口打开登录页。登录成功后：
   * 1. 原页面通过 localStorage 跨标签页感知登录状态变化
   * 2. 轮询检测到 access_token 后自动恢复认证
   * 3. resolve 所有等待中的请求，触发自动重试
   */
  function goLogin() {
    const currentHash = window.location.hash || ''
    // 将当前页面路径存入 sessionStorage，登录后知道要刷新哪个页面
    sessionStorage.setItem(STORAGE_KEYS.LOGIN_REDIRECT_HASH, currentHash)

    dismiss()

    // 开新窗口
    loginWindow = window.open('/#/login?from=hint', '_blank', 'width=480,height=640,menubar=no,toolbar=no,location=no')
    if (!loginWindow) {
      // 弹窗被拦截，回退到当前窗口跳转
      window.location.href = '/#/login?redirect=' + encodeURIComponent(currentHash)
      return
    }

    // 轮询：检测登录子窗口是否完成登录
    startPolling()
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(() => {
      if (loginWindow?.closed) {
        stopPolling()
        loginWindow = null
        return
      }
      void import('../api/request').then(async ({ default: req }) => {
        try {
          const res = await req.post('/auth/refresh', {})
          const data = res.data
          if (data?.access_token) {
            setMemoryToken(data.access_token)
            stopPolling()
            if (loginWindow && !loginWindow.closed) {
              loginWindow.close()
            }
            loginWindow = null
            onLoginSuccess()
          }
        } catch (err) {
          logger.error('[hintBarStore] refresh token in poll failed:', err)
        }
      })
    }, 1000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  /** 登录成功后的回调：resolve 所有等待中的请求 + 刷新页面数据 */
  function onLoginSuccess() {
    // 唤醒所有等待中的请求重试
    const retries = [...pendingRetries.value]
    pendingRetries.value = []
    retries.forEach(({ resolve }) => resolve())

    // 刷新用户信息（触发 Pinia store 更新）
    void import('./userStore').then(async ({ useUserStore }) => {
      try {
        const userStore = useUserStore()
        await userStore.fetchUserInfo()
      } catch (err) { logger.error('[hintBarStore] fetch user info failed:', err); /* ignore */ }
    })

    // 500ms 后刷新当前页面（让所有组件用新 token 重新加载数据）
    setTimeout(() => {
      window.location.reload()
    }, 500)
  }

  /** 登出时清理状态：关闭登录子窗口、停止轮询、清空待重试队列 */
  function resetState() {
    stopPolling()
    if (loginWindow && !loginWindow.closed) {
      loginWindow.close()
    }
    loginWindow = null
    const retries = [...pendingRetries.value]
    pendingRetries.value = []
    retries.forEach(({ reject }) => reject(new Error('logged out')))
    visible.value = false
    actionName.value = ''
  }

  return {
    visible,
    actionName,
    pendingRetries,
    show,
    dismiss,
    goLogin,
    waitUntilLoggedIn,
    resetState,
  }
})
