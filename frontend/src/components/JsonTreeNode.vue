<template>
  <div class="json-node" :class="{ 'json-root': depth === 1 }">
    <!-- 叶子节点：string / number / boolean / null -->
    <template v-if="node.type === 'string' || node.type === 'number' || node.type === 'boolean' || node.type === 'null'">
      <div class="json-line" :style="{ paddingLeft: depth * 16 + 'px' }" @contextmenu.prevent="onContextMenu($event)">
        <span v-if="node.key !== null" class="json-key">{{ formatKey(node.key) }}<span class="json-colon">:</span></span>
        <span :class="'json-value json-' + node.type">{{ node.value }}</span>
      </div>
    </template>
    <!-- 对象 -->
    <template v-else-if="node.type === 'object'">
      <div class="json-line json-bracket-line" :style="{ paddingLeft: depth * 16 + 'px' }" @click="toggle">
        <span class="json-toggle" :class="{ expanded: isOpen }">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M3 2l4 3-4 3z"/></svg>
        </span>
        <span v-if="node.key !== null" class="json-key">{{ formatKey(node.key) }}<span class="json-colon">:</span></span>
        <span class="json-bracket">{{ isOpen ? '{' : '{...}' }}</span>
        <span class="json-count">{{ node.size }} 个字段</span>
      </div>
      <div v-if="isOpen" class="json-children">
        <json-tree-node
          v-for="(child, idx) in node.children"
          :key="idx"
          :node="child"
          :depth="depth + 1"
          :is-last="idx === node.children.length - 1"
          :path-prefix="node.key !== null ? (pathPrefix ? pathPrefix + '.' + node.key : String(node.key)) : pathPrefix"
          @extract-variable="(e: { path: string; value: string }) => emit('extract-variable', e)"
        />
        <div class="json-line" :style="{ paddingLeft: (depth + 1) * 16 + 'px' }">
          <span class="json-bracket">}</span>
        </div>
      </div>
    </template>
    <!-- 数组 -->
    <template v-else-if="node.type === 'array'">
      <div class="json-line json-bracket-line" :style="{ paddingLeft: depth * 16 + 'px' }" @click="toggle">
        <span class="json-toggle" :class="{ expanded: isOpen }">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M3 2l4 3-4 3z"/></svg>
        </span>
        <span v-if="node.key !== null" class="json-key">{{ formatKey(node.key) }}<span class="json-colon">:</span></span>
        <span class="json-bracket">{{ isOpen ? '[' : '[...]' }}</span>
        <span class="json-count">{{ node.size }} 项</span>
      </div>
      <div v-if="isOpen" class="json-children">
        <json-tree-node
          v-for="(child, idx) in node.children"
          :key="idx"
          :node="child"
          :depth="depth + 1"
          :is-last="idx === node.children.length - 1"
          :path-prefix="node.key !== null ? (pathPrefix ? pathPrefix + '.' + node.key : String(node.key)) : pathPrefix"
          @extract-variable="(e: { path: string; value: string }) => emit('extract-variable', e)"
        />
        <div class="json-line" :style="{ paddingLeft: (depth + 1) * 16 + 'px' }">
          <span class="json-bracket">]</span>
        </div>
      </div>
    </template>

    <!-- 右键上下文菜单 -->
    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="json-context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <div class="context-menu-item" @click="handleExtract">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="4 12 20 12"/></svg>
          提取为变量
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'

interface TreeNode {
  key: string | null
  value: unknown
  type: 'string' | 'number' | 'boolean' | 'null' | 'object' | 'array'
  children: TreeNode[]
  size: number
}

const props = withDefaults(defineProps<{
  node: TreeNode
  depth?: number
  isLast?: boolean
  pathPrefix?: string
}>(), {
  depth: 0,
  isLast: false,
  pathPrefix: '',
})

const emit = defineEmits<{
  (e: 'extract-variable', payload: { path: string; value: string }): void
}>()

const isOpen = ref(true)
function toggle() { isOpen.value = !isOpen.value }

function formatKey(key: string | null): string {
  if (key === null) return ''
  if (typeof key === 'string' && /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(key)) return key
  return JSON.stringify(key)
}

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  path: '',
  value: '',
})

let closeMenuHandler: (() => void) | null = null

