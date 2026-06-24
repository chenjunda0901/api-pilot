<template>
  <div class="code-editor-wrapper" ref="editorRef" :style="{ height: computedHeight }"></div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, shallowRef, inject, type Ref } from 'vue'
import { EditorState, Compartment } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLine } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { syntaxHighlighting, defaultHighlightStyle, indentOnInput, bracketMatching, foldGutter, foldKeymap, indentUnit } from '@codemirror/language'
import { javascript } from '@codemirror/lang-javascript'
import { oneDark } from '@codemirror/theme-one-dark'
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete'

const props = withDefaults(defineProps<{
  modelValue: string
  language?: string
  placeholder?: string
  readonly?: boolean
  height?: string
}>(), {
  language: 'javascript',
  placeholder: '',
  readonly: false,
  height: '200px',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const injectedDark = inject<Ref<boolean> | undefined>('isDark', undefined)
const isDark = injectedDark || ref(document.documentElement.classList.contains('dark'))
const editorRef = ref<HTMLElement>()
const view = shallowRef<EditorView | null>(null)

const themeCompartment = new Compartment()

function getThemeExtension() {
  return isDark.value ? oneDark : []
}

const computedHeight = computed(() => props.height)

// Postman API 自动补全词条
const pmCompletions = [
  // pm.variables
  { label: 'pm.variables.get', type: 'function', detail: '获取变量值', info: 'pm.variables.get("key")' },
  { label: 'pm.variables.set', type: 'function', detail: '设置变量值', info: 'pm.variables.set("key", "value")' },
  { label: 'pm.variables.has', type: 'function', detail: '检查变量是否存在', info: 'pm.variables.has("key")' },
  { label: 'pm.variables.replaceIn', type: 'function', detail: '替换模板中的变量', info: 'pm.variables.replaceIn("{{key}}")' },
  { label: 'pm.variables.toObject', type: 'function', detail: '转换为对象', info: 'pm.variables.toObject()' },
  // pm.request
  { label: 'pm.request.headers', type: 'constant', detail: '请求头集合', info: 'pm.request.headers' },
  { label: 'pm.request.url', type: 'constant', detail: '请求 URL 对象', info: 'pm.request.url' },
  { label: 'pm.request.body', type: 'constant', detail: '请求体对象', info: 'pm.request.body' },
  { label: 'pm.request.method', type: 'constant', detail: '请求方法 (GET/POST...)', info: 'pm.request.method' },
  { label: 'pm.request.headers.add', type: 'function', detail: '添加请求头', info: 'pm.request.headers.add({ key: "X-Custom", value: "val" })' },
  { label: 'pm.request.headers.set', type: 'function', detail: '设置请求头', info: 'pm.request.headers.set("X-Custom", "value")' },
  { label: 'pm.request.headers.remove', type: 'function', detail: '移除请求头', info: 'pm.request.headers.remove("X-Custom")' },
  { label: 'pm.request.headers.get', type: 'function', detail: '获取请求头', info: 'pm.request.headers.get("Content-Type")' },
  // pm.response
  { label: 'pm.response', type: 'constant', detail: '响应对象', info: 'pm.response' },
  { label: 'pm.response.json', type: 'function', detail: '解析 JSON 响应体', info: 'pm.response.json()' },
  { label: 'pm.response.text', type: 'function', detail: '获取响应文本', info: 'pm.response.text()' },
  { label: 'pm.response.code', type: 'constant', detail: 'HTTP 状态码', info: 'pm.response.code' },
  { label: 'pm.response.status', type: 'constant', detail: '状态文本 (OK/Not Found)', info: 'pm.response.status' },
  { label: 'pm.response.headers', type: 'constant', detail: '响应头集合', info: 'pm.response.headers' },
  { label: 'pm.response.responseTime', type: 'constant', detail: '响应时间(ms)', info: 'pm.response.responseTime' },
  { label: 'pm.response.size', type: 'constant', detail: '响应大小(bytes)', info: 'pm.response.size' },
  { label: 'pm.response.cookies', type: 'constant', detail: '响应 cookies', info: 'pm.response.cookies' },
  // pm.environment
  { label: 'pm.environment.get', type: 'function', detail: '获取环境变量', info: 'pm.environment.get("key")' },
  { label: 'pm.environment.set', type: 'function', detail: '设置环境变量', info: 'pm.environment.set("key", "value")' },
  { label: 'pm.environment.has', type: 'function', detail: '检查环境变量存在', info: 'pm.environment.has("key")' },
  { label: 'pm.environment.unset', type: 'function', detail: '删除环境变量', info: 'pm.environment.unset("key")' },
  { label: 'pm.environment.clear', type: 'function', detail: '清空所有环境变量', info: 'pm.environment.clear()' },
  // pm.test & pm.iteration
  { label: 'pm.test', type: 'function', detail: '添加测试断言', info: 'pm.test("name", () => { ... })' },
  { label: 'pm.expect', type: 'constant', detail: '断言期望 (chai expect)', info: 'pm.expect(actual)' },
  { label: 'pm.iterationData', type: 'constant', detail: '迭代数据', info: 'pm.iterationData' },
  { label: 'pm.info', type: 'constant', detail: '请求信息 (requestName, requestId)', info: 'pm.info' },
]

// 自定义补全源
const postmanCompletionSource = {
  validFor: /^[\w.]*$/,
  items(context: { matchBefore: (regex: RegExp) => { from: number; to: number; text: string } | null; explicit: boolean }) {
    const word = context.matchBefore(/[\w.]*/)
    if (!word || (word.from === word.to && !context.explicit)) return null
    return pmCompletions
      .filter(c => c.label.toLowerCase().includes(word.text.toLowerCase()))
      .map(c => ({
        label: c.label,
        type: c.type as 'function' | 'constant' | 'variable' | 'keyword' | 'text' | 'match' | undefined,
        detail: c.detail,
        info: c.info,
      }))
  },
}

// placeholder 扩展
const placeholderExt = EditorView.theme({
  '&.cm-focused': {
    '& .cm-placeholder': { color: 'transparent' },
  },
  '.cm-placeholder': {
    color: 'var(--text-disabled)',
    fontStyle: 'italic',
    whiteSpace: 'pre-wrap',
    overflow: 'hidden',
    lineHeight: '1.75',
    pointerEvents: 'none',
    position: 'absolute',
    top: '4px',
    left: '28px',
    right: '4px',
  },
})

let currentDoc = ''

function createExtensions() {
  return [
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    history(),
    foldGutter(),
    drawSelection(),
    dropCursor(),
    EditorState.allowMultipleSelections.of(true),
    indentOnInput(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    bracketMatching(),
    closeBrackets(),
    autocompletion({ override: [postmanCompletionSource] }),
    rectangularSelection(),
    crosshairCursor(),
    highlightActiveLine(),
    indentUnit.of('  '),
    keymap.of([
      ...closeBracketsKeymap,
      ...defaultKeymap,
      ...historyKeymap,
      ...foldKeymap,
      ...completionKeymap,
      indentWithTab,
    ]),
    EditorView.lineWrapping,
    placeholderExt,
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        currentDoc = update.state.doc.toString()
        emit('update:modelValue', currentDoc)
      }
    }),
    EditorState.readOnly.of(props.readonly),
    themeCompartment.of(getThemeExtension()),
    props.language === 'javascript' ? javascript() : [],
  ]
}

