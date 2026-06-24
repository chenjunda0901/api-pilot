import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import { useTabsStore } from '@/stores/tabsStore'
import { RoutePaths } from '@/router/paths'
import type { BreadcrumbItem } from '@/components/common/BreadcrumbNav.vue'

/** 路由 path 段 → 中文模块名映射 */
const segmentLabels: Record<string, string> = {
  dashboard: '工作台',
  apis: '接口管理',
  scenes: '场景测试',
  reports: '测试报告',
  'mock-rules': 'Mock 规则',
  settings: '设置',
  'recycle-bin': '回收站',
  'test-tool': 'API 测试工具',
  'test-history': '测试历史',
  shared: '分享',
  'shared-docs': 'API 文档',

  detail: '详情',
  case: '用例',
  diff: '对比',
}

/** 不需要作为面包屑层级的段 */
const skipSegments = new Set(['projects'])

/**
 * 根据当前路由自动生成面包屑层级
 * 格式：项目名 > 模块名 > 页面名
 */
export function useBreadcrumb() {
  const route = useRoute()
  const projectStore = useProjectStore()
  const tabsStore = useTabsStore()

  const items = computed<BreadcrumbItem[]>(() => {
    const result: BreadcrumbItem[] = []

    // 1. 项目名
    const projectId = route.params.id
    if (projectId) {
      const project = projectStore.projects.find(p => p.id === Number(projectId))
      result.push({
        label: project?.name || `项目 ${projectId}`,
        to: RoutePaths.apiList(projectId),
      })
    }

    // 2. 从路径段生成模块名
    const pathSegments = route.path.split('/').filter(Boolean)
    let accumulatedPath = ''

    for (let i = 0; i < pathSegments.length; i++) {
      const seg = pathSegments[i]
      accumulatedPath += '/' + seg

      // 跳过 projects 段和项目 ID 段
      if (skipSegments.has(seg)) continue
      if (seg === String(route.params.id)) continue
      // 跳过动态参数段（纯数字或长 ID）
      if (/^\d+$/.test(seg)) continue

      let label = segmentLabels[seg] || seg

      // 如果是详情页，尝试从标签页获取名称
      if (seg === 'detail' || seg === 'case') {
        const activeTab = tabsStore.tabs.find(t => t.key === tabsStore.activeTab)
        if (activeTab?.label) {
          label = activeTab.label
        }
      }

      // 最后一项不需要链接（当前页）
      const isLast = i === pathSegments.length - 1 || isLastMeaningfulSegment(i, pathSegments, route)
      result.push({
        label,
        ...(isLast ? {} : { to: accumulatedPath }),
      })
    }

    return result
  })

  return { items }
}

/** 判断是否为最后一个有意义的路径段（后面只有数字 ID 或 detail/case 等） */
function isLastMeaningfulSegment(index: number, segments: string[], route: ReturnType<typeof useRoute>): boolean {
  for (let i = index + 1; i < segments.length; i++) {
    const seg = segments[i]
    if (skipSegments.has(seg)) continue
    if (seg === String(route.params.id)) continue
    if (/^\d+$/.test(seg)) continue
    // 如果后面还有有意义的段，当前不是最后一个
    return false
  }
  return true
}
