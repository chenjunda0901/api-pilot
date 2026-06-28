import { ref } from 'vue'

export type TransitionPhase = 'idle' | 'entering' | 'loading' | 'content'

/**
 * 路由过渡编排 composable
 *
 * 协调 skeleton → 内容的平滑过渡时序:
 *   1. 旧内容淡出 (150ms) → phase='entering'
 *   2. skeleton 展示 → phase='loading'
 *   3. 数据到达，skeleton → 内容 (300ms crossfade) → phase='content'
 *
 * 用法:
 *   const orchestrator = useTransitionOrchestrator()
 *   orchestrator.startTransition()
 *   // 数据到达后:
 *   orchestrator.onContentReady()
 */
export function useTransitionOrchestrator() {
  const phase = ref<TransitionPhase>('idle')

  function startTransition() {
    phase.value = 'entering'
    setTimeout(() => {
      phase.value = 'loading'
    }, 150)
  }

  function onContentReady() {
    phase.value = 'content'
  }

  function reset() {
    phase.value = 'idle'
  }

  return { phase, startTransition, onContentReady, reset }
}