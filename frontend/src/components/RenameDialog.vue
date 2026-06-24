<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="400px"
    :close-on-click-modal="false"
    @closed="onClosed"
   destroy-on-close>
    <el-input
      v-model="inputValue"
      ref="inputRef"
      size="default"
      :placeholder="placeholder"
      @keyup.enter="onConfirm"
      aria-label="输入名称"
    />
    <template #footer>
      <el-button size="small" @click="onCancel">取消</el-button>
      <el-button size="small" type="primary" @click="onConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  modelValue: boolean
  title: string
  placeholder?: string
  defaultValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  confirm: [string]
  cancel: []
}>()

const visible = ref(props.modelValue)
const inputValue = ref(props.defaultValue || '')
const inputRef = ref<{ focus: () => void } | null>(null)

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    inputValue.value = props.defaultValue || ''
    void nextTick(() => inputRef.value?.focus())
  }
})

watch(visible, (v) => {
  emit('update:modelValue', v)
})

function onConfirm() {
  if (!inputValue.value.trim()) return
  emit('confirm', inputValue.value.trim())
  visible.value = false
}

function onCancel() {
  emit('cancel')
  visible.value = false
}

function onClosed() {
  inputValue.value = ''
}
</script>

<style scoped>
/* ===== 对话框样式 — 使用 Element Plus 全局覆盖 + 局部优化 ===== */
/* 对话框已经由 element-plus-override.css 统一处理 */
/* 这里只需要优化输入框和按钮的局部样式 */

/* 输入框聚焦状态增强 */
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-500) inset,
    0 0 0 3px var(--color-primary-alpha-08);
}

/* 按钮间距优化 */
:deep(.el-dialog__footer) {
  gap: var(--space-3);
}

/* 无障碍：减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  :deep(.el-dialog),
  :deep(.el-input__wrapper),
  :deep(.el-button) {
    transition-duration: 0.01ms !important;
  }
}
</style>