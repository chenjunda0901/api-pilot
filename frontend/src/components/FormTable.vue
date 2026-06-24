<template>
  <div class="form-table">
    <el-table
      :data="modelValue"
      size="small"
      max-height="400"
      style="width: 100%"
      aria-label="表单参数列表"
    >
      <el-table-column label="启用" width="50">
        <template #default="{ row }">
          <el-checkbox v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="参数名" min-width="140">
        <template #default="{ row }">
          <el-input v-model="row.key" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="参数值" min-width="200">
        <template #default="{ row }">
          <div v-if="row.type === 'file'" class="file-value-row">
            <VarAwareInput
              v-model="row.value"
              size="small"
              placeholder="文件路径（服务器路径）"
              aria-label="参数值"
            />
            <el-upload
              :show-file-list="false"
              :before-upload="(f: File) => handleFileSelect(f, row)"
              style="flex-shrink: 0"
            >
              <el-button size="small" :icon="UploadIcon">浏览</el-button>
            </el-upload>
          </div>
          <VarAwareInput
            v-else
            v-model="row.value"
            size="small"
            placeholder="参数值"
            aria-label="参数值"
          />
        </template>
      </el-table-column>
      <el-table-column label="类型" :width="bodyType === 'x-www-form-urlencoded' ? 80 : 100">
        <template #default="{ row }">
          <el-select v-model="row.type" size="small" v-if="bodyType === 'form-data'">
            <el-option label="Text" value="text" />
            <el-option label="File" value="file" />
          </el-select>
          <span v-else class="type-label">text</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60">
        <template #default="{ $index }">
          <el-button text size="small" @click="remove($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <button class="add-row" @click="addRow">+ 添加参数</button>
  </div>
</template>
<script setup lang="ts">
import { onMounted, watch, h } from "vue"
import { Upload } from "lucide-vue-next"
import VarAwareInput from "./common/VarAwareInput.vue"

const UploadIcon = h(Upload, { size: 14 })

interface FormRow {
  key: string
  value: string
  type: string
  enabled: boolean
}

const modelValue = defineModel<FormRow[]>({ default: () => [] })
const props = defineProps<{ bodyType?: string }>()

function addRow() {
  const defaultType = props.bodyType === 'form-data' ? 'text' : 'text'
  modelValue.value.push({ key: "", value: "", type: defaultType, enabled: true })
}

function ensureDefaultRow() {
  if (modelValue.value.length === 0) {
    const defaultType = props.bodyType === 'form-data' ? 'text' : 'text'
    modelValue.value.push({ key: "", value: "", type: defaultType, enabled: false })
  }
}

onMounted(ensureDefaultRow)
watch(
  () => modelValue.value,
  (val) => {
    if (Array.isArray(val) && val.length === 0) {
      ensureDefaultRow()
    }
  }
)

function handleFileSelect(file: File, row: FormRow) {
  // 浏览器环境下只能获取文件名，服务器执行时需要绝对路径
  row.value = file.name
  return false
}

function remove(index: number) {
  modelValue.value.splice(index, 1)
}
</script>
<style scoped>
/* 表单表格 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角均使用 CSS 变量，确保暗色模式自动适配
 */
.form-table {
  padding-bottom: var(--spacing-sm);
}

/* 添加参数按钮：虚线边框 + 悬停主色 */
.add-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  width: 100%;
  padding: var(--spacing-xs) var(--spacing-sm);
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  background: transparent;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-smooth),
              border-color var(--duration-fast) var(--ease-smooth),
              background-color var(--duration-fast) var(--ease-smooth);
  font-family: inherit;
}
.add-row:hover {
  color: var(--primary-500);
  border-color: var(--primary-500);
  background: var(--color-primary-alpha-06);
}

/* 焦点态：主色环 */
.add-row:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

/* 激活态：更深主色背景 */
.add-row:active {
  background: var(--color-primary-alpha-12);
}

/* 文件值行：输入框 + 浏览按钮 */
.file-value-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

/* 类型标签 */
.type-label {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  padding: 0 var(--spacing-sm);
}
</style>
