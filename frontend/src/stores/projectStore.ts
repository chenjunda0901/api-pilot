import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { listProjects, createProject as createProjectApi, getProject, forkSeedProject } from "@/api/projects"
import { logger } from "@/utils/logger"
import { msgError, msgInfo, msgSuccess } from "@/utils/message"
import type { Project, ApiResponse } from "../types"
import { STORAGE_KEYS } from "../constants/events"
import { useApiStore } from "./apiStore"
import { useEnvStore } from "./envStore"
import { useTabsStore } from "./tabsStore"
import { useReentrancyGuard } from "../composables/useReentrancyGuard"
import { useUserStore } from "./userStore"

export const useProjectStore = defineStore("project", () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<number | null>(null)
  const loading = ref(false)
  const autoForking = ref(false)
  const { isRunning: isCreating, guard } = useReentrancyGuard()

  /** 当前选中的项目对象（与 currentProjectId 联动） */
  const currentProject = computed<Project | null>(() => {
    if (currentProjectId.value == null) return null
    return projects.value.find((p) => p.id === currentProjectId.value) ?? null
  })

  /**
   * 只读模式：当前项目是种子演示模板（global_demo=1）。
   * 种子项目对所有用户（含 admin）只读，需修改时用户应 fork 到自己的私有副本。
   */
  const isReadOnly = computed(() => currentProject.value?.global_demo === 1)

  const hasPrivateProject = computed(() => {
    return projects.value.some((p) => (p.global_demo ?? 0) !== 1)
  })

  async function fetchProjects(page?: number, page_size?: number) {
    loading.value = true
    try {
      const params: { page?: number; page_size?: number } = {}
      if (page !== undefined) params.page = page
      if (page_size !== undefined) params.page_size = page_size
      const res = (await listProjects(params)) as unknown as ApiResponse<{ items: Project[]; total: number; page: number; page_size: number }>
      const data = res.data
      projects.value = data?.items || []

      const userStore = useUserStore()
      const isLoggedIn = !!userStore.user

      // 自动恢复上次使用的项目
      if (!currentProjectId.value && projects.value.length > 0) {
        const lastId = localStorage.getItem(STORAGE_KEYS.LAST_PROJECT_ID)
        if (lastId && projects.value.some((p) => p.id === Number(lastId))) {
          currentProjectId.value = Number(lastId)
          try { localStorage.setItem(STORAGE_KEYS.LAST_PROJECT_ID, String(currentProjectId.value)) } catch {}
        } else {
          // 优先选择有场景内容的私有项目（global_demo !== 1），跳过公共演示项目
          const privateProjects = projects.value.filter((p: Project) => p.global_demo !== 1)
          const withScenes = privateProjects.find((p: Project) => (p.scene_count ?? 0) > 0)
          currentProjectId.value = withScenes?.id ?? privateProjects[0]?.id ?? projects.value[0]?.id ?? null
          try { localStorage.setItem(STORAGE_KEYS.LAST_PROJECT_ID, String(currentProjectId.value)) } catch {}
        }
      }

      // 新用户自动 Fork：已登录但无任何私有项目时，自动从种子模板创建私有副本
      if (isLoggedIn && !hasPrivateProject.value && !autoForking.value) {
        void autoForkSeed()
      }
    } catch (err) {
      logger.error('[projectStore] fetchProjects failed:', err)
      msgError('加载项目列表失败')
      projects.value = []
    } finally {
      loading.value = false
    }
  }

  async function autoForkSeed() {
    if (autoForking.value) return
    autoForking.value = true
    try {
      const userStore = useUserStore()
      if (!userStore.user) return

      logger.info('[projectStore] Auto-forking seed project for new user')
      const res = await forkSeedProject()
      const data = (res as unknown as { data: { id: number; name: string; is_new: boolean; message: string } }).data

      if (data?.id) {
        // 刷新项目列表
        await fetchProjects(1, 50)
        // 自动切换到新的私有项目
        if (projects.value.some((p) => p.id === data.id)) {
          currentProjectId.value = data.id
          try {
            localStorage.setItem(STORAGE_KEYS.LAST_PROJECT_ID, String(data.id))
          } catch { /* ignored */ }
        }
        if (data.is_new) {
          msgSuccess('已为您创建私有演示副本，可自由编辑所有内容')
        }
        logger.info('[projectStore] Auto-fork completed:', data)
      }
    } catch (err) {
      logger.error('[projectStore] autoForkSeed failed:', err)
      // 自动 Fork 失败不影响用户使用，静默处理（用户可手动 Fork）
    } finally {
      autoForking.value = false
    }
  }

  async function createProject(name: string, isPublic = false): Promise<Project | null> {
    return guard(async () => {
      try {
        const res = (await createProjectApi({ name, is_public: isPublic })) as unknown as ApiResponse<Project>
        if (res.data) {
          projects.value.push(res.data)
          currentProjectId.value = res.data.id
          return res.data
        }
      } catch (err) {
        logger.error('[projectStore] createProject failed:', err)
        msgError('创建项目失败')
        // Error handled by interceptor
      }
      return null
    })
  }

  /**
   * 加载指定项目的详情（含 role 字段），并合并到 projects 列表中。
   * 用于：项目不在列表第一页，但需要正确的 role 权限判断时。
   */
  async function fetchProjectDetail(projectId: number): Promise<Project | null> {
    try {
      const res = (await getProject(projectId)) as unknown as ApiResponse<Project>
      if (res.data) {
        const idx = projects.value.findIndex((p) => p.id === projectId)
        if (idx >= 0) {
          projects.value[idx] = { ...projects.value[idx], ...res.data }
        } else {
          projects.value.push(res.data)
        }
        return res.data
      }
    } catch (err) {
      logger.error('[projectStore] fetchProjectDetail failed:', err)
    }
    return null
  }

  function setCurrentProject(id: number) {
    const oldId = currentProjectId.value
    currentProjectId.value = id
    try {
      localStorage.setItem(STORAGE_KEYS.LAST_PROJECT_ID, String(id))
    } catch {
      /* Ignored */
    }
    // 切换项目时清除各关联 store 的缓存，避免项目间数据泄漏
    if (id !== oldId) {
      const apiStore = useApiStore()
      const envStore = useEnvStore()
      const tabsStore = useTabsStore()
      apiStore.clearCache()
      envStore.resetState()
      tabsStore.resetState()
    }
    // 自动加载环境配置
    if (id) {
      const envStore = useEnvStore()
      void envStore.fetchEnvs(id)
      void envStore.fetchGlobalConfig(id)
    }
    // 如果项目不在列表中（可能在后续分页），主动加载详情以获取 role 等信息
    const existing = projects.value.find((p) => p.id === id)
    if (!existing || !existing.role) {
      void fetchProjectDetail(id)
    }
  }

  function resetState() {
    projects.value = []
    currentProjectId.value = null
    loading.value = false
    try { localStorage.removeItem(STORAGE_KEYS.LAST_PROJECT_ID) } catch { /* ignored */ }
  }

  return {
    projects,
    currentProjectId,
    currentProject,
    isReadOnly,
    loading,
    isCreating,
    autoForking,
    hasPrivateProject,
    fetchProjects,
    fetchProjectDetail,
    createProject,
    autoForkSeed,
    setCurrentProject,
    resetState,
  }
})
