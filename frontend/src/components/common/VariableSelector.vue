<template>
  <div>
    <Teleport to="body">
    <div v-if="visible" class="variable-selector-overlay" @click.self="close">
      <div class="variable-selector-panel">
        <div class="vs-header">
          <span class="vs-title">插入变量</span>
          <button class="vs-close" aria-label="关闭" @click="close"><X :size="14" /></button>
        </div>

        <div class="vs-search">
          <el-input
            v-model="searchText"
            size="small"
            placeholder="搜索变量..." aria-label="搜索变量"
          />
        </div>

        <div class="vs-body">
          <!-- 环境全局变量 -->
          <div v-if="filteredGlobalVariables.length > 0" class="vs-section">
            <div class="vs-section-title">环境全局变量</div>
            <div
              v-for="v in filteredGlobalVariables"
              :key="v.key"
              class="vs-item"
              tabindex="0"
              role="option"
              @click="selectVariable(v.key)"
              @keydown.enter="selectVariable(v.key)"
            >
              <span class="vs-var-name" v-text="'{{' + v.key + '}}'"></span>
              <span class="vs-var-preview">{{ v.value || '(无值)' }}</span>
            </div>
          </div>

          <!-- 步骤提取变量 -->
          <div v-if="filteredStepVariables.length > 0" class="vs-section">
            <div class="vs-section-title">步骤提取变量</div>
            <template v-for="step in filteredStepVariables" :key="step.index">
              <div class="vs-step-header">{{ step.index + 1 }}. {{ step.label }}</div>
              <div
                v-for="v in step.variables"
                :key="v.name"
                class="vs-item"
                tabindex="0"
                role="option"
                @click="selectVariable(v.name)"
                @keydown.enter="selectVariable(v.name)"
              >
                <span class="vs-var-name" v-text="'{{' + v.name + '}}'"></span>
                <span class="vs-var-source">= {{ v.path || v.header_name }}</span>
                <span v-if="v.lastValue" class="vs-var-preview">"{{ v.lastValue }}"</span>
              </div>
            </template>
          </div>

          <!-- 随机变量 -->
          <div v-if="filteredRandomVariables.length > 0" class="vs-section">
            <div class="vs-section-title">随机变量</div>
            <div
              v-for="item in filteredRandomVariables"
              :key="item.label"
              class="vs-item"
              tabindex="0"
              role="option"
              @click="selectRandom(item)"
              @keydown.enter="selectRandom(item)"
            >
              <span class="vs-var-name">{{ item.label }}</span>
              <span class="vs-var-source">{{ item.desc }}</span>
              <span v-if="item.preview" class="vs-var-preview">{{ item.preview }}</span>
            </div>
          </div>

          <div v-if="filteredGlobalVariables.length === 0 && filteredStepVariables.length === 0" class="vs-empty">
            暂无可用变量
          </div>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { X } from 'lucide-vue-next'

interface GlobalVariable {
  key: string
  value: string
}

interface StepVariable {
  name: string
  path?: string
  header_name?: string
  lastValue?: string
}

interface StepInfo {
  index: number
  label: string
  variables: StepVariable[]
}

interface RandomItem {
  label: string
  desc: string
  preview?: string
  generate: () => string
}

const props = defineProps<{
  visible: boolean
  globalVariables?: GlobalVariable[]
  steps: StepInfo[]
  currentStepIndex: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', variableName: string): void
}>()

const searchText = ref('')

// 随机变量列表
const randomItems: RandomItem[] = [
  { label: 'UUID', desc: '通用唯一标识符', generate: () => crypto.randomUUID() },
  { label: '随机整数', desc: '1-1000 整数', generate: () => String(Math.floor(Math.random() * 1000) + 1) },
  { label: '随机小数', desc: '0-100 之间的随机小数', generate: () => (Math.random() * 100).toFixed(2) },
  { label: '随机布尔值', desc: 'true / false', generate: () => Math.random() > 0.5 ? 'true' : 'false' },
  { label: '随机日期', desc: '近 30 天内的日期', generate: () => {
    const d = new Date(Date.now() - Math.floor(Math.random() * 30 * 86400000))
    return d.toISOString().slice(0, 10)
  }},
  { label: '随机时间戳', desc: '毫秒级时间戳', generate: () => String(Date.now() - Math.floor(Math.random() * 1000000)) },
  { label: '随机邮箱', desc: '随机生成的测试邮箱', generate: () => {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    let name = ''
    for (let i = 0; i < 8; i++) name += chars[Math.floor(Math.random() * chars.length)]
    return name + '@test.com'
  }},
  { label: '随机手机号', desc: '11 位手机号', generate: () => {
    const prefixes = ['13', '15', '18', '17']
    const pre = prefixes[Math.floor(Math.random() * prefixes.length)]
    let rest = ''
    for (let i = 0; i < 9; i++) rest += Math.floor(Math.random() * 10)
    return pre + rest
  }},
  { label: '8 位随机串', desc: '字母数字混排', generate: () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let result = ''
    for (let i = 0; i < 8; i++) result += chars[Math.floor(Math.random() * chars.length)]
    return result
  }},
  { label: '当前时间', desc: 'ISO 格式当前时间', generate: () => new Date().toISOString() },
  { label: '中文姓名', desc: '随机中文姓名', generate: () => {
    const surnames = '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛'
    const names = '伟芳娜秀英敏静丽强磊军勇杰涛明超斌华平刚桂英兰菊萍红玲莲琴梅文光海辉飞达强博辉刚峰俊毅'
    const sur = surnames[Math.floor(Math.random() * surnames.length)]
    const given1 = names[Math.floor(Math.random() * names.length)]
    const given2 = names[Math.floor(Math.random() * names.length)]
    return sur + given1 + given2
  }},
]

