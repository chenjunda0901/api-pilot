<template>
  <div class="extract-tab">
    <div class="extract-header">
      <span class="extract-title">变量提取规则</span>
      <el-button size="small" @click="addRule">+ 添加规则</el-button>
    </div>
    <div v-if="!rules.length" class="extract-empty">暂无提取规则 — 响应中的变量将不会被自动保存</div>
    <div v-for="(rule, i) in rules" :key="i" class="extract-rule">
      <div class="rule-row">
        <VarAwareInput v-model="rule.variable" size="small" placeholder="变量名" aria-label="变量名" class="rule-name" @update:model-value="onChange" />
        <el-select v-model="rule.source" size="small" class="rule-source" @change="onChange">
          <el-option value="body" label="响应体" />
          <el-option value="header" label="响应头" />
          <el-option value="status" label="状态码" />
        </el-select>
        <el-select v-model="rule.type" size="small" class="rule-type" @change="onChange">
          <el-option value="jsonpath" label="JSONPath" />
          <el-option value="regex" label="正则" />
        </el-select>
        <el-button text size="small" @click="removeRule(i)">删除</el-button>
      </div>
      <VarAwareInput v-model="rule.expression" size="small" :placeholder="rule.type === 'jsonpath' ? '$.data.id' : '\\\\d+'" class="rule-expr" aria-label="提取表达式" @update:model-value="onChange" />
      <div class="extract-scope">
        <label>作用域</label>
        <el-select v-model="rule.scope" size="small" @change="onChange">
          <el-option label="📍 步骤级 (Step)" value="step" />
          <el-option label="📂 场景级 (Scene)" value="scene" />
          <el-option label="🌐 全局级 (Global)" value="global" />
          <el-option label="⚙️ 环境级 (Env)" value="env" />
        </el-select>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import VarAwareInput from './common/VarAwareInput.vue'

interface ExtractRule {
  variable: string
  source: 'body' | 'header' | 'status'
  type: 'jsonpath' | 'regex'
  expression: string
  scope: 'step' | 'scene' | 'global' | 'env'
}

const props = defineProps<{ modelValue: ExtractRule[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: ExtractRule[]] }>()

const rules = ref<ExtractRule[]>(props.modelValue || [])

const _internalUpdating = ref(false)

watch(() => props.modelValue, (val) => {
  if (_internalUpdating.value) return
  rules.value = val || []
}, { deep: true })

function onChange() {
  _internalUpdating.value = true
  emit('update:modelValue', [...rules.value])
  void nextTick(() => { _internalUpdating.value = false })
}
function addRule() {
  rules.value.push({ variable: '', source: 'body', type: 'jsonpath', expression: '', scope: 'step' })
  onChange()
}
function removeRule(i: number) { rules.value.splice(i, 1); onChange() }
</script>
<style scoped>
/* ==========================================
 * VariableExtractTab — 变量提取规则配置样式
 * ==========================================
 * 用于配置从响应中自动提取变量的规则
 * 支持 JSONPath 和正则两种提取方式
 * ========================================== */

/* 提取规则容器 */
.extract-tab {
  padding: var(--space-1) 0;
}

/* 头部：标题 + 添加按钮 */
.extract-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.extract-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 空状态提示 */
.extract-empty {
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: var(--space-5);
  text-align: center;
  background: var(--surface-hover);
  border-radius: var(--radius-sm);
}

/* 单条提取规则卡片 */
.extract-rule {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  margin-bottom: var(--space-2);
  transition: border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}
.extract-rule:hover {
  border-color: var(--border-strong);
}
.extract-rule:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--color-primary-alpha-12);
}

/* 规则主行（变量名 + 来源 + 类型 + 删除按钮） */
.rule-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

/* 变量名输入框 */
.rule-name {
  width: 140px;
}

/* 来源选择器（响应体/响应头/状态码） */
.rule-source {
  width: 110px;
}

/* 类型选择器（JSONPath/正则） */
.rule-type {
  width: 110px;
}

/* 表达式输入框 */
.rule-expr {
  width: 100%;
  font-family: var(--font-mono);
}

/* 作用域配置区域 */
.extract-scope {
  margin-top: var(--space-2);
}

.extract-scope label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  display: block;
  margin-bottom: var(--space-0-5);
  font-weight: var(--weight-medium);
}
</style>
