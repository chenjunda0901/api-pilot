<template>
  <div class="variable-preview" :class="`mode-${mode}`">
    <div class="preview-header">
      <span class="preview-title">{{ title }}</span>
    </div>
    <div class="preview-body">
      <!-- API 模式 -->
      <template v-if="mode === 'api'">
        <div class="used-variables">
          <div class="section-title">当前请求用到的变量</div>
          <div v-if="parsedVariables.length === 0" class="empty-hint">无</div>
          <div v-else class="var-list">
            <div v-for="(v, idx) in parsedVariables" :key="idx" class="var-item">
              <span class="var-expr">{{ v.expression }}</span>
              <span class="var-arrow">→</span>
              <span class="var-value">{{ v.resolved || "(未定义)" }}</span>
            </div>
          </div>
        </div>
        <div class="all-variables">
          <div class="section-title">当前环境全部变量</div>
          <div v-for="group in allVariables" :key="group.label" class="var-group">
            <div class="group-label">{{ group.label }}</div>
            <div v-for="item in group.items" :key="item.key" class="var-item">
              <span class="var-key">{{ item.key }}</span>
              <span class="var-eq">=</span>
              <span class="var-val">{{ item.value }}</span>
            </div>
          </div>
        </div>
        <div class="copy-json-row" v-if="mode === 'api'">
          <el-button size="small" @click="copyAsJson">复制为 JSON</el-button>
        </div>
      </template>

      <!-- 场景模式 -->
      <template v-if="mode === 'scene'">
        <div class="warning-banner" v-if="undefinedVars.length > 0">
          ⚠️ 检测到 {{ undefinedVars.length }} 个未定义变量
          <span v-for="v in undefinedVars" :key="v" class="undefined-item">{{ v }}</span>
        </div>
        <div class="var-source-list">
          <div v-for="group in varSources" :key="group.label" class="source-group">
            <div class="source-label">{{ group.label }}</div>
            <div v-if="group.variables.length === 0" class="empty-hint">无</div>
            <div v-for="v in group.variables" :key="v.name" class="var-item">
              <span class="var-name">{{ v.name }}</span>
              <span class="var-eq">=</span>
              <span class="var-val">{{ v.value || "(空)" }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- EnvManager 模式 -->
      <template v-if="mode === 'envManager'">
        <div class="var-filter-bar">
          <el-input
            v-model="varSearchQuery"
            placeholder="搜索变量名..."
            clearable
            size="small"
            :prefix-icon="SearchIcon"
          />
          <span class="var-count">显示 {{ filteredVariables.length }} / {{ allVarsCount }}</span>
        </div>
        <div class="env-all-vars">
          <div v-if="services.length > 0" class="var-section">
            <div class="section-label">服务地址</div>
            <div v-for="s in services" :key="s.name" class="var-item">
              <span class="var-name">{{ s.name }}</span>
              <span class="var-eq">:</span>
              <span class="var-val">{{ s.url }}</span>
            </div>
          </div>
          <div v-if="filteredVariables.length > 0" class="var-section">
            <div class="section-label">全局变量</div>
            <div v-for="v in filteredVariables" :key="v.key" class="var-item">
              <span class="var-name">{{ v.key }}</span>
              <span class="var-eq">=</span>
              <span class="var-val">{{ v.value }}</span>
            </div>
          </div>
          <div v-if="headers.length > 0" class="var-section">
            <div class="section-label">全局请求头</div>
            <div v-for="h in headers" :key="h.key" class="var-item">
              <span class="var-name">{{ h.key }}</span>
              <span class="var-eq">:</span>
              <span class="var-val">{{ h.value }}</span>
            </div>
          </div>
          <div
            v-if="services.length === 0 && variables.length === 0 && headers.length === 0"
            class="empty-hint"
          >
            暂无变量
          </div>
        </div>
        <div class="copy-json-row">
          <el-button size="small" @click="copyAsJson">复制为 JSON</el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { msgSuccess, msgError } from "@/utils/message"
import { logger } from "@/utils/logger"
import { Search as SearchIcon } from "lucide-vue-next"

interface ServiceItem {
  name: string
  module: string
  url: string
  is_base?: boolean
}
interface VariableItem {
  key: string
  value: string
  enabled: boolean
}
interface HeaderItem {
  key: string
  value: string
  enabled: boolean
}
interface SceneStepExtract {
  [key: string]: string
}
interface SceneStepRequestData {
  url?: string
  path?: string
  body?: string
  headers?: string
  params?: string
  [key: string]: string | undefined
}
interface SceneStep {
  extract_variables?: string | SceneStepExtract
  request_data?: SceneStepRequestData
}
interface VarSourceGroup {
  label: string
  variables: { name: string; value: string }[]
}

const props = withDefaults(
  defineProps<{
    mode: "api" | "scene" | "envManager"
    title?: string
    // API 模式
    requestExpressions?: string[]
    allVars?: { services: ServiceItem[]; variables: VariableItem[]; headers: HeaderItem[] }
    // 场景模式
    sceneSteps?: SceneStep[]
    // EnvManager 模式
    services?: ServiceItem[]
    variables?: VariableItem[]
    headers?: HeaderItem[]
  }>(),
  {
    title: "变量预览",
    services: () => [],
    variables: () => [],
    headers: () => [],
    requestExpressions: () => [],
    sceneSteps: () => [],
    allVars: () => ({ services: [], variables: [], headers: [] }),
  }
)

const varSearchQuery = ref('')

// === EnvManager 模式搜索过滤 ===
const allVarsCount = computed(() => (props.variables || []).length)
const filteredVariables = computed(() => {
  const query = varSearchQuery.value.trim().toLowerCase()
  if (!query) return props.variables || []
  return (props.variables || []).filter((v: VariableItem) =>
    v.key.toLowerCase().includes(query)
  )
})

// === API 模式 ===
const parsedVariables = computed(() => {
  return props.requestExpressions.map((expr) => {
    const match = expr.match(/\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/)
    const varName = match ? match[1] : null
    let resolved = ""
    if (varName) {
      const allVars = props.allVars
      const found = allVars.variables.find((v) => v.key === varName)
      resolved = found ? found.value : ""
    }
    return { expression: expr, resolved }
  })
})

const allVariables = computed(() => {
  const allVars = props.allVars || { services: [], variables: [], headers: [] }
  let services = allVars.services
  if (typeof services === 'string') {
    try { services = JSON.parse(services) } catch { services = [] }
  }
  if (!Array.isArray(services)) services = []
  let variables = allVars.variables
  if (typeof variables === 'string') {
    try { variables = JSON.parse(variables) } catch { variables = [] }
  }
  if (!Array.isArray(variables)) variables = []
  let headers = allVars.headers
  if (typeof headers === 'string') {
    try { headers = JSON.parse(headers) } catch { headers = [] }
  }
  if (!Array.isArray(headers)) headers = []
  return [
    { label: "服务地址", items: services.map((s) => ({ key: s.name, value: s.url })) },
    {
      label: "全局变量",
      items: variables
        .filter((v) => v.enabled)
        .map((v) => ({ key: v.key, value: v.value })),
    },
    {
      label: "请求头",
      items: headers.filter((h) => h.enabled).map((h) => ({ key: h.key, value: h.value })),
    },
  ].filter((g) => g.items.length > 0)
})

// === 场景模式 ===
const varSources = computed((): VarSourceGroup[] => {
  const steps = props.sceneSteps || []
  const envVars = (props.allVars?.variables || []).filter((v) => v.enabled)
  const stepExtracts: { name: string; value: string }[] = []
  const manualVars: { name: string; value: string }[] = []

  steps.forEach((step: SceneStep) => {
    if (step.extract_variables) {
      try {
        const extracted =
          typeof step.extract_variables === "string"
            ? (JSON.parse(step.extract_variables) as SceneStepExtract)
            : step.extract_variables
        Object.entries(extracted).forEach(([key, val]: [string, string]) => {
          stepExtracts.push({ name: key, value: String(val) })
        })
      } catch (err) {
        logger.warn('[VariablePreview] parse extract_variables failed:', err)
      }
    }
    const reqData = step.request_data || {}
    const textFields: (keyof SceneStepRequestData)[] = ["url", "path", "body", "headers", "params"]
    textFields.forEach((field) => {
      if (reqData[field]) {
        const matches = String(reqData[field]).matchAll(/\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/g)
        for (const m of matches) {
          if (!manualVars.find((v) => v.name === m[1])) {
            manualVars.push({ name: m[1], value: "(待替换)" })
          }
        }
      }
    })
  })

  return [
    { label: "环境变量", variables: envVars.map((v) => ({ name: v.key, value: v.value })) },
    { label: "步骤提取", variables: stepExtracts },
    { label: "手动引用", variables: manualVars },
  ]
})

const undefinedVars = computed((): string[] => {
  const defined = new Set<string>([
    ...(props.allVars?.variables || []).map((v: VariableItem) => v.key),
    ...(props.allVars?.services || []).map((s: ServiceItem) => s.name),
    ...(props.allVars?.headers || []).map((h: HeaderItem) => h.key),
  ])
  const used: string[] = []
  ;(props.sceneSteps || []).forEach((step: SceneStep) => {
    const reqData = step.request_data || {}
    const textFields: (keyof SceneStepRequestData)[] = ["url", "path", "body", "headers", "params"]
    textFields.forEach((field) => {
      if (reqData[field]) {
        const matches = String(reqData[field]).matchAll(/\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/g)
        for (const m of matches) used.push(m[1])
      }
    })
  })
  return [...new Set(used)].filter((u) => !defined.has(u))
})

// === EnvManager 模式 ===
async function copyAsJson() {
  const data = {
    services: props.services,
    variables: props.variables,
    headers: props.headers,
  }
  try {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    msgSuccess("已复制到剪贴板")
  } catch {
    msgError("复制失败")
  }
}
</script>

<style scoped>
/* ==========================================
 * VariablePreview — 变量预览面板样式
 * ==========================================
 * 用于显示当前请求/场景/环境中的变量
 * 支持三种模式：api、scene、envManager
 * ========================================== */

/* 预览容器 */
.variable-preview {
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
  padding: 0 var(--space-3);
  border: 1px solid var(--border-subtle);
}

/* 头部：标题 */
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
  color: var(--text-secondary);
}

