<template>
  <div class="route-skeleton">
    <SkeletonLoader variant="page" />
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from './SkeletonLoader.vue'
</script>

<style scoped>
.route-skeleton {
  padding: var(--space-4);
}
</style>