function createView() {
  if (!editorRef.value) return

  view.value?.destroy()
  currentDoc = props.modelValue || ''
  const state = EditorState.create({
    doc: currentDoc,
    extensions: createExtensions(),
  })

  view.value = new EditorView({
    state,
    parent: editorRef.value,
  })
}

onMounted(createView)

watch(isDark, () => {
  if (view.value) {
    view.value.dispatch({
      effects: themeCompartment.reconfigure(getThemeExtension())
    })
  }
})

watch(() => props.modelValue, (val) => {
  if (!view.value) return
  const docStr = view.value.state.doc.toString()
  if (val !== docStr) {
    view.value.dispatch({
      changes: { from: 0, to: docStr.length, insert: val || '' },
    })
  }
})

onBeforeUnmount(() => {
  view.value?.destroy()
})

/** 在光标位置插入文本（供父组件通过 ref 调用） */
function insertText(text: string) {
  if (!view.value) return
  const pos = view.value.state.selection.main.head
  view.value.dispatch({
    changes: { from: pos, insert: text },
    selection: { anchor: pos + text.length },
  })
}

defineExpose({ insertText })
</script>

<style scoped>
/* CodeEditor 容器 — 圆角边框 + 聚焦态光环 */
.code-editor-wrapper {
  position: relative;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  min-height: 120px;
  background: var(--surface-code);
  transition: border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

/* 聚焦态：主色边框 + 柔和高光 */
.code-editor-wrapper:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
}

.code-editor-wrapper :deep(.cm-editor) {
  height: 100%;
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
}

.code-editor-wrapper :deep(.cm-editor.cm-focused) {
  outline: none;
}

.code-editor-wrapper :deep(.cm-scroller) {
  overflow: auto;
  font-family: var(--font-mono);
  line-height: 1.75;
}

/* 行号槽：柔和背景 + 分隔线 */
.code-editor-wrapper :deep(.cm-gutters) {
  background: var(--surface-nested);
  border-right: 1px solid var(--border-subtle, var(--border-default));
  padding-right: var(--space-2);
  color: var(--text-muted);
}

.code-editor-wrapper :deep(.cm-lineNumbers .cm-gutterElement) {
  min-width: 32px;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  padding: 0 var(--space-1);
  text-align: right;
}

/* 活跃行高亮 */
.code-editor-wrapper :deep(.cm-activeLineGutter) {
  background: var(--surface-hover);
  border-radius: var(--radius-xs, 2px);
  color: var(--text-primary);
}

.code-editor-wrapper :deep(.cm-activeLine) {
  background: var(--color-primary-alpha-04);
}

.code-editor-wrapper :deep(.cm-content) {
  padding: var(--space-2) var(--space-3);
  background: transparent;
}

/* 暗色模式适配 */
html.dark .code-editor-wrapper {
  background: var(--surface-code);
  border-color: var(--border-subtle);
}
html.dark .code-editor-wrapper:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-16);
}
html.dark .code-editor-wrapper :deep(.cm-gutters) {
  background: var(--surface-nested);
  border-right-color: var(--border-subtle);
  color: var(--text-muted);
}
html.dark .code-editor-wrapper :deep(.cm-activeLineGutter) {
  background: var(--surface-hover);
  color: var(--text-primary);
}
html.dark .code-editor-wrapper :deep(.cm-activeLine) {
  background: var(--color-primary-alpha-06);
}
</style>
