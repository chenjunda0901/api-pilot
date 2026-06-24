<template>
  <el-collapse-item :title="'Step ' + (index + 1) + ': ' + (step.name || 'Untitled')" :name="index">
    <el-form :model="step" label-width="100px" size="small" class="step-config">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="Timeout(ms)">
            <el-input-number v-model="step.timeout" :min="100" :max="60000" :step="500" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Retry Count">
            <el-input-number v-model="step.retry_count" :min="0" :max="5" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="On Failure">
            <el-select v-model="step.failure_strategy" style="width:100%">
              <el-option label="Stop" value="stop" />
              <el-option label="Continue" value="continue" />
              <el-option label="Skip Remaining" value="skip_remaining" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="Condition">
        <el-input v-model="step.condition" placeholder="JS expression, e.g.: response.status === 200" />
      </el-form-item>
      <el-form-item label="Assert Mode">
        <el-radio-group v-model="step.assert_mode">
          <el-radio value="strict">Strict</el-radio>
          <el-radio value="lenient">Lenient</el-radio>
        </el-radio-group>
        <div class="form-hint">
          Strict: 所有断言必须通过 | Lenient: 允许部分断言失败
        </div>
      </el-form-item>
      
      <!-- Assertions Configuration -->
      <el-form-item label="Assertions">
        <div class="assertions-section">
          <div v-if="!step.assertions || step.assertions.length === 0" class="empty-hint">
            暂无断言规则，点击下方按钮添加
          </div>
          <div v-for="(assertion, i) in step.assertions" :key="i" class="assertion-row">
            <el-select v-model="assertion.type" placeholder="断言类型" style="width: 120px">
              <el-option label="状态码" value="status" />
              <el-option label="响应体" value="body" />
              <el-option label="响应头" value="header" />
              <el-option label="JSON路径" value="json_path" />
              <el-option label="包含" value="contains" />
              <el-option label="响应时间" value="response_time" />
            </el-select>
            
            <el-input 
              v-model="assertion.path" 
              placeholder="JSON路径，如: $.data.id" 
              style="flex: 2"
              v-if="assertion.type === 'json_path' || assertion.type === 'body'"
            />
            
            <el-input 
              v-model="assertion.header" 
              placeholder="Header名称" 
              style="flex: 2"
              v-if="assertion.type === 'header'"
            />
            
            <el-select v-model="assertion.operator" placeholder="操作符" style="width: 100px">
              <el-option label="等于" value="eq" />
              <el-option label="不等于" value="neq" />
              <el-option label="包含" value="contains" />
              <el-option label="大于" value="gt" />
              <el-option label="小于" value="lt" />
              <el-option label="为空" value="is_null" />
              <el-option label="不为空" value="is_not_null" />
            </el-select>
            
            <el-input 
              v-model="assertion.expected" 
              placeholder="期望值" 
              style="flex: 2"
              v-if="assertion.operator !== 'is_null' && assertion.operator !== 'is_not_null'"
            />
            
            <el-button type="danger" link size="small" @click="removeAssertion(i)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button size="small" type="primary" link @click="addAssertion">+ 添加断言</el-button>
        </div>
      </el-form-item>
      
      <el-form-item label="Var Extract">
        <div class="extractions">
          <div v-if="!step.variable_extractions || step.variable_extractions.length === 0" class="empty-hint">
            暂无变量提取规则
          </div>
          <div v-for="(ext, i) in step.variable_extractions" :key="i" class="extraction-row">
            <el-input v-model="ext.expression" placeholder="$.data.id" style="flex:3" />
            <el-input v-model="ext.var_name" placeholder="var_name" style="flex:2" />
            <el-button type="danger" link size="small" @click="step.variable_extractions.splice(i,1)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button size="small" @click="addExtraction">+ Add Rule</el-button>
          <div class="form-hint">
            使用 JSONPath 提取响应数据，如: $.data.token 提取 token 字段
          </div>
        </div>
      </el-form-item>
    </el-form>
  </el-collapse-item>
</template>

<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'

const props = defineProps<{ step: Record<string, unknown>; index: number }>()

function addExtraction() {
  if (!props.step.variable_extractions) props.step.variable_extractions = []
  props.step.variable_extractions.push({ expression: '', var_name: '' })
}

function addAssertion() {
  if (!props.step.assertions) props.step.assertions = []
  props.step.assertions.push({
    type: 'status',
    operator: 'eq',
    expected: '',
    path: '',
    header: '',
  })
}

function removeAssertion(index: number) {
  if (props.step.assertions && Array.isArray(props.step.assertions)) {
    props.step.assertions.splice(index, 1)
  }
}
</script>

<style scoped>
/* 步骤配置表单 */
.step-config {
  padding: var(--spacing-sm) 0;
}

/* 变量提取规则容器 */
.extractions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* 单条提取规则行 */
.extraction-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

/* 表单标签颜色 */
:deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}

/* 输入框焦点状态 */
:deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
}

/* 输入框悬停状态 */
:deep(.el-input__wrapper:hover:not(.is-focus)) {
  border-color: var(--primary-400);
}

/* 输入框禁用状态 */
:deep(.el-input__wrapper.is-disabled) {
  background-color: var(--surface-muted);
  cursor: not-allowed;
}

/* 数字输入框焦点 */
:deep(.el-input-number:focus-within .el-input__wrapper) {
  box-shadow: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
}

/* 下拉框焦点状态 */
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
}

/* 单选按钮组样式 */
:deep(.el-radio-group) {
  gap: var(--spacing-sm);
}

/* 单选按钮焦点 */
:deep(.el-radio:focus-within .el-radio__inner) {
  box-shadow: 0 0 0 var(--focus-ring-width) var(--focus-ring-color);
}

/* 单选按钮悬停 */
:deep(.el-radio:hover .el-radio__inner) {
  border-color: var(--primary-500);
}

/* 删除按钮悬停 */
:deep(.el-button--danger:hover) {
  color: var(--error-dark);
  background-color: var(--error-bg);
  border-radius: var(--radius-sm);
}

/* 添加规则按钮 */
:deep(.el-button + .el-button) {
  margin-left: var(--spacing-xs);
}

/* 折叠面板内容区域 */
:deep(.el-collapse-item__wrap) {
  border-color: var(--border-subtle);
}

/* 折叠面板标题 */
:deep(.el-collapse-item__header) {
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
  border-color: var(--border-subtle);
}

/* 折叠面板悬停 */
:deep(.el-collapse-item__header:hover) {
  color: var(--primary-600);
}

/* 断言规则容器 */
.assertions-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* 断言规则行 */
.assertion-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  padding: var(--spacing-xs);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
}

/* 空状态提示 */
.empty-hint {
  color: var(--text-muted);
  font-size: var(--text-xs);
  padding: var(--spacing-xs) 0;
  font-style: italic;
}

/* 表单提示文本 */
.form-hint {
  color: var(--text-muted);
  font-size: var(--text-xs);
  margin-top: var(--spacing-xs);
  line-height: var(--leading-relaxed);
}
</style>
