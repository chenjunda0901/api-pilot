import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTabsStore } from '../stores/tabsStore'
import { useProjectStore } from '../stores/projectStore'

export function useAppProjectWatcher() {
  const route = useRoute()
  const router = useRouter()
  const tabsStore = useTabsStore()
  const projectStore = useProjectStore()

  const projectId = computed(() => {
    const p = route.params.id
    return p ? Number(p) : undefined
  })

  // 仅在 API 根路由下，根据当前项目的 API/Case 标签恢复到最后活跃标签
  watch(
    [() => route.path, () => tabsStore.tabs.length],
    ([path, tabCount]) => {
      const currentPid = Number(route.params.id)
      const apisBase = `/projects/${currentPid}/apis`
      const isApiDetail = /\/apis\/(detail|case)\//.test(path)
      if (path !== apisBase || tabCount === 0 || isApiDetail) return

      const projectTabs = tabsStore.tabs.filter(
        t => (!t.projectId || t.projectId === currentPid) && (t.type === 'api' || t.type === 'case')
      )
      if (projectTabs.length === 0) return

      const active = projectTabs.find(t => t.key === tabsStore.activeTab)
      const target = active?.type === 'api' && active?.apiId
        ? active
        : projectTabs.find(t => t.type === 'api' && t.apiId) || projectTabs[0]

      if (target?.type === 'api' && target?.apiId && target.apiId !== 'new') {
        router.replace(`/projects/${currentPid}/apis/detail/${target.apiId}`).catch(() => {})
      }
    },
    { immediate: true }
  )

  // 切换项目时清除不属于新项目的标签页
  watch(
    () => projectStore.currentProjectId,
    (newId, oldId) => {
      if (newId && oldId && newId !== oldId) {
        // 移除属于旧项目的标签（保留无 projectId 的兼容旧标签）
        const staleTabs = tabsStore.tabs.filter(
          t => t.projectId && t.projectId !== newId
        )
        staleTabs.forEach(t => tabsStore.removeTab(t.key))
        // 如果没有剩余标签，完全清除
        if (tabsStore.tabs.length === 0) {
          tabsStore.closeAll()
        }
        try {
          localStorage.removeItem("api_pilot_tabs_cleared")
        } catch { /* localStorage 不可用 */ }
      }
    }
  )

  // 路由里的 projectId 变化时同步到 projectStore（直接 URL 跳转场景）
  watch(
    () => route.params.id,
    (idRaw) => {
      const id = idRaw ? Number(idRaw) : null
      if (!id) return
      // 项目列表尚未加载完成时不要强行设置（fetchProjects 内有兜底逻辑）
      if (projectStore.projects.length === 0) return
      // 当前项目 ID 已是该值则跳过
      if (projectStore.currentProjectId === id) return
      // 校验该 id 真实存在（防止被篡改/无效 URL）
      if (!projectStore.projects.some(p => p.id === id)) return
      projectStore.setCurrentProject(id)
    }
  )

  // 项目列表加载完成后，如果路由里的 projectId 与当前 projectStore 不一致，强制同步
  watch(
    () => projectStore.projects.length,
    () => {
      const idRaw = route.params.id
      const id = idRaw ? Number(idRaw) : null
      if (!id) return
      if (projectStore.currentProjectId === id) return
      if (!projectStore.projects.some(p => p.id === id)) return
      projectStore.setCurrentProject(id)
    }
  )

  return { projectId }
}
