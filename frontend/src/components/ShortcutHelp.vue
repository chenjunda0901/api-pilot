<template>
  <div>
    <Teleport to="body">
    <div v-if="visible" class="sh-overlay" @click.self="emit('close')">
      <div class="sh-panel">
        <div class="sh-header">
          <h3 class="sh-title">键盘快捷键</h3>
          <button class="sh-close" @click="emit('close')">&times;</button>
        </div>
        <div class="sh-body">
          <div v-for="group in shortcuts" :key="group.group" class="sh-group">
            <div class="sh-group-label">{{ group.group }}</div>
            <div v-for="item in group.items" :key="item.keys" class="sh-item">
              <span class="sh-keys">
                <kbd v-for="k in item.keys.split('+')" :key="k">{{ k }}</kbd>
              </span>
              <span class="sh-desc">{{ item.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const shortcuts = [
  { group: '全局', items: [
    { keys: 'Ctrl+K', desc: '全局搜索' },
    { keys: 'Ctrl+/', desc: '显示快捷键面板' },
    { keys: 'Ctrl+Z', desc: '撤销上一次操作' },
    { keys: 'Ctrl+Shift+Z', desc: '重做上一次撤销' },
    { keys: 'Ctrl+Y', desc: '重做上一次撤销' },
    { keys: 'Escape', desc: '关闭弹窗/抽屉' },
  ]},
  { group: '导航', items: [
    { keys: 'Ctrl+[', desc: '折叠侧边栏（开发中）' },
  ]},
  { group: '编辑', items: [
    { keys: 'Ctrl+S', desc: '保存当前编辑' },
  ]},
  { group: '执行', items: [
    { keys: 'Ctrl+Enter', desc: '运行场景 / 发送请求' },
  ]},
]
</script>

<style scoped>
.sh-overlay {
  position: fixed; inset: 0;
  background: var(--color-neutral-alpha-20);
  display: flex; align-items: center; justify-content: center;
  z-index: var(--z-shortcut);
}

.sh-panel {
  width: 460px;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-drag);
  overflow: hidden;
}

.sh-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 0px solid transparent;
}

.sh-title {
  font-size: var(--text-md); font-weight: var(--weight-bold); color: var(--text-primary); margin: 0;
}

.sh-close {
  background: none; border: none; font-size: var(--text-2xl);
  color: var(--text-muted); cursor: pointer; line-height: 1;
}
.sh-close:hover { color: var(--text-regular); }

.sh-body { padding: var(--space-3) var(--space-5) 20px; max-height: 360px; overflow-y: auto; }

.sh-group { margin-top: var(--space-3); }
.sh-group:first-child { margin-top: 0; }

.sh-group-label {
  font-size: 0.625rem; font-weight: var(--weight-bold); text-transform: uppercase;
  color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: var(--space-1);
}

.sh-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-1) 0;
}

.sh-keys { display: flex; gap: 0; min-width: 120px; }

.sh-keys kbd {
  display: inline-block;
  padding: 0 calc(var(--space-2) - 1px); font-size: 0.625rem; font-family: var(--font-mono);
  background: var(--slate-200); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xs); color: var(--text-regular);
}

.sh-keys kbd:hover {
  background: var(--surface-hover);
  border-color: var(--border-subtle);
}

.sh-desc { font-size: var(--text-sm); color: var(--text-secondary); }

html.dark .shortcut-panel { background: var(--surface-card); border-color: var(--border-subtle); }
html.dark .shortcut-title { color: var(--text-primary); }
html.dark .shortcut-item { color: var(--text-secondary); }
html.dark .shortcut-key {
  background: var(--surface-hover);
  border-color: var(--border-subtle);
  color: var(--text-primary);
}

</style>