.preview-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  letter-spacing: 0.01em;
}

/* 主体内容区 */
.preview-body {
  padding: var(--space-2) 0;
}

/* 分区标题（如"当前请求用到的变量"） */
.section-title {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-2);
  font-weight: var(--weight-semibold);
}

/* 变量列表容器 */
.var-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* 单个变量项（通用） */
.var-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  min-width: 0;
}

/* 变量表达式（如 {{token}}） */
.var-expr {
  color: var(--primary-600);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 箭头分隔符（→） */
.var-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 变量值 */
.var-value {
  color: var(--text-primary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 变量键名 */
.var-key {
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 等号分隔符（=） */
.var-eq {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 变量值（通用） */
.var-val {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 变量分组容器 */
.var-group {
  margin-bottom: var(--space-3);
}

/* 分组标签（如"全局变量"） */
.group-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: var(--space-1);
  letter-spacing: var(--tracking-wide);
}

/* 来源分组容器（场景模式） */
.source-group {
  margin-bottom: var(--space-3);
}

/* 来源标签（如"环境变量"、"步骤提取"） */
.source-label {
  font-size: var(--text-xs);
  color: var(--primary-600);
  text-transform: uppercase;
  margin-bottom: var(--space-1);
  letter-spacing: var(--tracking-wide);
}

/* 警告横幅（未定义变量提示） */
.warning-banner {
  background: var(--color-error-alpha-12);
  color: var(--error-text);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
  font-size: var(--text-sm);
}

/* 未定义变量标签 */
.undefined-item {
  background: var(--error);
  color: var(--text-inverse);
  padding: var(--space-1);
  border-radius: var(--radius-xs);
  margin-left: var(--space-1);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

/* 变量分区容器（EnvManager 模式） */
.var-section {
  margin-bottom: var(--space-3);
}

/* 分区标签（如"服务地址"、"全局变量"） */
.section-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: var(--space-1);
  letter-spacing: var(--tracking-wide);
}

/* 复制 JSON 按钮行 */
.copy-json-row {
  margin-top: var(--space-3);
}

/* 空状态提示 */
.empty-hint {
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: var(--space-1) 0;
}

/* 变量搜索栏（EnvManager 模式） */
.var-filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

/* 变量计数显示 */
.var-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

/* 暗色模式适配 */
html.dark .variable-preview {
  background: var(--surface-hover);
  border-color: var(--border-subtle);
}
html.dark .var-expr { color: var(--primary-400); }
html.dark .source-label { color: var(--primary-400); }
html.dark .preview-title { color: var(--text-secondary); }
html.dark .section-title { color: var(--text-muted); }
</style>
