<template>
  <el-dialog :model-value="visible" title="cURL Command" width="640px" @close="$emit('update:visible', false)">
    <div class="curl-preview">
      <pre class="curl-code">{{ curlCommand }}</pre>
      <div class="curl-actions">
        <el-button type="primary" @click="copyCurl">
          <el-icon><DocumentCopy /></el-icon> Copy cURL
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { msgSuccess, msgError } from '@/utils/message'
import { DocumentCopy } from '@element-plus/icons-vue'

const props = defineProps<{
  visible: boolean
  method: string
  url: string
  headers?: Record<string, string>
  body?: string
}>()

defineEmits<{ 'update:visible': [val: boolean] }>()

const curlCommand = computed(() => {
  let cmd = `curl -X ${props.method} '${props.url}'`
  if (props.headers) {
    for (const [k, v] of Object.entries(props.headers)) {
      cmd += ` \
  -H '${k}: ${v}'`
    }
  }
  if (props.body && props.method !== 'GET') {
    cmd += ` \
  -d '${props.body}'`
  }
  return cmd
})

async function copyCurl() {
  try {
    await navigator.clipboard.writeText(curlCommand.value)
    msgSuccess('cURL copied')
  } catch {
    msgError('Copy failed')
  }
}
</script>

<style scoped>
/* ===== cURL 预览容器 ===== */
.curl-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
}

/* ===== cURL 代码块 ===== */
.curl-code {
  background: var(--surface-nested);
  color: var(--text-primary);
  padding: var(--space-4, 16px);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--text-sm, 13px);
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
  max-height: 400px;
  margin: 0;
  transition: background var(--transition-normal, 250ms) ease,
    border-color var(--transition-normal, 250ms) ease;
}

/* ===== 操作栏 ===== */
.curl-actions {
  display: flex;
  justify-content: flex-end;
}

/* ===== 按钮增强 ===== */
:deep(.el-button--primary) {
  transition: all var(--transition-fast, 150ms) ease;
}

:deep(.el-button--primary:focus-visible) {
  outline: var(--focus-ring-width) solid var(--primary-500);
  outline-offset: 2px;
}

/* ===== 对话框增强 ===== */
:deep(.el-dialog) {
  border-radius: var(--radius-lg, 12px);
}

:deep(.el-dialog__header) {
  padding-bottom: var(--space-2, 8px);
  border-bottom: 1px solid var(--border-subtle);
  margin-right: 0;
}

:deep(.el-dialog__body) {
  padding-top: var(--space-4, 16px);
}

/* ===== 暗色模式 ===== */
html.dark .curl-code {
  background: var(--surface-bg);
  color: var(--text-primary);
  border-color: var(--border-subtle);
}

/* ===== 滚动条美化 ===== */
.curl-code::-webkit-scrollbar {
  height: 6px;
  width: 6px;
}

.curl-code::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: var(--radius-sm, 4px);
}

.curl-code::-webkit-scrollbar-track {
  background: transparent;
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  .curl-code,
  :deep(.el-button--primary) {
    transition-duration: 0.01ms !important;
  }
}
</style>
