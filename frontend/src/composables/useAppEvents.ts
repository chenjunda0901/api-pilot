import { onMounted, onUnmounted, ref, type Ref } from 'vue'
import { provideEventBus } from './useEventBus'
import { EVENTS } from '../constants/events'

export function useAppEvents() {
  const eventBus = provideEventBus()
  const runningSceneInfo: Ref<string> = ref("")

  function onSceneRunning(name: string) {
    runningSceneInfo.value = `正在运行: ${name}`
  }

  function onSceneComplete() {
    runningSceneInfo.value = ""
  }

  onMounted(() => {
    eventBus.on(EVENTS.SCENE_RUNNING, onSceneRunning)
    eventBus.on(EVENTS.SCENE_COMPLETE, onSceneComplete)
    eventBus.on(EVENTS.PAGE_LOADED, () => { /* consumed by useAppLoading */ })
  })

  onUnmounted(() => {
    eventBus.off(EVENTS.SCENE_RUNNING, onSceneRunning)
    eventBus.off(EVENTS.SCENE_COMPLETE, onSceneComplete)
  })

  return { eventBus, runningSceneInfo }
}
