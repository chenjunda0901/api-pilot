<template>
  <div class="cron-editor">
    <!-- 预置模板下拉 -->
    <div class="cron-presets">
      <el-select v-model="presetKey" placeholder="选择预置规则" size="small" clearable @change="onPresetChange">
        <el-option v-for="p in presets" :key="p.key" :label="p.label" :value="p.key" />
      </el-select>
      <span class="cron-preset-desc" v-if="currentPreset">{{ currentPreset.description }}</span>
    </div>

    <!-- 字段式编辑（6 段） -->
    <div class="cron-fields">
      <div v-for="(f, i) in fields" :key="f.key" class="cron-field">
        <el-input
          v-model="cronParts[i]"
          size="small"
          :placeholder="f.placeholder"
        />
        <span class="cron-field-label">{{ f.label }}</span>
      </div>
    </div>

    <!-- 自定义输入 -->
    <el-input
      v-model="customCron"
      size="small"
      placeholder="或直接输入 cron 表达式 (5 或 6 段)"
      @input="onCustomInput"
    >
      <template #append>
        <el-button size="small" @click="validate">校验</el-button>
      </template>
    </el-input>

    <!-- 校验结果 -->
    <div v-if="validation.message" class="cron-validation" :class="validation.valid ? 'ok' : 'err'">
      <span class="cron-validation-icon">{{ validation.valid ? '✓' : '✗' }}</span>
      <span>{{ validation.message }}</span>
    </div>

    <!-- 下次执行时间 -->
    <div v-if="nextRuns.length" class="cron-next-runs">
      <div class="cron-next-head">下次执行时间：</div>
      <ul>
        <li v-for="(t, idx) in nextRuns" :key="idx">{{ formatTime(t) }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { previewNextRuns } from '@/api/schedules'

defineOptions({ name: 'CronEditor' })

const props = defineProps<{
  modelValue: string
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

interface Preset {
  key: string
  label: string
  description: string
  cron: string
}

const presets: Preset[] = [
  { key: 'every_minute', label: '每分钟', description: '每分钟执行一次', cron: '0 * * * * *' },
  { key: 'every_5min', label: '每 5 分钟', description: '每隔 5 分钟执行', cron: '0 */5 * * * *' },
  { key: 'every_hour', label: '每小时', description: '每小时整点执行', cron: '0 0 * * * *' },
  { key: 'daily_9am', label: '每天 9 点', description: '每天上午 9 点执行', cron: '0 0 9 * * *' },
  { key: 'daily_18pm', label: '每天 18 点', description: '每天下午 6 点执行', cron: '0 0 18 * * *' },
  { key: 'weekdays_9am', label: '工作日 9 点', description: '周一至周五 9 点执行', cron: '0 0 9 * * 1-5' },
  { key: 'weekly_mon', label: '每周一 9 点', description: '每周一上午 9 点', cron: '0 0 9 * * 1' },
  { key: 'monthly_1st', label: '每月 1 日', description: '每月 1 日 0 点执行', cron: '0 0 0 1 * *' },
]

const fields = [
  { key: 'sec', label: '秒', placeholder: '0' },
  { key: 'min', label: '分', placeholder: '*' },
  { key: 'hour', label: '时', placeholder: '*' },
  { key: 'day', label: '日', placeholder: '*' },
  { key: 'month', label: '月', placeholder: '*' },
  { key: 'week', label: '周', placeholder: '*' },
]

const presetKey = ref<string>('')
const currentPreset = computed(() => presets.find(p => p.key === presetKey.value))

const cronParts = ref<string[]>(['0', '*', '*', '*', '*', '*'])
const customCron = ref(props.modelValue || '0 * * * * *')

const validation = ref<{ valid: boolean; message: string }>({ valid: true, message: '' })
const nextRuns = ref<string[]>([])

watch(
  () => props.modelValue,
  (v) => {
    customCron.value = v || ''
    syncPartsFromCron(v || '')
  },
  { immediate: true }
)

watch(
  cronParts,
  () => {
    const joined = cronParts.value.join(' ')
    if (joined !== customCron.value) {
      customCron.value = joined
    }
    emit('update:modelValue', joined)
    void fetchNext()
  },
  { deep: true }
)

function syncPartsFromCron(cron: string) {
  const parts = cron.trim().split(/\s+/)
  if (parts.length === 5) {
    cronParts.value = ['0', ...parts]
  } else if (parts.length === 6) {
    cronParts.value = parts.slice(0, 6)
  } else if (parts.length === 0) {
    cronParts.value = ['0', '*', '*', '*', '*', '*']
  }
}

function onPresetChange(key: string) {
  const p = presets.find(x => x.key === key)
  if (!p) return
  cronParts.value = p.cron.split(/\s+/)
  customCron.value = p.cron
  validation.value = { valid: true, message: `已选择预置: ${p.label}` }
}

function onCustomInput(v: string) {
  if (!v) return
  syncPartsFromCron(v)
}

function validate() {
  const v = customCron.value.trim()
  const parts = v.split(/\s+/)
  if (parts.length !== 5 && parts.length !== 6) {
    validation.value = { valid: false, message: 'cron 必须为 5 或 6 段' }
    return
  }
  validation.value = { valid: true, message: '表达式有效' }
  void fetchNext()
}

async function fetchNext() {
  const v = customCron.value.trim()
  if (!v) {
    nextRuns.value = []
    return
  }
  try {
    const res = await previewNextRuns(v, 5)
    nextRuns.value = res.data.runs
    if (nextRuns.value.length) {
      validation.value = { valid: true, message: `有效，将执行 ${nextRuns.value.length} 次` }
    }
  } catch {
    nextRuns.value = []
  }
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString()
  } catch { return iso }
}

function matchPreset() {
  const matched = presets.find(p => p.cron === customCron.value)
  if (matched) presetKey.value = matched.key
}

onMounted(() => {
  matchPreset()
})
</script>

<style scoped>
.cron-editor { display: flex; flex-direction: column; gap: var(--space-3); }

.cron-presets { display: flex; align-items: center; gap: var(--space-2); }
.cron-preset-desc { color: var(--text-muted); font-size: var(--text-xs); }

.cron-fields { display: flex; gap: var(--space-1); align-items: center; }
.cron-field { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.cron-field-label { font-size: var(--text-2xs); color: var(--text-muted); text-align: center; }

.cron-validation {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}
.cron-validation.ok { background: var(--color-success-alpha-12); color: var(--color-success); }
.cron-validation.err { background: var(--color-error-alpha-12); color: var(--color-error); }
.cron-validation-icon { font-weight: var(--weight-bold); }

.cron-next-runs {
  background: var(--surface-hover);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
}
.cron-next-head { font-weight: var(--weight-semibold); margin-bottom: var(--space-1); color: var(--text-secondary); }
.cron-next-runs ul { list-style: none; padding: 0; margin: 0; }
.cron-next-runs li { padding: 2px 0; color: var(--text-muted); font-family: var(--font-mono); }
</style>
