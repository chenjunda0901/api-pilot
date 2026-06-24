<template>
  <span class="animated-counter" :aria-label="`${label}: ${displayValue}`">{{ displayValue }}</span>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  duration?: number
  label?: string
  decimals?: number
  prefix?: string
  suffix?: string
}>(), {
  duration: 1200,
  label: '',
  decimals: 0,
  prefix: '',
  suffix: '',
})

const displayValue = ref('')
let animFrame = 0
let startTime = 0
let startVal = 0

const format = (n: number) => {
  const fixed = n.toFixed(props.decimals)
  return `${props.prefix}${fixed}${props.suffix}`
}

const animate = (from: number, to: number) => {
  cancelAnimationFrame(animFrame)
  startVal = from
  startTime = performance.now()
  const dur = props.duration

  const step = (now: number) => {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / dur, 1)
    // ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3)
    const current = startVal + (to - startVal) * eased
    displayValue.value = format(current)
    if (progress < 1) {
      animFrame = requestAnimationFrame(step)
    }
  }
  animFrame = requestAnimationFrame(step)
}

watch(() => props.value, (newVal, oldVal) => {
  animate(oldVal ?? 0, newVal)
}, { immediate: true })

onUnmounted(() => cancelAnimationFrame(animFrame))
</script>

<style scoped>
.animated-counter {
  font-variant-numeric: tabular-nums;
}
</style>
