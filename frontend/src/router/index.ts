import { ref } from "vue"
import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router"
import { logger } from "@/utils/logger"
import request, { getMemoryToken, refreshToken } from "../api/request"

export const routeLoading = ref(false)


// Extend RouteMeta
declare module "vue-router" {
  interface RouteMeta {
    title?: string
    transition?: string
    requireAuth?: boolean // 标记该路由是否必须登录（注意：无末尾 s）
    public?: boolean // 标记该路由允许未登录访问（覆盖父级 requireAuth）
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/LoginView.vue"),
    meta: { title: "登录" },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("../views/RegisterView.vue"),
    meta: { title: "注册" },
  },
  {
    path: "/shared/:token",
    name: "SharedReport",
    component: () => import("../views/SharedReportView.vue"),
    meta: { title: "分享报告" },
  },
  {
    path: "/shared-docs/:token",
    name: "SharedDocs",
    component: () => import("../views/SharedDocsView.vue"),
    meta: { title: "API 文档" },
    // 不需要登录即可访问
  },
  {
    path: "/",
    component: () => import("../layout/AppLayout.vue"),
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("../views/DashboardView.vue"),
        meta: { title: "工作台", public: true },
      },
      {
        path: "projects/:id/apis",
        name: "Apis",
        component: () => import("../views/ApiListView.vue"),
        meta: { title: "接口管理", public: true },
      },
      {
        path: "projects/:id/apis/test-tool",
        name: "ApiTestTool",
        component: () => import("../components/ApiTestTool.vue"),
        meta: { title: "API 测试工具", public: true },
      },
      {
        path: "projects/:id/apis/detail/:apiId",
        name: "ApiDetail",
        component: () => import("../views/ApiDetail.vue"),
        meta: { title: "接口详情", public: true },
      },
      {
        path: "projects/:id/apis/:apiId/test-history",
        name: "ApiTestHistory",
        component: () => import("../views/ApiTestHistoryView.vue"),
        meta: { title: "接口测试历史", public: true },
      },
      {
        path: "projects/:id/apis/case/:caseId",
        name: "CaseDetail",
        component: () => import("../views/CaseDetail.vue"),
        meta: { title: "用例详情", public: true },
      },
      {
        path: "projects/:id/scenes",
        name: "Scenes",
        component: () => import("../views/ScenesView.vue"),
        meta: { title: "场景测试", public: true },
      },
      {
        path: "projects/:id/reports",
        name: "Reports",
        component: () => import("../views/ReportsView.vue"),
        meta: { title: "测试报告", public: true },
      },
      {
        path: "projects/:id/reports/:reportId",
        name: "ReportDetail",
        component: () => import("../views/ReportDetailView.vue"),
        meta: { title: "报告详情", public: true },
      },
      {
        path: "projects/:id/mock-rules",
        name: "MockRules",
        component: () => import("../views/MockRulesView.vue"),
        meta: { title: "Mock 规则", public: true },
      },
      {
        path: "projects/:id/settings",
        name: "Settings",
        component: () => import("../views/SettingsView.vue"),
        meta: { title: "设置", requireAuth: true },
      },
      {
        path: "projects/:id/recycle-bin",
        name: "RecycleBin",
        component: () => import("../views/RecycleBinView.vue"),
        meta: { title: "回收站", requireAuth: true },
      },

      {
        path: '/projects',
        redirect: '/dashboard',
      },
    ],
  },
  {
    path: "/404",
    name: "NotFound",
    component: () => import("../views/NotFoundView.vue"),
    meta: { title: "页面未找到" },
  },
  { path: "/:pathMatch(.*)*", redirect: "/404" },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

let _authReady = false
let _authCheckPromise: Promise<boolean> | null = null

/** 供 userStore.logout() 调用，登出时重置认证状态 */
export function resetAuthState(): void {
  _authReady = false
  _authCheckPromise = null
}

/** 供 userStore.login/register 成功后调用，标记认证已就绪 */
export function markAuthReady(): void {
  _authReady = true
  _authCheckPromise = null
}

function getRefreshTokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|; )api_pilot_refresh_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

/**
 * ★ 重要：httpOnly cookie JS 永远读不到，所以不能用 document.cookie 判断
 * "是否可能有 refresh_token"。改用 localStorage 中持久化的 user 对象作
 * 代理信号：有 user → 曾经登录过 → 浏览器可能还持有 refresh cookie →
 * 发请求让后端裁决；无 user → 从未登录 → 跳过 refresh。
 */
function hasLikelyRefreshToken(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return !!localStorage.getItem('user')
  } catch {
    return false
  }
}

async function _ensureAuthReady(): Promise<boolean> {
  if (_authReady) return true
  if (_authCheckPromise) return _authCheckPromise

  _authCheckPromise = (async () => {
    // 用 user localStorage 代理信号判断是否值得尝试 refresh
    // ★ 关键：不能用 getRefreshTokenFromCookie() — httpOnly cookie 永远读不到
    const likelyHadToken = hasLikelyRefreshToken()
    if (!likelyHadToken) {
      return false
    }

    // 复用 request.ts 中的 refreshToken()：统一刷新逻辑，自带并发锁、重试、httpOnly cookie 支持
    const refreshed = await refreshToken()
    if (refreshed) {
      // token 刷新成功后同步加载用户信息，避免 userStore.user 为 null 导致
      // 登录按钮显示但路由守卫又把 /login 跳转拦截的不一致状态
      try {
        const { useUserStore } = await import("../stores/userStore")
        const store = useUserStore()
        await store.fetchUserInfo()
        // 同步更新 store.accessToken，确保 isTokenReady 计算属性与 memoryToken 一致
        const { getMemoryToken: getMemToken } = await import("../api/request")
        store.setAccessToken(getMemToken())
      } catch (err) {
        logger.error('[router] fetch user info failed:', err)
        /* 静默失败，用户后续可手动登录 */
      }
      return true
    }

    // refresh 失败：检查内存中是否已有有效 token（如刚登录设置）
    const hasMemoryToken = (() => { try { return !!getMemoryToken() } catch { return false } })()
    if (hasMemoryToken) {
      // 内存已有 token（刚登录或已有有效 session）：不清除，视为已就绪
      _authReady = true
      _authCheckPromise = null
      return true  // 有内存 token，视为认证就绪
    }

    // 之前没有 refresh token 凭据（首次访问且从未登录过）：清除残留状态
    if (!likelyHadToken) {
      _authReady = true
      _authCheckPromise = null
      try {
        const { setMemoryToken: setMemToken } = await import("../api/request")
        setMemToken(null)
      } catch { /* 静默失败 */ }
      // 清除残留的 user 数据，确保 UI 与认证状态一致
      try {
        const { useUserStore } = await import("../stores/userStore")
        const store = useUserStore()
        if (store.user) {
          store.user = null
          store.setAccessToken(null)
          try { localStorage.removeItem("user") } catch { /* ignore */ }
          try { localStorage.removeItem("access_token") } catch { /* ignore */ }
        }
      } catch { /* 静默失败 */ }
    }

    return false
  })()

  const result = await _authCheckPromise
  _authReady = result // 只有 auth 真正成功才缓存，否则下次继续尝试
  if (!result) {
    _authCheckPromise = null // 失败时重置，允许下次重试
  }
  return result
}

router.beforeEach((to) => {
  // 同步设置页面标题，在异步守卫之前执行
  const title = to.meta?.title
  if (title) {
    document.title = `${title} - API Pilot`
  }
})

