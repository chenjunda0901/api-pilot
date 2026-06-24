<template>
  <div class="var-scope-panel">
    <div v-if="loading" class="var-scope-loading">
      <span>加载变量中...</span>
    </div>
    <div v-else-if="!effective" class="var-scope-empty">
      <span>暂无变量数据</span>
    </div>
    <div v-else class="var-scope-body">
      <!-- 5 层作用域 -->
      <div class="var-layers">
        <div
          v-for="layer in effective.layers"
          :key="layer.scope + (layer.scope_id ?? '')"
          class="var-layer"
        >
          <div class="var-layer-head">
            <span class="var-layer-name">{{ layer.scope_name }}</span>
            <el-tag size="small" :type="scopeTagType(layer.scope)">{{ layer.variables.length }}</el-tag>
          </div>
          <div class="var-layer-vars">
            <div
              v-for="v in layer.variables"
              :key="v.key"
              class="var-item"
              :class="{ encrypted: v.encrypted }"
            >
              <span class="var-key">{{ v.key }}</span>
              <span class="var-value">
                <code v-if="!v.encrypted">{{ v.value || '(空)' }}</code>
                <template v-else>
                  <code v-if="revealedVars[v.key]">{{ revealedVars[v.key] }}</code>
                  <span v-else class="var-masked">••••••••</span>
                </template>
              </span>
              <el-button
                v-if="v.encrypted"
                link
                size="small"
                @click="reveal(v)"
                :loading="revealing === v.key"
              >{{ revealedVars[v.key] ? '隐藏' : '显示' }}</el-button>
              <el-button
                v-if="v.encrypted && revealedVars[v.key]"
                link
                size="small"
                @click="copyRevealed(v.key)"
              >复制</el-button>
            </div>
            <div v-if="!layer.variables.length" class="var-layer-empty">无</div>
          </div>
        </div>
      </div>

      <!-- 当前生效值 -->
      <div class="var-effective">
        <div class="var-effective-head">
          <span>当前请求生效值</span>
          <el-tag size="small" type="info">{{ Object.keys(effective.effective).length }} 项</el-tag>
        </div>
        <div class="var-effective-list">
          <div v-for="(value, key) in effective.effective" :key="key" class="var-effective-item">
            <span class="var-key">{{ key }}</span>
            <code class="var-value">{{ value }}</code>
          </div>
          <div v-if="!Object.keys(effective.effective).length" class="var-effective-empty">
            暂无生效变量
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { msgSuccess, msgError, msgInfo } from '@/utils/message'
import {
  getEffectiveVariables, revealEncryptedVariable,
  type EffectiveVariablesResponse, type VariableScope,
} from '@/api/variables'

const props = defineProps<{
  projectId: number
  environmentId?: number
  sceneId?: number
  caseId?: number
}>()

const loading = ref(false)
const effective = ref<EffectiveVariablesResponse | null>(null)
const revealing = ref<string | null>(null)
const revealedVars = ref<Record<string, string>>({})

async function load() {
  if (!props.projectId) return
  loading.value = true
  try {
    const res = await getEffectiveVariables(props.projectId, {
      environment_id: props.environmentId,
      scene_id: props.sceneId,
      case_id: props.caseId,
    })
    effective.value = res.data
  } catch {
    effective.value = null
  } finally {
    loading.value = false
  }
}

async function reveal(v: { key: string }) {
  // 如果已显示，则隐藏
  if (revealedVars.value[v.key]) {
    delete revealedVars.value[v.key]
    revealedVars.value = { ...revealedVars.value }
    return
  }
  revealing.value = v.key
  try {
    const res = await revealEncryptedVariable(props.projectId, v.key)
    revealedVars.value[v.key] = res.data.value
    revealedVars.value = { ...revealedVars.value }
  } catch {
    msgError('获取失败')
  } finally {
    revealing.value = null
  }
}

async function copyRevealed(key: string) {
  const value = revealedVars.value[key]
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    msgSuccess('已复制到剪贴板')
  } catch {
    msgInfo(value)
  }
}

function scopeTagType(scope: VariableScope): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  switch (scope) {
    case 'global': return 'primary'
    case 'project': return 'success'
    case 'environment': return 'warning'
    case 'scene': return 'info'
    case 'case': return 'danger'
    default: return 'info'
  }
}

onMounted(load)
watch(
  () => [props.projectId, props.environmentId, props.sceneId, props.caseId],
  () => load()
)
</script>

<style scoped>
.var-scope-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.var-scope-loading,
.var-scope-empty {
  text-align: center;
  color: var(--text-muted);
  padding: var(--space-4);
}

.var-scope-body { display: flex; flex-direction: column; gap: var(--space-4); }

.var-layers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-2);
}

.var-layer {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.var-layer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-hover);
  border-bottom: 1px solid var(--border-subtle);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
}

.var-layer-vars { padding: var(--space-2); display: flex; flex-direction: column; gap: 2px; }
.var-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  padding: 2px 4px;
  border-radius: 3px;
}
.var-item:hover { background: var(--surface-hover); }
.var-item.encrypted .var-value { font-family: var(--font-mono); }
.var-key { color: var(--primary-600); font-weight: var(--weight-semibold); }
.var-value { flex: 1; color: var(--text-secondary); word-break: break-all; font-family: var(--font-mono); }
.var-masked { color: var(--text-muted); letter-spacing: 2px; }
.var-layer-empty { color: var(--text-muted); font-size: var(--text-xs); text-align: center; padding: 4px; }

.var-effective {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
.var-effective-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  font-weight: var(--weight-semibold);
}
.var-effective-list { display: flex; flex-direction: column; gap: 2px; }
.var-effective-item { display: flex; gap: var(--space-2); font-size: var(--text-xs); }
.var-effective-empty { color: var(--text-muted); font-size: var(--text-xs); }
</style>
