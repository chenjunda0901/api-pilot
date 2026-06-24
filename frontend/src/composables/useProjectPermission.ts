import { computed } from 'vue'
import { useProjectStore } from '../stores/projectStore'
import { useUserStore } from '../stores/userStore'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { forkSeedProject } from '../api/projects'
import { logger } from '../utils/logger'
import { msgSuccess } from '../utils/message'

const READ_ONLY_ROLES = ['viewer', 'read', 'guest']
const EDIT_ROLES = ['editor', 'owner', 'admin']
const MANAGE_ROLES = ['owner', 'admin']
const MEMBER_ROLES = ['member', 'editor', 'owner', 'admin']

function roleLevel(role: string): number {
  const levels: Record<string, number> = {
    viewer: 1,
    guest: 1,
    read: 1,
    member: 2,
    editor: 3,
    owner: 4,
    admin: 5,
  }
  return levels[role.toLowerCase()] || 0
}

export function useProjectPermission() {
  const projectStore = useProjectStore()
  const userStore = useUserStore()
  const route = useRoute()
  const router = useRouter()

  const projectId = computed(() => {
    const routeId = route.params.id
    if (routeId) return Number(routeId)
    return projectStore.currentProjectId
  })

  const currentProject = computed(() =>
    projectStore.projects.find((p) => p.id === projectId.value),
  )

  const projectRole = computed(() => {
    const user = userStore.user
    const project = currentProject.value
    if (!user || !project) return null

    if (user.role === 'admin') return 'admin'
    if (project.created_by === user.id) return 'owner'
    return project.role || null
  })

  const isLoggedIn = computed(() => !!userStore.user)

  const isSeedProject = computed(() => {
    const project = currentProject.value
    if (!project) return false
    return (project.global_demo ?? 0) === 1
  })

  const canEdit = computed(() => {
    const user = userStore.user
    const project = currentProject.value
    if (!user || !project) return false

    if (user.role === 'admin') return true
    if (project.created_by === user.id) return true

    if (isSeedProject.value) return false

    const role = projectRole.value
    if (role) {
      return roleLevel(role) >= roleLevel('editor')
    }

    if (project.is_public) return false
    return false
  })

  const canView = computed(() => {
    const project = currentProject.value
    if (!project) return false

    if (isSeedProject.value) return true
    if (project.is_public) return true

    const user = userStore.user
    if (!user) return false
    if (user.role === 'admin') return true
    if (project.created_by === user.id) return true

    return !!projectRole.value
  })

  const canManageMembers = computed(() => {
    const user = userStore.user
    const project = currentProject.value
    if (!user || !project) return false
    if (isSeedProject.value) return false

    if (user.role === 'admin') return true
    if (project.created_by === user.id) return true

    const role = projectRole.value
    if (!role) return false
    return roleLevel(role) >= roleLevel('owner')
  })

  const canManageSettings = computed(() => {
    const user = userStore.user
    const project = currentProject.value
    if (!user || !project) return false
    if (isSeedProject.value) return false

    if (user.role === 'admin') return true
    if (project.created_by === user.id) return true

    const role = projectRole.value
    if (!role) return false
    return roleLevel(role) >= roleLevel('editor')
  })

  const canViewRecycleBin = computed(() => {
    if (isSeedProject.value) return false
    return canEdit.value
  })

  const canExport = computed(() => {
    const user = userStore.user
    const project = currentProject.value
    if (!user || !project) return false

    if (user.role === 'admin') return true
    if (project.created_by === user.id) return true

    if (isSeedProject.value) return true

    const role = projectRole.value
    if (!role) return false
    return roleLevel(role) >= roleLevel('member')
  })

  const canUseMock = computed(() => {
    const project = currentProject.value
    if (!project) return false
    if (isSeedProject.value) return true
    return canView.value
  })

  async function showSeedForkDialog(actionName = '此操作'): Promise<boolean> {
    try {
      const { value: action } = await ElMessageBox({
        title: '种子演示项目为只读',
        message: `${actionName}需要在您的私有副本中进行。是否立即 Fork 一份到您的账号下？`,
        showCancelButton: true,
        confirmButtonText: '立即 Fork',
        cancelButtonText: '取消',
        type: 'info',
        distinguishCancelAndClose: true,
      })
      if (action === 'confirm') {
        await handleForkAndGo()
        return true
      }
      return false
    } catch {
      return false
    }
  }

  async function handleForkAndGo() {
    try {
      const res = await forkSeedProject()
      const data = (res as unknown as { data: { id: number; name: string; is_new: boolean; message: string } }).data
      if (data?.id) {
        await projectStore.fetchProjects(1, 50)
        projectStore.setCurrentProject(data.id)
        const targetPath = `/projects/${data.id}/apis`
        if (router.currentRoute.value.path !== targetPath) {
          void router.push(targetPath)
        }
        if (data.is_new) {
          msgSuccess('已为您创建私有副本，可自由编辑所有内容')
        }
        return data.id
      }
    } catch (err) {
      logger.error('[useProjectPermission] fork failed:', err)
    }
    return null
  }

  async function requireWrite(actionName = '此操作'): Promise<boolean> {
    if (!userStore.user) {
      const { useRequireLogin } = await import('./useRequireLogin')
      const { requireLogin } = useRequireLogin()
      return requireLogin(actionName)
    }

    if (isSeedProject.value) {
      await showSeedForkDialog(actionName)
      return false
    }

    if (!canEdit.value) {
      const { ElMessage } = await import('element-plus')
      ElMessage.warning('您没有该项目的编辑权限')
      return false
    }

    return true
  }

  function withWrite<T extends (...args: unknown[]) => unknown>(
    action: T,
    actionName: string,
  ): (...args: Parameters<T>) => Promise<ReturnType<T> | void> {
    return async (...args: Parameters<T>) => {
      if (!await requireWrite(actionName)) return
      return action(...args) as ReturnType<T>
    }
  }

  return {
    canEdit,
    canView,
    canManageMembers,
    canManageSettings,
    canViewRecycleBin,
    canExport,
    canUseMock,
    projectRole,
    isLoggedIn,
    isSeedProject,
    requireWrite,
    withWrite,
    showSeedForkDialog,
    handleForkAndGo,
  }
}
