<template>
  <div class="response-example-panel">
    <!-- 添加按钮 -->
    <div class="example-toolbar">
      <button class="add-example-btn" @click="addExample">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
        添加响应示例
      </button>
    </div>

    <!-- 空状态 -->
    <div v-if="!examples || examples.length === 0" class="empty-examples">
      <p class="empty-text">暂无响应示例</p>
      <p class="empty-hint">点击上方按钮添加响应示例，定义接口的预期响应</p>
    </div>

    <!-- 示例卡片列表 -->
    <div v-for="(ex, i) in examples" :key="i" class="example-card">
      <div class="example-header">
        <div class="example-header-left">
          <input
            v-model="ex.name"
            class="example-name-input"
            placeholder="示例名称"
            @input="emitUpdate"
          />
          <select v-model="ex.status_code" class="status-code-select" @change="emitUpdate">
            <option v-for="code in statusCodes" :key="code" :value="code">{{ code }}</option>
          </select>
        </div>
        <button class="delete-example-btn" @click="removeExample(i)" title="删除此示例">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="example-content">
        <!-- 描述 -->
        <div class="example-field">
          <label class="field-label">描述</label>
          <input
            v-model="ex.description"
            class="field-input"
            placeholder="描述此响应示例的用途"
            @input="emitUpdate"
          />
        </div>
        <!-- 响应头 -->
        <div class="example-field">
          <label class="field-label">响应头</label>
          <div class="kv-table">
            <div v-for="(h, hi) in (ex.headers || [])" :key="hi" class="kv-row">
              <input v-model="h.key" class="kv-input" placeholder="Header 名称" @input="emitUpdate" />
              <input v-model="h.value" class="kv-input" placeholder="Header 值" @input="emitUpdate" />
              <button class="kv-remove-btn" @click="removeHeader(ex, hi)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <button class="kv-add-btn" @click="addHeader(ex)">+ 添加响应头</button>
          </div>
        </div>
        <!-- 响应体 -->
        <div class="example-field">
          <label class="field-label">响应体 (JSON)</label>
          <textarea
            v-model="ex.body"
            class="body-editor"
            placeholder='{"code": 0, "data": {}}'
            rows="6"
            @input="emitUpdate"
          ></textarea>
          <span v-if="ex.body && !isValidJson(ex.body)" class="json-error">JSON 格式不正确</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface KvPair {
  key: string
  value: string
}

interface ResponseExample {
  name: string
  status_code: number
  description: string
  headers: KvPair[]
  body: string
}

const props = defineProps<{ examples: ResponseExample[] }>()
const emit = defineEmits<{ 'update:examples': [value: ResponseExample[]] }>()

const statusCodes = [200, 201, 204, 400, 401, 403, 404, 500, 502, 503]

function emitUpdate() {
  emit('update:examples', [...props.examples])
}

function addExample() {
  if (!props.examples) {
    ;(props as { examples: ResponseExample[] }).examples = []
  }
  props.examples.push({
    name: `示例 ${props.examples.length + 1}`,
    status_code: 200,
    description: '',
    headers: [],
    body: '',
  })
  emitUpdate()
}

function removeExample(index: number) {
  props.examples.splice(index, 1)
  emitUpdate()
}

function addHeader(ex: ResponseExample) {
  if (!ex.headers) ex.headers = []
  ex.headers.push({ key: '', value: '' })
  emitUpdate()
}

function removeHeader(ex: ResponseExample, index: number) {
  ex.headers.splice(index, 1)
  emitUpdate()
}

function isValidJson(str: string): boolean {
  try {
    JSON.parse(str)
    return true
  } catch {
    return false
  }
}
</script>

<style scoped>
.response-example-panel {
  padding: var(--space-3);
}

/* 工具栏 */
.example-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-3);
}

.add-example-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--primary-600);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.add-example-btn:hover {
  border-color: var(--primary-300);
  background: var(--surface-hover);
}

/* 空状态 */
.empty-examples {
  text-align: center;
  padding: var(--space-10) 0;
}

.empty-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}

.empty-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
  margin-bottom: 0;
}

/* 示例卡片 */
.example-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
  overflow: hidden;
  background: var(--surface-card);
}

/* 卡片头部 */
.example-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
  gap: var(--space-2);
}

.example-header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.example-name-input {
  flex: 1;
  min-width: 0;
  height: 28px;
  padding: 0 var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  outline: none;
  transition: border-color var(--duration-fast);
}

.example-name-input:hover {
  border-color: var(--border-default);
}

.example-name-input:focus {
  border-color: var(--primary-400);
  background: var(--surface-input);
}

.status-code-select {
  height: 28px;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xs);
  background: var(--surface-input);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  outline: none;
  cursor: pointer;
}

.delete-example-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--duration-fast);
}

.delete-example-btn:hover {
  background: var(--color-danger-alpha-10, rgba(239, 68, 68, 0.1));
  color: var(--color-danger-500, #ef4444);
}

/* 内容区域 */
.example-content {
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.example-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
}

.field-input {
  height: 30px;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xs);
  background: var(--surface-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  outline: none;
  transition: border-color var(--duration-fast);
}

.field-input:focus {
  border-color: var(--primary-400);
}

/* KV 表格 */
.kv-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.kv-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.kv-input {
  flex: 1;
  min-width: 0;
  height: 28px;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xs);
  background: var(--surface-input);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  outline: none;
  transition: border-color var(--duration-fast);
}

.kv-input:focus {
  border-color: var(--primary-400);
}

.kv-remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
}

.kv-remove-btn:hover {
  color: var(--color-danger-500, #ef4444);
}

.kv-add-btn {
  align-self: flex-start;
  padding: 2px 8px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.kv-add-btn:hover {
  border-color: var(--primary-300);
  color: var(--primary-600);
}

/* 响应体编辑器 */
.body-editor {
  width: 100%;
  min-height: 120px;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xs);
  background: var(--surface-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.5;
  resize: vertical;
  outline: none;
  transition: border-color var(--duration-fast);
  box-sizing: border-box;
}

.body-editor:focus {
  border-color: var(--primary-400);
}

.json-error {
  font-size: var(--text-xs);
  color: var(--color-danger-500, #ef4444);
}
</style>
