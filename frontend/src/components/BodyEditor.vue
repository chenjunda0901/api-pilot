<template>
  <div class="body-editor">
    <div v-if="bodyNotSupported" class="method-disabled-hint">
      <FileX2 :size="24" class="none-icon" />
      <p>{{ (props.method || 'GET').toUpperCase() }} 请求不支持请求体</p>
      <span class="none-sub">只有 POST、PUT、PATCH 方法可以携带请求体</span>
    </div>
    <div v-else>
    <div class="body-type-tabs">
      <button
        v-for="t in types"
        :key="t.key"
        class="type-tab"
        :class="{ active: bodyType === t.key }"
        @click="switchType(t.key)"
      >
        {{ t.label }}
      </button>
    </div>
    <div class="body-content">
      <div v-if="bodyType === 'json'" class="json-editor-wrapper">
        <JsonEditor
          ref="jsonEditorRef"
          v-model="jsonContent"
          :disable-context-menu="true"
        />
      </div>
      <FormTable
        v-else-if="bodyType === 'form-data' || bodyType === 'x-www-form-urlencoded'"
        v-model="formContent"
        :body-type="bodyType"
      />
      <el-input
        v-else-if="bodyType === 'text'"
        v-model="textContent"
        type="textarea"
        :rows="6"
      />
      <el-input
        v-else-if="bodyType === 'xml'"
        v-model="xmlContent"
        type="textarea"
        :rows="6"
        placeholder='&#x3C;root&#x3E;\n  &#x3C;item id=&#x22;1&#x22;&#x3E;example&#x3C;/item&#x3E;\n&#x3C;/root&#x3E;'
      />
      <div v-else-if="bodyType === 'graphql'" class="graphql-editor">
        <div class="gql-section">
          <span class="gql-label">Query</span>
          <el-input v-model="graphqlQuery" type="textarea" :rows="8" placeholder="# GraphQL 查询" aria-label="GraphQL查询语句" class="gql-textarea" @input="onGraphqlChange" />
        </div>
        <div class="gql-section">
          <span class="gql-label">Variables (JSON)</span>
          <el-input v-model="graphqlVariables" type="textarea" :rows="4" placeholder='{ "id": 1 }' aria-label="GraphQL变量JSON" class="gql-textarea" @input="onGraphqlChange" />
        </div>
      </div>
      <div v-else-if="bodyType === 'binary'" class="binary-tab">
        <div class="binary-hint">
          <Upload :size="24" class="binary-icon" />
          <p>选择文件作为请求体发送</p>
          <el-upload
            class="binary-upload"
            :show-file-list="false"
            :before-upload="handleBinaryUpload"
          >
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </div>
      </div>
      <div v-else class="none-hint">
        <FileX2 :size="24" class="none-icon" />
        <p>当前请求不包含请求体</p>
        <span class="none-sub">选择上方的请求体类型以添加内容</span>
      </div>
    </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Upload, FileX2 } from 'lucide-vue-next'
import JsonEditor from './JsonEditor.vue'
import FormTable from './FormTable.vue'

const jsonEditorRef = ref<InstanceType<typeof JsonEditor> | null>(null)

interface BodyConfig {
  type: string
  content?: string | Record<string, unknown>[]
  form?: Record<string, unknown>[]
  graphql?: { query: string; variables: string }
  file_name?: string
  file_size?: number
}

const props = defineProps<{
  modelValue: BodyConfig
  method?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: BodyConfig] }>()

const bodyNotSupported = computed(() => ['GET', 'DELETE', 'HEAD'].includes((props.method || '').toUpperCase()))

const types = [
  { key: 'none', label: 'none' },
  { key: 'form-data', label: 'form-data' },
  { key: 'x-www-form-urlencoded', label: 'urlencoded' },
  { key: 'json', label: 'JSON' },
  { key: 'xml', label: 'XML' },
  { key: 'text', label: 'Text' },
  { key: 'graphql', label: 'GraphQL' },
  { key: 'binary', label: 'Binary' },
]

const bodyType = ref(props.modelValue?.type || 'none')
function tryFormatJson(raw: string | Record<string, unknown>): string {
  const str = typeof raw === 'string' ? raw : JSON.stringify(raw)
  try {
    const parsed = JSON.parse(str)
    // 是对象/数组才格式化，字符串等原始类型保持原样
    if (parsed !== null && typeof parsed === 'object') {
      return JSON.stringify(parsed, null, 2)
    }
    return str
  } catch {
    return str
  }
}

