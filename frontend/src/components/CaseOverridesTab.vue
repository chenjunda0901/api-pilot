<template>
  <div class="overrides-tab">
    <div class="override-section">
      <h4 class="section-title">URL 路径</h4>
      <div class="override-row">
        <span class="override-label">原路径：</span>
        <code class="override-original">{{ parentPath }}</code>
      </div>
      <div class="override-row">
        <span class="override-label">覆盖值：</span>
        <el-input v-model="overrides.path" size="small" placeholder="留空则继承接口路径" aria-label="路径覆盖值" class="override-input" @input="onChange" />
      </div>
    </div>
    <div class="override-section">
      <h4 class="section-title">请求头覆盖</h4>
      <div class="override-hint" v-if="!overrides.headers?.length">未设置覆盖项 — 将继承接口的请求头</div>
      <div v-for="(h, i) in overrides.headers" :key="i" class="override-row">
        <el-input v-model="h.key" size="small" placeholder="请求头" aria-label="请求头名称" class="override-key" />
        <el-input v-model="h.value" size="small" placeholder="值" aria-label="请求头值" class="override-value" />
        <el-button text size="small" @click="removeHeader(i)">删除</el-button>
      </div>
      <el-button size="small" text @click="addHeader">+ 添加覆盖请求头</el-button>
    </div>
    <div class="override-section">
      <h4 class="section-title">查询参数覆盖</h4>
      <div class="override-hint" v-if="!overrides.params?.length">未设置覆盖项 — 将继承接口的查询参数</div>
      <div v-for="(p, i) in overrides.params" :key="i" class="override-row">
        <el-input v-model="p.key" size="small" placeholder="参数名" aria-label="参数名" class="override-key" />
        <el-input v-model="p.value" size="small" placeholder="参数值" aria-label="参数值" class="override-value" />
        <el-button text size="small" @click="removeParam(i)">删除</el-button>
      </div>
      <el-button size="small" text @click="addParam">+ 添加覆盖查询参数</el-button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface OverrideEntry {
  key: string
  value: string
}

interface CaseOverride {
  path: string
  headers: OverrideEntry[]
  params: OverrideEntry[]
}

const props = defineProps<{ modelValue: CaseOverride; parentPath?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: CaseOverride] }>()

const overrides = ref<CaseOverride>({
  path: props.modelValue?.path || '',
  headers: props.modelValue?.headers || [],
  params: props.modelValue?.params || [],
})

const _internalUpdating = ref(false)

watch(() => props.modelValue, (val) => {
  if (_internalUpdating.value) return
  if (val) {
    overrides.value = { path: val.path || '', headers: val.headers || [], params: val.params || [] }
  }
}, { deep: true })

function onChange() {
  _internalUpdating.value = true
  emit('update:modelValue', { ...overrides.value })
  void nextTick(() => { _internalUpdating.value = false })
}
function addHeader() { overrides.value.headers.push({ key: '', value: '' }); onChange() }
function removeHeader(i: number | string) { overrides.value.headers.splice(Number(i), 1); onChange() }
function addParam() { overrides.value.params.push({ key: '', value: '' }); onChange() }
function removeParam(i: number | string) { overrides.value.params.splice(Number(i), 1); onChange() }
</script>
<style scoped>
.overrides-tab { padding: var(--space-1) 0; }
.override-section { margin-bottom: var(--space-5); }
.section-title { font-size: var(--text-sm); font-weight: var(--weight-semibold); margin: 0 0 8px; color: var(--text-primary); }
.override-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.override-label { font-size: var(--text-xs); color: var(--text-secondary); white-space: nowrap; }
.override-original { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }
.override-input { flex: 1; max-width: 400px; }
.override-key { width: 160px; }
.override-value { flex: 1; max-width: 300px; }
.override-hint { font-size: var(--text-xs); color: var(--text-muted); padding: var(--space-2); background: var(--surface-hover); border-radius: var(--radius-xs); margin-bottom: var(--space-2); }
</style>
