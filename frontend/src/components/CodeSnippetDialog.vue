<template>
  <el-dialog
    :model-value="visible"
    title="生成请求代码"
    width="700px"
    top="8vh"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="snippet-toolbar">
      <div class="snippet-langs">
        <button
          v-for="lang in languages"
          :key="lang.key"
          class="snippet-lang-btn"
          :class="{ active: activeLang === lang.key }"
          @click="switchLang(lang.key)"
        >
          {{ lang.label }}
        </button>
      </div>
      <el-button size="small" @click="copyCode">复制代码</el-button>
    </div>
    <div class="snippet-body">
      <pre class="snippet-code"><code>{{ code }}</code></pre>
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue"
import request from "@/api/request"
import { msgSuccess, msgWarning } from "@/utils/message"

const props = defineProps<{
  visible: boolean
  projectId: number
  apiId: number
  envId?: number | null
}>()

defineEmits<{
  "update:visible": [v: boolean]
}>()

const languages = [
  { key: "curl", label: "cURL" },
  { key: "python", label: "Python" },
  { key: "javascript", label: "JavaScript" },
  { key: "java", label: "Java" },
  { key: "go", label: "Go" },
  { key: "csharp", label: "C#" },
]

const activeLang = ref("curl")
const code = ref("// 点击语言按钮生成代码")

async function switchLang(lang: string) {
  activeLang.value = lang
  if (!props.apiId) return
  try {
    const res = await request.post(
      `/projects/${props.projectId}/apis/${props.apiId}/code-snippet`,
      { language: lang, environment_id: props.envId || undefined }
    )
    code.value = res.code
  } catch (e: unknown) {
    code.value = `// 生成失败: ${e instanceof Error ? e.message : "未知错误"}`
  }
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(code.value)
    msgSuccess("已复制到剪贴板")
  } catch {
    msgWarning("复制失败，请手动选择复制")
  }
}

watch(
  () => props.visible,
  (v) => {
    if (v) void switchLang(activeLang.value)
  }
)
</script>

<style scoped>
/* 代码片段对话框 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角均使用 CSS 变量，确保暗色模式自动适配
 */
.snippet-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.snippet-langs {
  display: flex;
  gap: var(--spacing-xs);
}

/* 语言切换按钮 */
.snippet-lang-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-xs);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  font-family: inherit;
}

.snippet-lang-btn:hover {
  border-color: var(--primary-500);
  color: var(--primary-600);
  background: var(--color-primary-alpha-04);
}

/* 焦点态：主色环 */
.snippet-lang-btn:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.snippet-lang-btn.active {
  background: var(--primary-500);
  border-color: var(--primary-500);
  color: var(--text-inverse);
}

/* 代码区域 */
.snippet-body {
  background: var(--surface-code);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  max-height: 420px;
  overflow: auto;
}

.snippet-code {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  line-height: var(--leading-relaxed);
  white-space: pre;
}

/* 滚动条美化 */
.snippet-body::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.snippet-body::-webkit-scrollbar-track {
  background: transparent;
}

.snippet-body::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-2xs);
}

.snippet-body::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* 暗色模式 */
:global(html.dark) .snippet-lang-btn { background: var(--surface-nested); border-color: var(--border-default); color: var(--text-muted); }
:global(html.dark) .snippet-lang-btn:hover { border-color: var(--primary-400); color: var(--primary-400); background: var(--surface-hover); }
:global(html.dark) .snippet-lang-btn.active { background: var(--primary-500); border-color: var(--primary-500); color: var(--text-on-primary); }
:global(html.dark) .snippet-body { background: var(--surface-code); border-color: var(--border-subtle); }
:global(html.dark) .snippet-code { color: var(--text-primary); }
</style>