router.beforeEach(async (to) => {
  routeLoading.value = true

  const isAuthPage = to.path === "/login" || to.path === "/register"
  // 登录/注册页不先发起 refresh 校验，避免未登录状态下 401 等待阻塞路由组件挂载。
  const isAuthenticated = isAuthPage ? false : await _ensureAuthReady()
  const _hasToken =
    isAuthenticated ||
    (() => {
      try {
        return !!getMemoryToken()
      } catch {
        return false
      }
    })()
  // 已登录用户访问登录/注册页
  // 注意：对 auth 页面进行严格校验，避免因 _authReady 缓存或 localStorage 残留数据
  // 导致未登录用户被误判为"已登录"而强制跳转
  if (to.path === "/login" || to.path === "/register") {
    const memoryToken = (() => { try { return !!getMemoryToken() } catch { return false } })()
    if (memoryToken) {
      // 有内存 token：通过实时 API 调用验证 session 是否仍然有效
      // 避免仅依赖 _authReady 缓存或 localStorage 残留数据导致误判
      let actuallyLoggedIn = false
      try {
        const { useUserStore } = await import("../stores/userStore")
        const store = useUserStore()
        // 强制调用 fetchUserInfo() 进行实时验证，无论 store.user 是否已有值
        // 若 session 已过期，API 会返回 401/403，catch 分支会将 actuallyLoggedIn 保持为 false
        await store.fetchUserInfo()
        if (store.user) {
          actuallyLoggedIn = true
        }
      } catch (e: unknown) {
        // 区分网络错误和认证错误：
        // - 网络错误（无 response）：用户可能仍处于登录状态，不应清除认证缓存，
        //   基于内存 token 仍视为已登录，避免网络抖动导致已登录用户看到登录页
        // - 认证错误（401/403）：session 已失效，清除缓存
        const errResp = (e as { response?: { status?: number } })?.response
        if (!errResp) {
          // 网络故障：内存有 token 则仍视为已登录
          actuallyLoggedIn = true
        } else {
          // 认证失败：清除过期的认证状态，避免后续导航继续使用缓存
          _authReady = false
          _authCheckPromise = null
        }
      }
      if (actuallyLoggedIn) {
        routeLoading.value = false
        // 登录页直接重定向到首页
        if (to.path === "/login") {
          return "/"
        }
        // 注册页：弹出确认框询问用户是否要注册新账号
        if (to.path === "/register") {
          try {
            const { ElMessageBox } = await import("element-plus")
            await ElMessageBox.confirm(
              "您已登录，确定要注册新账号吗？注册前将自动退出当前账号。",
              "提示",
              {
                confirmButtonText: "去注册",
                cancelButtonText: "取消",
                type: "info",
              }
            )
            // 用户确认：先登出，然后继续前往注册页
            const { useUserStore: useUserStore2 } = await import("../stores/userStore")
            const store2 = useUserStore2()
            await store2.logout()
            return true
          } catch {
            // 用户取消：中止导航
            return false
          }
        }
      }
    }
  }
  // 路由级认证守卫：requireAuth 标记的路由必须登录才能访问
  // 注意：public=true 路由（如 Dashboard、种子项目内的只读页面）跳过此检查
  if (!to.meta.public && to.meta.requireAuth && !_hasToken) {
    routeLoading.value = false
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  routeLoading.value = false
})

router.afterEach(() => {
  routeLoading.value = false
})

router.onError(() => {
  routeLoading.value = false
})

// Unsaved changes guard — warn before navigating away from dirty tabs
router.beforeEach(async (to, from) => {
  try {
    const { useTabsStore } = await import("../stores/tabsStore")
    const tabsStore = useTabsStore()
    const fromKey = _routeToTabKey(from)
    if (fromKey && tabsStore.isDirty(fromKey)) {
      const { ElMessageBox } = await import("element-plus")
      try {
        await ElMessageBox.confirm(
          "当前页面有未保存的更改，离开后将丢失。是否继续？",
          "未保存的更改",
          { confirmButtonText: "离开", cancelButtonText: "留下", type: "warning" }
        )
        tabsStore.markClean(fromKey)
      } catch {
        return false
      }
    }
  } catch {
    // skip guard
  }
})
function _routeToTabKey(route: { params: Record<string, string | string[]>; path: string }): string | null {
  const apiId = route.params?.apiId
  if (apiId) return `api-${apiId}`
  const caseId = route.params?.caseId
  if (caseId) return `case-${caseId}`
  return null
}
export default router