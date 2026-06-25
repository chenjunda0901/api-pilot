import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import request from '@/api/request'
import { logger } from '@/utils/logger'
import { msgSuccess } from '@/utils/message'
import { useRequireLogin } from './useRequireLogin'

/**
 * 场景定时调度管理
 *
 * 提供场景的 Cron 定时执行配置：
 * - 加载/保存/取消调度
 * - 快速设置常用 Cron 表达式
 */
export function useSceneSchedule() {
  const route = useRoute()
  const { requireLogin } = useRequireLogin()

  const projectId = computed(() => route.params.id as string)

  const scheduleEnabled = ref(false)
  const scheduleCron = ref('0 0 9 * * *')
  const scheduleSaving = ref(false)

  const cronPresets: Record<string, string> = {
    daily: '0 0 9 * * *',
    hourly: '0 0 * * * *',
    weekdays: '0 0 9 * * 1-5',
  }

  function setQuickCron(type: string) {
    if (cronPresets[type]) scheduleCron.value = cronPresets[type]
  }

  async function loadSchedule(sceneId: number) {
    try {
      const res = await request.get(`/projects/${projectId.value}/scenes/${sceneId}/schedule`)
      scheduleEnabled.value = (res.data && res.data.enabled) || false
      scheduleCron.value = (res.data && res.data.cron) || '0 0 9 * * *'
    } catch (e) {
      logger.warn('[Scenes] Failed to load schedule:', e)
    }
  }

  async function onScheduleToggle(
    val: boolean,
    selectedSceneId: number | undefined,
  ) {
    if (!val) {
      if (!(await requireLogin('取消定时执行'))) return
      try {
        await request.delete(`/projects/${projectId.value}/scenes/${selectedSceneId}/schedule`)
        msgSuccess('已取消定时执行')
      } catch (e) {
        logger.warn('[Scenes] Failed to cancel schedule:', e)
      }
    }
  }

  async function saveSchedule(
    sceneId: number,
    envId?: number | null,
  ) {
    if (!(await requireLogin('保存定时执行'))) return

    scheduleSaving.value = true
    try {
      await request.put(`/projects/${projectId.value}/scenes/${sceneId}/schedule`, null, {
        params: { cron: scheduleCron.value, enabled: true, env_id: envId || undefined },
      })
      msgSuccess('调度配置已保存')
    } catch (e) {
      logger.warn('[Scenes] Failed to save schedule:', e)
    } finally {
      scheduleSaving.value = false
    }
  }

  return {
    scheduleEnabled,
    scheduleCron,
    scheduleSaving,
    setQuickCron,
    loadSchedule,
    onScheduleToggle,
    saveSchedule,
  }
}
