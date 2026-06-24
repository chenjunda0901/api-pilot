<template>
  <div class="form-hint-wrapper">
    <!-- 字段级提示 -->
    <div
      v-if="hint && !error"
      class="field-hint"
      :class="[`hint-${hintType}`]"
    >
      <el-icon v-if="hintType !== 'default'" class="hint-icon">
        <component :is="hintIcon" />
      </el-icon>
      <span>{{ hint }}</span>
    </div>
    
    <!-- 错误提示 -->
    <div v-if="error" class="field-error">
      <el-icon class="error-icon"><WarningFilled /></el-icon>
      <span>{{ friendlyError }}</span>
    </div>
    
    <!-- 成功提示 -->
    <div v-if="success" class="field-success">
      <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
      <span>{{ success }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled, CircleCheckFilled, InfoFilled, QuestionFilled } from '@element-plus/icons-vue'

interface Props {
  hint?: string
  error?: string
  success?: string
  hintType?: 'default' | 'tip' | 'warning' | 'info'
}

const props = withDefaults(defineProps<Props>(), {
  hint: '',
  error: '',
  success: '',
  hintType: 'default'
})

const hintIcon = computed(() => {
  switch (props.hintType) {
    case 'tip': return QuestionFilled
    case 'warning': return WarningFilled
    case 'info': return InfoFilled
    default: return null
  }
})

// 将技术性错误消息转换为友好消息
const friendlyError = computed(() => {
  if (!props.error) return ''
  
  const errorMap: Record<string, string> = {
    // 验证错误
    'This field is required': '此项为必填项',
    'Field is required': '此项为必填',
    'Invalid email': '邮箱格式不正确',
    'Invalid URL': '网址格式不正确',
    'String should have at least': '内容太短',
    'String should have at most': '内容太长',
    
    // 通用错误
    'not found': '数据不存在',
    'not found.': '数据不存在',
    'unauthorized': '登录已过期，请重新登录',
    'forbidden': '权限不足',
    'timeout': '请求超时，请稍后重试',
    'network': '网络连接失败，请检查网络后重试',
  }
  
  let msg = props.error
  
  // 精确匹配
  if (errorMap[msg]) return errorMap[msg]
  
  // 模糊匹配
  const lowerMsg = msg.toLowerCase()
  for (const [key, value] of Object.entries(errorMap)) {
    if (lowerMsg.includes(key.toLowerCase())) {
      return value
    }
  }
  
  // 太长的错误消息可能是堆栈或英文技术消息
  if (msg.length > 50 && !msg.includes('\u4e00-\u9fa5')) {
    return '输入有误，请检查后重试'
  }
  
  return msg
})
</script>

<style scoped>
.form-hint-wrapper {
  margin-top: var(--space-1);
  min-height: 20px;
}

.field-hint {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--leading-normal);
}

.field-hint.hint-tip {
  color: var(--primary-600);
}

.field-hint.hint-warning {
  color: var(--warning-text);
}

.field-hint.hint-info {
  color: var(--info-text);
}

.hint-icon {
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.field-error {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--error-text);
  line-height: var(--leading-normal);
  animation: formHintShake 0.3s ease;
}

@keyframes formHintShake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

.error-icon {
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.field-success {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--success-text);
  line-height: var(--leading-normal);
  animation: formHintFadeIn 0.2s ease;
}

@keyframes formHintFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.success-icon {
  font-size: var(--text-xs);
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .field-error,
  .field-success {
    animation: none;
  }
}

html.dark .field-hint.hint-tip {
  color: var(--primary-400);
}
</style>