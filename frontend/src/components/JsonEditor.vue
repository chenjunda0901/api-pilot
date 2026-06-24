<template>
  <div class="json-editor" ref="editorContainer" :style="{ height: height + 'px' }"></div>
</template>
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, shallowRef, inject, type Ref } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  readOnly?: boolean
  disableContextMenu?: boolean
  height?: number
}>(), {
  readOnly: false,
  disableContextMenu: false,
  height: 300,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// 从 AppLayout 注入的暗黑模式状态
const isDark = inject<Ref<boolean>>('isDark', ref(false))

const editorContainer = ref<HTMLElement>()
const editor = shallowRef<{ onDidChangeModelContent: (cb: () => void) => void; getValue: () => string; setValue: (v: string) => void; updateOptions: (opts: Record<string, unknown>) => void; getAction: (id: string) => { run: () => void } | null; getSelection: () => { startLineNumber: number; startColumn: number; endLineNumber: number; endColumn: number } | null; getPosition: () => { lineNumber: number; column: number } | null; executeEdits: (source: string, edits: { range: unknown; text: string; forceMoveMarkers: boolean }[]) => void; focus: () => void; dispose: () => void } | null>(null)
const monacoRef = shallowRef<{ editor: { defineTheme: (name: string, theme: Record<string, unknown>) => void; create: (el: HTMLElement, opts: Record<string, unknown>) => unknown; setTheme: (name: string) => void }; Range: new (sl: number, sc: number, el: number, ec: number) => unknown } | null>(null)

onMounted(async () => {
  // 加载中文语言包（必须在 editor.api 之前）
  // @ts-expect-error - Monaco types not available
  await import('monaco-editor/esm/nls.messages.zh-cn.js')

  // Dynamic import Monaco (code-split automatically)
  // @ts-expect-error - Monaco types not available
  const monaco = await import('monaco-editor/esm/vs/editor/editor.api')
  // Register JSON language features (syntax highlighting, completion, etc.)
  // @ts-expect-error - Monaco types not available
  await import('monaco-editor/esm/vs/language/json/monaco.contribution')

  monacoRef.value = monaco

  // 异步导入后组件可能已卸载，检查 DOM 元素是否仍存在
  if (!editorContainer.value) return

  // Define Aqua Fresh theme (亮色)
  monaco.editor.defineTheme('aqua-fresh-json', {
    base: 'vs',
    inherit: false,
    rules: [
      // JSON key — 青蓝 + 加粗
      { token: 'string.key.json', foreground: '0891b2', fontStyle: 'bold' },
      // JSON string value — 薄荷绿
      { token: 'string.value.json', foreground: '059669' },
      // Number — 琥珀
      { token: 'number.json', foreground: 'd97706' },
      // Boolean / Null — 统一紫色（Monaco 无法区分 keyword 子类）
      { token: 'keyword.json', foreground: '8b5cf6' },
      // 大括号/方括号 — 中性灰
      { token: 'delimiter.bracket.json', foreground: '64748b' },
      { token: 'delimiter.square.json', foreground: '64748b' },
    ],
    colors: {
      'editor.background': '#fdfdff',
      'editor.foreground': '#334155',
      'lineNumbers.foreground': '#cbd5e1',
      'editor.lineHighlightBackground': '#f8fafc',
      'editor.selectionBackground': '#e0f2fe',
      'editorCursor.foreground': '#3B82F6',
      'editorScrollbar.sliderBackground': '#e2e8f0',
      'editorScrollbar.sliderHoverBackground': '#94a3b8',
      'lineNumbers.activeForeground': '#3B82F6',
    }
  })

  // Define Aqua Fresh theme (暗色) — 基于 vs-dark
  monaco.editor.defineTheme('aqua-fresh-json-dark', {
    base: 'vs-dark',
    inherit: false,
    rules: [
      // JSON key — 亮青蓝 + 加粗
      { token: 'string.key.json', foreground: '22d3ee', fontStyle: 'bold' },
      // JSON string value — 翠绿
      { token: 'string.value.json', foreground: '34d399' },
      // Number — 琥珀亮
      { token: 'number.json', foreground: 'fbbf24' },
      // Boolean / Null — 淡紫
      { token: 'keyword.json', foreground: 'a78bfa' },
      // 大括号/方括号 — 浅灰
      { token: 'delimiter.bracket.json', foreground: '94a3b8' },
      { token: 'delimiter.square.json', foreground: '94a3b8' },
    ],
    colors: {
      'editor.background': '#0f172a',
      'editor.foreground': '#e2e8f0',
      'lineNumbers.foreground': '#475569',
      'editor.lineHighlightBackground': '#1e293b',
      'editor.selectionBackground': '#164e63',
      'editorCursor.foreground': '#22d3ee',
      'editorScrollbar.sliderBackground': '#334155',
      'editorScrollbar.sliderHoverBackground': '#475569',
      'lineNumbers.activeForeground': '#22d3ee',
    }
  })

  const currentTheme = isDark.value ? 'aqua-fresh-json-dark' : 'aqua-fresh-json'
  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: 'json',
    locale: 'zh-cn',
    theme: currentTheme,
    readOnly: props.readOnly,
    minimap: { enabled: false },
    fontSize: 13,
    fontFamily: '"JetBrains Mono", monospace',
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
    formatOnPaste: true,
    contextmenu: props.disableContextMenu ? false : undefined,
  })

  editor.value.onDidChangeModelContent(() => {
    emit('update:modelValue', editor.value.getValue())
  })
})

// 监听暗黑模式切换，同步 Monaco 主题
watch(isDark, (dark) => {
  if (editor.value && monacoRef.value) {
    monacoRef.value.editor.setTheme(dark ? 'aqua-fresh-json-dark' : 'aqua-fresh-json')
  }
})

onBeforeUnmount(() => {
  editor.value?.dispose()
})

watch(() => props.modelValue, (val) => {
  if (editor.value && val !== editor.value.getValue()) {
    editor.value.setValue(val)
  }
})

watch(() => props.readOnly, (val) => {
  editor.value?.updateOptions({ readOnly: val })
})

watch(() => props.disableContextMenu, (val) => {
  editor.value?.updateOptions({ contextmenu: val ? false : true })
})

function format() {
  editor.value?.getAction('editor.action.formatDocument')?.run()
}

function getEditor() {
  return editor.value
}

function insertAtCursor(text: string) {
  const ed = editor.value
  if (!ed) return
    const sel = ed.getSelection()
    if (sel && monacoRef.value) {
      const Range = monacoRef.value.Range
      const range = new Range(sel.startLineNumber, sel.startColumn, sel.endLineNumber, sel.endColumn)
      ed.executeEdits('insert-variable', [{ range, text, forceMoveMarkers: true }])
      ed.focus()
    } else {
      const pos = ed.getPosition()
      if (pos && monacoRef.value) {
        const Range = monacoRef.value.Range
        const range = new Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column)
        ed.executeEdits('insert-variable', [{ range, text, forceMoveMarkers: true }])
        ed.focus()
      }
    }
}

defineExpose({ format, getEditor, insertAtCursor })
</script>
<style scoped>
/* JsonEditor 容器 — 圆角边框 + 过渡动画 */
.json-editor {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-code);
  transition: border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

/* 聚焦态：主色边框 + 柔和高光 */
.json-editor:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
}

/* 暗色模式适配 */
html.dark .json-editor {
  background: var(--surface-code);
  border-color: var(--border-subtle);
}
html.dark .json-editor:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-16);
}
</style>