function onContextMenu(e: MouseEvent) {
  // 构建完整路径
  const key = props.node.key
  const fullPath = key !== null
    ? (props.pathPrefix ? props.pathPrefix + '.' + key : String(key))
    : props.pathPrefix

  // 获取实际值（去除引号）
  let rawValue = props.node.value
  if (props.node.type === 'string') {
    try { rawValue = JSON.parse(rawValue) } catch { /* JSON 解析失败时保留原始值 */ }
  }

  contextMenu.path = fullPath
  contextMenu.value = String(rawValue)
  contextMenu.x = e.clientX
  contextMenu.y = e.clientY
  contextMenu.visible = true

  // 清理之前的监听器
  if (closeMenuHandler) {
    document.removeEventListener('click', closeMenuHandler)
  }

  // 点击其他位置关闭菜单
  closeMenuHandler = () => {
    contextMenu.visible = false
    document.removeEventListener('click', closeMenuHandler!)
    closeMenuHandler = null
  }
  setTimeout(() => document.addEventListener('click', closeMenuHandler!), 0)
}

onUnmounted(() => {
  if (closeMenuHandler) {
    document.removeEventListener('click', closeMenuHandler)
    closeMenuHandler = null
  }
  contextMenu.visible = false
})

function handleExtract() {
  emit('extract-variable', {
    path: contextMenu.path,
    value: contextMenu.value,
  })
  contextMenu.visible = false
}
</script>

<style scoped>
/* JSON 行：基础布局 */
.json-line {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 1px var(--space-1);
  min-height: 22px;
  white-space: nowrap;
  cursor: default;
  border-radius: var(--radius-xs, 2px);
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

/* 行悬停：柔和主色高亮 */
.json-line:hover {
  background: var(--color-primary-alpha-04);
}

/* 可点击行（对象/数组折叠行） */
.json-bracket-line {
  cursor: pointer;
}

/* 折叠/展开图标：旋转动画 */
.json-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--text-muted);
  transition: transform var(--duration-fast) var(--ease-spring);
}
.json-toggle { transform: rotate(0deg); }
.json-toggle.expanded { transform: rotate(90deg); }

/* JSON 键：信息色 + 加粗 */
.json-key {
  color: var(--info);
  font-weight: var(--weight-semibold);
  transition: color var(--duration-fast) var(--ease-smooth);
}

/* 冒号：弱化 */
.json-colon {
  color: var(--text-muted);
  margin-right: 2px;
}

/* 大括号/中括号：次要色 + 加粗 */
.json-bracket {
  color: var(--text-secondary);
  font-weight: var(--weight-semibold);
}

/* 子节点计数徽章：迷你胶囊 */
.json-count {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-2xs);
  color: var(--text-disabled);
  margin-left: var(--space-1);
  padding: 0 var(--space-1);
  background: var(--surface-muted);
  border-radius: var(--radius-full);
  font-family: var(--font-sans);
  line-height: 1.4;
  transition: background-color var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
}

/* 值类型颜色：语义化配色 */
.json-value.json-string { color: var(--success); }
.json-value.json-number { color: var(--warning); }
.json-value.json-boolean { color: var(--purple); }
.json-value.json-null { color: var(--text-disabled); font-style: italic; }

/* 子节点容器：展开/折叠动画 */
.json-children {
  overflow: hidden;
  animation: jsonChildrenExpand var(--duration-base) var(--ease-out);
}

@keyframes jsonChildrenExpand {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

/* 右键上下文菜单：浮层卡片 */
.json-context-menu {
  position: fixed;
  z-index: var(--z-max);
  min-width: 160px;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-pop);
  padding: var(--space-1) 0;
  overflow: hidden;
  animation: jsonMenuIn var(--duration-fast) var(--ease-bounce-soft);
}

@keyframes jsonMenuIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(-2px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* 菜单项：悬停高亮 + 图标反馈 */
.context-menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-primary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  margin: 0 var(--space-1);
  transition: background var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-spring);
}

.context-menu-item:hover {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  transform: translateX(2px);
}

.context-menu-item:active {
  transform: scale(var(--press-scale));
}

.context-menu-item svg {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-spring);
}

.context-menu-item:hover svg {
  color: var(--primary-600);
  transform: translateX(2px);
}

/* 暗色模式适配 */
html.dark .json-key {
  color: var(--info);
}
html.dark .json-count {
  background: var(--surface-hover);
  color: var(--text-muted);
}
html.dark .json-context-menu {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-pop);
}
html.dark .context-menu-item:hover {
  background: var(--color-primary-alpha-12);
  color: var(--primary-400);
}
html.dark .context-menu-item:hover svg {
  color: var(--primary-400);
}

/* 淡入动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
