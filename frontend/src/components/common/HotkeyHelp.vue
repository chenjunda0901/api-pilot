<template>
  <Teleport to="body">
    <Transition name="hotkey-fade">
      <div v-if="visible" class="hotkey-overlay" @click.self="$emit('update:visible', false)" @keydown.escape="$emit('update:visible', false)">
        <div class="hotkey-panel" role="dialog" aria-label="快捷键帮助" aria-modal="true">
          <!-- Header -->
          <div class="hotkey-header">
            <h3 class="hotkey-title">键盘快捷键</h3>
            <button class="hotkey-close" @click="$emit('update:visible', false)" aria-label="关闭">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <!-- Body: grouped shortcuts -->
          <div class="hotkey-body">
            <div v-for="group in groupedHotkeys" :key="group.label" class="hotkey-group">
              <div class="hotkey-group-label">{{ group.label }}</div>
              <div v-for="item in group.items" :key="item.description" class="hotkey-row">
                <div class="hotkey-keys">
                  <kbd v-for="key in item.keys" :key="key">{{ key }}</kbd>
                </div>
                <span class="hotkey-desc">{{ item.description }}</span>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="hotkey-footer">
            按 <kbd>?</kbd> 切换此面板 · <kbd>Esc</kbd> 关闭
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRegisteredHotkeys, formatKeys } from '@/composables/useHotkeys'

defineProps<{ visible: boolean }>()
defineEmits<{ 'update:visible': [val: boolean] }>()

const registeredHotkeys = useRegisteredHotkeys()

// 分类规则：根据快捷键特征自动归类
function categorize(binding: { key: string; ctrl?: boolean; shift?: boolean; alt?: boolean; description: string }): string {
  const desc = binding.description
  if (desc.includes('发送') || desc.includes('请求')) return '请求'
  if (desc.includes('保存')) return '请求'
  if (desc.includes('关闭') || desc.includes('导航') || desc.includes('Tab')) return '导航'
  return '通用'
}

const groupedHotkeys = computed(() => {
  // 动态注册的快捷键
  const dynamicItems = registeredHotkeys.value.map(h => ({
    keys: formatKeys(h),
    description: h.description,
    category: categorize(h),
  }))

  // 静态补充：一些未通过 useHotkeys 注册但实际存在的快捷键
  const staticItems = [
    { keys: ['?'], description: '快捷键帮助', category: '通用' },
    { keys: ['Ctrl', 'Z'], description: '撤销', category: '通用' },
    { keys: ['Ctrl', '⇧', 'Z'], description: '重做', category: '通用' },
    { keys: ['Ctrl', '/'], description: '快捷键帮助', category: '通用' },
    { keys: ['Tab'], description: '下一个字段', category: '导航' },
  ]

  // 合并去重（按 description）
  const all = [...dynamicItems, ...staticItems]
  const seen = new Set<string>()
  const deduped = all.filter(item => {
    if (seen.has(item.description)) return false
    seen.add(item.description)
    return true
  })

  // 按分类分组，保持固定顺序
  const categoryOrder = ['通用', '请求', '导航']
  const groups: Record<string, { keys: string[]; description: string }[]> = {}
  for (const cat of categoryOrder) {
    groups[cat] = []
  }
  for (const item of deduped) {
    const cat = categoryOrder.includes(item.category) ? item.category : '通用'
    groups[cat].push({ keys: item.keys, description: item.description })
  }

  return categoryOrder
    .filter(cat => groups[cat].length > 0)
    .map(cat => ({ label: cat, items: groups[cat] }))
})
</script>

<style scoped>
/* 遮罩层 */
.hotkey-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-max);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-black-alpha-45, rgba(0, 0, 0, 0.45));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* 面板 */
.hotkey-panel {
  width: 480px;
  max-width: 90vw;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-float);
  overflow: hidden;
}

/* Header */
.hotkey-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}
.hotkey-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}
.hotkey-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--duration-fast), color var(--duration-fast);
}
.hotkey-close:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

/* Body */
.hotkey-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) var(--space-5);
}

/* Group */
.hotkey-group {
  margin-bottom: var(--space-4);
}
.hotkey-group:last-child {
  margin-bottom: 0;
}
.hotkey-group-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
}

/* Row */
.hotkey-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-1-5) 0;
}
.hotkey-row + .hotkey-row {
  border-top: 1px solid var(--border-subtle);
  border-top-style: dashed;
}

/* Keys */
.hotkey-keys {
  display: flex;
  gap: var(--space-1);
  align-items: center;
  flex-shrink: 0;
}

/* kbd 键帽样式 */
kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  padding: var(--space-0-5) var(--space-1-5);
  font-size: var(--text-2xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xs);
  box-shadow: 0 1px 0 var(--border-subtle);
  line-height: var(--leading-tight);
}

/* Description */
.hotkey-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-left: var(--space-4);
  text-align: right;
}

/* Footer */
.hotkey-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-2-5) var(--space-5);
  border-top: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.hotkey-footer kbd {
  font-size: var(--text-3xs);
  padding: var(--space-0-5) var(--space-1);
  margin: 0 var(--space-0-5);
}

/* 暗色模式 */
html.dark .hotkey-overlay {
  background: var(--color-black-alpha-60);
}

/* 过渡动画 */
.hotkey-fade-enter-active {
  transition: all var(--duration-base) var(--ease-out);
}
.hotkey-fade-leave-active {
  transition: all var(--duration-fast) var(--ease-in);
}
.hotkey-fade-enter-from {
  opacity: 0;
  transform: scale(0.96);
}
.hotkey-fade-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .hotkey-fade-enter-active,
  .hotkey-fade-leave-active {
    transition-duration: 0.01ms !important;
  }
}
</style>
