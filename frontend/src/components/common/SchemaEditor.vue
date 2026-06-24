<template>
  <div class="schema-editor">
    <!-- 左侧：JSON 编辑 -->
    <div class="schema-edit">
      <div class="schema-edit-head">
        <span>JSON Schema</span>
        <div class="schema-edit-actions">
          <el-button size="small" @click="formatJson" :disabled="!content">格式化</el-button>
          <el-button size="small" type="primary" :loading="generating" @click="generateSample">
            生成示例
          </el-button>
          <el-button size="small" @click="$emit('import-text')">导入</el-button>
        </div>
      </div>
      <textarea
        v-model="content"
        class="schema-textarea"
        spellcheck="false"
        :class="{ 'has-error': jsonError }"
        @blur="onContentChange"
        placeholder='{"type":"object","properties":{"id":{"type":"integer"},"name":{"type":"string"}}}'
      />
      <div v-if="jsonError" class="schema-error">⚠ {{ jsonError }}</div>
    </div>

    <!-- 右侧：预览 -->
    <div class="schema-preview">
      <div class="schema-preview-head">
        <span>实时预览（Mock 数据）</span>
        <el-tag v-if="localSamples.length" size="small" type="success">{{ localSamples.length }} 项</el-tag>
      </div>
      <div class="schema-preview-body">
        <pre v-if="localSamples.length" class="schema-sample"><code>{{ formatJson(localSamples[0]) }}</code></pre>
        <EmptyState
          v-else
          illustration="data"
          title="未生成示例"
          description="点击左上「生成示例」按钮或编辑左侧 Schema"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { msgError, msgWarning } from '@/utils/message'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps<{
  modelValue: string | Record<string, unknown>
  samples?: Array<Record<string, unknown>>
  generating?: boolean
  jsonErrorMessage?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'generate': []
  'import-text': []
  'valid': [valid: boolean]
  'json': [parsed: Record<string, unknown>]
}>()

const content = ref<string>('')
const jsonError = ref<string>('')
const localSamples = ref<Array<Record<string, unknown>>>([])

onMounted(() => {
  if (typeof props.modelValue === 'object') {
    content.value = JSON.stringify(props.modelValue, null, 2)
  } else {
    content.value = props.modelValue || ''
  }
  localSamples.value = props.samples || []
})

watch(
  () => props.modelValue,
  (v) => {
    if (typeof v === 'object') {
      content.value = JSON.stringify(v, null, 2)
    } else if (v !== content.value) {
      content.value = v
    }
  }
)

watch(
  () => props.samples,
  (v) => { localSamples.value = v || [] }
)

function onContentChange() {
  jsonError.value = ''
  if (!content.value.trim()) {
    emit('update:modelValue', '')
    emit('valid', false)
    return
  }
  try {
    const parsed = JSON.parse(content.value)
    emit('update:modelValue', content.value)
    emit('valid', true)
    emit('json', parsed)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'JSON 解析错误'
    jsonError.value = msg
    emit('valid', false)
  }
}

function formatJson(input?: string | Record<string, unknown>) {
  try {
    let obj: unknown
    if (input === undefined) {
      obj = JSON.parse(content.value)
      content.value = JSON.stringify(obj, null, 2)
      jsonError.value = ''
      emit('update:modelValue', content.value)
    } else {
      obj = typeof input === 'string' ? JSON.parse(input) : input
      return JSON.stringify(obj, null, 2)
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'JSON 解析错误'
    if (input === undefined) {
      jsonError.value = msg
      msgError('JSON 格式错误')
    }
  }
}

function generateSample() {
  if (!content.value.trim()) {
    msgWarning('请先填写 Schema')
    return
  }
  if (jsonError.value) {
    msgError('请先修正 JSON 格式')
    return
  }
  emit('generate')
}
</script>

<style scoped>
.schema-editor {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  height: 100%;
  min-height: 360px;
}

.schema-edit,
.schema-preview {
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.schema-edit-head,
.schema-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-hover);
  border-bottom: 1px solid var(--border-subtle);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
}
.schema-edit-actions { display: flex; gap: var(--space-1); }

.schema-textarea {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  padding: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  background: transparent;
  color: var(--text-primary);
  resize: none;
}
.schema-textarea.has-error { background: var(--color-error-alpha-08); }
.schema-error {
  padding: 4px 12px;
  font-size: var(--text-xs);
  color: var(--color-error);
  background: var(--color-error-alpha-08);
  border-top: 1px solid var(--color-error-alpha-20);
}

.schema-preview-body {
  flex: 1;
  padding: var(--space-3);
  overflow: auto;
}
.schema-sample {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-primary);
}

@media (max-width: 768px) {
  .schema-editor { grid-template-columns: 1fr; }
}

/* 暗色模式 */
:global(html.dark) .schema-edit,
:global(html.dark) .schema-preview { background: var(--surface-card); border-color: var(--border-subtle); }
:global(html.dark) .schema-edit-head,
:global(html.dark) .schema-preview-head { background: var(--surface-hover); border-bottom-color: var(--border-subtle); }
:global(html.dark) .schema-textarea { color: var(--text-primary); }
:global(html.dark) .schema-sample { color: var(--text-primary); }
</style>
