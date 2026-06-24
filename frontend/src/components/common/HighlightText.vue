<template>
  <span class="ht-wrapper">
    <template v-for="(part, i) in parsed" :key="i">
      <span v-if="part.type === 'text'" class="ht-text" :style="textStyle">{{ part.value }}</span>
      <span v-else-if="part.type === 'variable'" class="ht-variable" :style="varStyle">
        {{ part.display }}
      </span>
    </template>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue"

const props = withDefaults(
  defineProps<{
    text: string
    tagStyle?: "tag" | "inline" // tag=标签样式, inline=行内高亮
  }>(),
  {
    tagStyle: "inline",
  }
)

const parsed = computed(() => {
  const parts: { type: string; value: string; display?: string }[] = []
  const regex = /\{\{([^}]+)\}\}/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(props.text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: props.text.slice(lastIndex, match.index) })
    }
    const varName = match[1].trim()
    parts.push({
      type: "variable",
      value: varName,
      display: "{{" + varName + "}}",
    })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < props.text.length) {
    parts.push({ type: "text", value: props.text.slice(lastIndex) })
  }
  return parts
})

const textStyle = computed(() => ({}))
const varStyle = computed(() => ({}))
</script>

<style scoped>
.ht-wrapper {
  display: inline;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}
.ht-text {
  display: inline;
}
.ht-variable {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-1);
  margin: 0 1px;
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
  border-radius: 3px;
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono, monospace);
  font-size: inherit;
  border: 1px solid var(--color-primary-alpha-20);
  line-height: 1.4;
}

/* 暗色模式 */
:global(html.dark) .ht-variable { color: var(--primary-400); background: var(--color-primary-alpha-16); border-color: var(--color-primary-alpha-24); }
</style>
