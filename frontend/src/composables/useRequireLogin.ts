import { useUserStore } from '../stores/userStore'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { STORAGE_KEYS } from '../constants/events'

export type LoginDialogType = 'login' | 'expired'

export interface RequireLoginOptions {
  actionName?: string
  type?: LoginDialogType
  showDialog?: boolean
}

export function useRequireLogin() {
  const userStore = useUserStore()
  const router = useRouter()
  const route = useRoute()

  function getRedirectPath(): string {
    return route.fullPath || window.location.pathname + window.location.search || '/'
  }

  function goLogin(redirect?: string): void {
    const target = redirect || getRedirectPath()
    void router.push({ path: '/login', query: { redirect: target } })
  }

  async function showLoginDialog(actionName: string, type: LoginDialogType = 'login'): Promise<boolean> {
    const content = type === 'expired'
      ? `登录状态已过期，「${actionName}」需要重新登录后方可执行。`
      : `「${actionName}」需要登录后方可执行，是否前往登录？`
    try {
      await ElMessageBox.confirm(content, '提示', {
        confirmButtonText: '去登录',
        cancelButtonText: '取消',
        type: type === 'expired' ? 'warning' : 'info',
      })
      goLogin()
      return false
    } catch {
      return false
    }
  }

  function showLoginToast(type: LoginDialogType = 'login'): void {
    const msg = type === 'expired' ? '登录状态已失效，请重新登录' : '请先登录后再操作'
    ElMessage.warning(msg)
  }

  async function requireLogin(options: RequireLoginOptions | string = {}): Promise<boolean> {
    const opts: RequireLoginOptions = typeof options === 'string' ? { actionName: options } : options
    const { actionName = '此操作', type: preferredType, showDialog = true } = opts

    if (!userStore.user) {
      if (showDialog) {
        await showLoginDialog(actionName, 'login')
      } else {
        showLoginToast('login')
        goLogin()
      }
      return false
    }

    const tokenOk = await userStore.ensureToken()
    if (!tokenOk) {
      userStore.user = null
      try { localStorage.removeItem(STORAGE_KEYS.USER) } catch { /* ignore */ }
      try { localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN) } catch { /* ignore */ }

      const actualType: LoginDialogType = preferredType || 'expired'
      if (showDialog) {
        await showLoginDialog(actionName, actualType)
      } else {
        showLoginToast(actualType)
        goLogin()
      }
      return false
    }

    return true
  }

  function withLogin<T extends (...args: unknown[]) => unknown>(
    action: T,
    actionName: string,
  ): (...args: Parameters<T>) => Promise<ReturnType<T> | void> {
    return async (...args: Parameters<T>) => {
      if (!await requireLogin(actionName)) return
      return action(...args) as ReturnType<T>
    }
  }

  return {
    requireLogin,
    withLogin,
    showLoginDialog,
    showLoginToast,
    goLogin,
    getRedirectPath,
  }
}