const jsonContent = ref(tryFormatJson(props.modelValue?.content))
// 兼容导入的 content（JSON字符串/数组）和 UI 创建的 form 字段
function _initFormData(): Record<string, unknown>[] {
  const raw = props.modelValue?.content ?? props.modelValue?.form
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed : []
    } catch { return [] }
  }
  return []
}
const formContent = ref(_initFormData())
// 即时同步 formContent 变更到父组件
watch(formContent, (val) => {
  emit('update:modelValue', { ...props.modelValue, content: val })
}, { deep: true })
const textContent = ref(props.modelValue?.type === 'text' ? (props.modelValue?.content as string || '') : '')
watch(textContent, (val) => {
  emit('update:modelValue', { ...props.modelValue, content: val })
})
const xmlContent = ref(props.modelValue?.type === 'xml' ? (props.modelValue?.content as string || '') : '')
watch(xmlContent, (val) => {
  emit('update:modelValue', { ...props.modelValue, content: val })
})
const graphqlQuery = ref('')
const graphqlVariables = ref('')

watch(bodyType, (type) => {
  // 根据类型获取对应的已存储内容，避免切换类型时内容丢失
  let content: string | Record<string, unknown>[] = ''
  if (type === 'json') {
    content = jsonContent.value
  } else if (type === 'xml') {
    content = xmlContent.value
  } else if (type === 'text') {
    content = textContent.value
  } else if (type === 'form-data' || type === 'x-www-form-urlencoded') {
    content = formContent.value
  } else if (type === 'graphql') {
    content = ''
  } else {
    content = ''
  }
  emit('update:modelValue', { ...props.modelValue, type, content })
})

watch(jsonContent, (val) => {
  emit('update:modelValue', { ...props.modelValue, content: val })
})

watch(() => props.modelValue, (val) => {
  if (!val) return
  bodyType.value = val.type || 'none'
  if (val.type === 'json') {
    const formatted = tryFormatJson(val.content)
    // 深度比较：格式化结果与当前值相同时跳过赋值，防止 watch(→emit→update→watch) 死循环
    if (formatted !== jsonContent.value) {
      jsonContent.value = formatted
    }
  }
  if (val.type === 'form-data' || val.type === 'x-www-form-urlencoded') {
    const raw = val.content ?? val.form
    if (Array.isArray(raw)) {
      formContent.value = raw
    } else if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw)
        formContent.value = Array.isArray(parsed) ? parsed : []
      } catch { formContent.value = [] }
    } else {
      formContent.value = []
    }
  }
  if (val.type === 'graphql' && val.graphql) {
    graphqlQuery.value = val.graphql.query || ''
    graphqlVariables.value = val.graphql.variables || ''
  }
}, { deep: true })

function switchType(key: string) {
  bodyType.value = key
}

function onGraphqlChange() {
  emit('update:modelValue', {
    type: 'graphql',
    graphql: { query: graphqlQuery.value, variables: graphqlVariables.value }
  })
}

function handleBinaryUpload(file: File) {
  emit('update:modelValue', { type: 'binary', file_name: file.name, file_size: file.size })
  return false
}
</script>
<style scoped>
/* ==========================================
 * Body Editor — 请求体编辑器样式
 * ========================================== */

.body-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* 类型切换标签页 */
.body-type-tabs {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
  padding: var(--space-1);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  overflow-x: auto;
  position: relative;
  scrollbar-width: thin;
  border: 1px solid var(--border-subtle);
}

/* 右侧渐隐遮罩，提示可横向滚动 */
.body-type-tabs::after {
  content: '';
  position: sticky;
  right: 0;
  width: 32px;
  height: 100%;
  background: linear-gradient(90deg, transparent, var(--surface-nested));
  pointer-events: none;
  flex-shrink: 0;
  margin-left: auto;
}

.type-tab {
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  border-radius: var(--radius-sm);
  font-weight: var(--weight-medium);
  transition: all var(--duration-fast) var(--ease-smooth);
}

.type-tab:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.type-tab.active {
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
  background: var(--surface-card);
  box-shadow: var(--shadow-xs);
}

/* JSON 编辑器容器 */
.json-editor-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

/* 无请求体提示 */
.none-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex: 1;
  min-height: 240px;
  text-align: center;
  color: var(--text-disabled);
  font-size: var(--text-sm);
  animation: none-hint-appear 0.4s var(--ease-spring) backwards;
}

@keyframes none-hint-appear {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.none-icon {
  color: var(--text-muted);
  opacity: 0.6;
}

.none-sub {
  color: var(--text-disabled);
  font-size: var(--text-xs);
}

/* GET/DELETE/HEAD 方法不支持请求体提示 */
.method-disabled-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex: 1;
  min-height: 240px;
  text-align: center;
  color: var(--text-disabled);
  font-size: var(--text-sm);
}

/* GraphQL 编辑器 */
.graphql-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.gql-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

.gql-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
}

.gql-textarea :deep(.el-textarea__inner) {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
}

/* 二进制文件上传 */
.binary-tab {
  padding: var(--space-5);
}

.binary-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.binary-icon {
  color: var(--text-muted);
  opacity: 0.6;
}

/* 暗色模式 */
html.dark .body-type-tabs {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .type-tab.active {
  background: var(--surface-card);
}

html.dark .json-editor-wrapper {
  border-color: var(--border-subtle);
}
</style>
