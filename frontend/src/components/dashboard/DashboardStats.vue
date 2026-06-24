<template>
  <div class="stat-row">
    <div v-for="card in stats" :key="card.label" class="stat-card" tabindex="0" :style="{ '--card-accent': card.accentGradient }" @click="$emit('navigate', card.link)"
      @keydown.enter="$emit('navigate', card.link)"
    >
      <div class="stat-card-glow"></div>
      <div class="stat-card-body">
        <div class="stat-card-top">
          <div class="stat-icon-circle" :style="{ background: card.iconBg }">
            <component :is="card.iconComponent" :size="20" :style="{ color: card.color }" />
          </div>
          <div class="stat-trend-row" :class="card.trend != null ? (card.trend > 0 ? 'up' : card.trend < 0 ? 'down' : 'flat') : ''" v-if="card.trend != null">
            <span class="stat-trend-value" :class="card.trend > 0 ? 'up' : card.trend < 0 ? 'down' : 'flat'">
              {{ card.trend > 0 ? '+' : '' }}{{ card.trend }}%（较上周）
              <span v-if="card.trend > 0" class="trend-arrow up">▲</span>
              <span v-else-if="card.trend < 0" class="trend-arrow down">▼</span>
            </span>
          </div>
        </div>
        <div class="stat-num-wrap">
          <AnimatedCounter v-if="card.value > 0" :value="card.value" :duration="1200" :label="card.label" />
          <span v-else class="stat-zero">0</span>
        </div>
        <div class="stat-card-foot">
          <div class="stat-bar-row">
            <div class="stat-mini-bar"><div class="stat-mini-bar-fill" :style="{ width: Math.min(card.pct, 100).toFixed(1) + '%', background: card.accentGradient }"></div></div>
          </div>
          <span class="stat-label">{{ card.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AnimatedCounter from '../AnimatedCounter.vue'

defineProps<{
  stats: Array<{
    label: string
    value: number
    color: string
    iconBg: string
    accentGradient: string
    iconComponent: unknown
    trend: number | null
    pct: number
    link: string
  }>
}>()

defineEmits<{
  navigate: [link: string]
}>()
</script>