// 只显示当前步骤之前的步骤
const visibleSteps = computed(() => {
  return props.steps.filter(s => s.index < props.currentStepIndex)
})

const globalVariables = computed(() => props.globalVariables || [])
const stepVariables = computed(() => visibleSteps.value)

const filteredGlobalVariables = computed(() => {
  if (!searchText.value) return globalVariables.value
  const q = searchText.value.toLowerCase()
  return globalVariables.value.filter(v => v.key.toLowerCase().includes(q))
})

const filteredStepVariables = computed(() => {
  const q = searchText.value.toLowerCase()
  if (!q) return stepVariables.value

  const result: StepInfo[] = []
  for (const step of stepVariables.value) {
    const matchedVars = step.variables.filter(v =>
      v.name.toLowerCase().includes(q) ||
      (v.path || '').toLowerCase().includes(q)
    )
    if (matchedVars.length > 0) {
      result.push({ ...step, variables: matchedVars })
    }
  }
  return result
})

const filteredRandomVariables = computed(() => {
  if (!searchText.value) return randomItems
  const q = searchText.value.toLowerCase()
  return randomItems.filter(item =>
    item.label.toLowerCase().includes(q) ||
    item.desc.toLowerCase().includes(q)
  )
})

function selectVariable(name: string) {
  emit('select', `{{${name}}}`)
  close()
}

function selectRandom(item: RandomItem) {
  const value = item.generate()
  emit('select', value)
  close()
}

function close() {
  searchText.value = ''
  emit('close')
}
</script>

<style scoped>
/* ==========================================
 * VariableSelector — 变量选择器面板样式
 * ==========================================
 * 用于在输入框中插入变量的弹出面板
 * 支持环境全局变量、步骤提取变量、随机变量
 * ========================================== */

/* 遮罩层 */
.variable-selector-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-dropdown);
  background: var(--alpha-overlay);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 120px;
}

/* 面板容器 */
.variable-selector-panel {
  width: 380px;
  max-height: 480px;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部：标题 + 关闭按钮 */
.vs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}

.vs-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}

.vs-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--size-icon-md);
  height: 28px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
}
.vs-close:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
.vs-close:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}

/* 搜索框区域 */
.vs-search {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}

/* 变量列表区域（可滚动） */
.vs-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2) 0;
}
.vs-body::-webkit-scrollbar {
  width: 6px;
}
.vs-body::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-full);
}
.vs-body::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* 分区容器 */
.vs-section {
  padding: var(--space-2) 0;
}

/* 分区标题（环境全局变量、步骤提取变量、随机变量） */
.vs-section-title {
  padding: var(--space-1) var(--space-4) var(--space-2);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

/* 步骤分组标题（如 "1. 登录接口"） */
.vs-step-header {
  padding: var(--space-1) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
}

/* 单个变量项 */
.vs-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-smooth);
  border-radius: 0;
}
.vs-item:hover {
  background: var(--surface-hover);
}
.vs-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: -2px;
  background: var(--surface-selected);
}

/* 变量名标签（如 {{token}}） */
.vs-var-name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--primary-600);
  background: var(--color-primary-alpha-08);
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-xs);
  flex-shrink: 0;
}

/* 变量来源描述（如 = $.data.id） */
.vs-var-source {
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  color: var(--text-muted);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 变量值预览 */
.vs-var-preview {
  font-size: var(--text-2xs);
  color: var(--text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
  padding-left: var(--space-2);
}

/* 空状态提示 */
.vs-empty {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
