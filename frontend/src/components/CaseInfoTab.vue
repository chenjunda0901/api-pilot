<template>
  <el-form :model="caseData" label-width="70" size="small">
    <el-form-item label="用例名称">
      <el-input v-model="caseData.name" placeholder="输入用例名称" />
    </el-form-item>
    <el-form-item label="用例类型">
      <el-select v-model="caseData.case_type" style="width:120px">
        <el-option label="正向" value="positive" />
        <el-option label="负向" value="negative" />
        <el-option label="边界值" value="boundary" />
        <el-option label="安全性" value="security" />
        <el-option label="其他" value="other" />
      </el-select>
    </el-form-item>
    <el-form-item label="优先级">
      <el-select v-model="caseData.priority" style="width:120px">
        <el-option label="P0 (紧急)" value="P0" />
        <el-option label="P1 (重要)" value="P1" />
        <el-option label="P2 (常规)" value="P2" />
        <el-option label="P3 (低优)" value="P3" />
      </el-select>
    </el-form-item>
    <el-form-item label="状态">
      <el-switch v-model="caseStatus" active-text="启用" inactive-text="禁用" />
    </el-form-item>
    <el-form-item label="描述">
      <el-input v-model="caseData.description" type="textarea" :rows="3" placeholder="用例描述" />
    </el-form-item>
    <el-form-item label="标签">
      <el-input v-model="caseData.tags" placeholder="逗号分隔" />
    </el-form-item>
  </el-form>
</template>
<script setup lang="ts">
import { computed } from 'vue'
interface CaseFormData {
  name: string
  case_type: string
  priority: string
  status: string
  description: string
  tags: string
}

const props = defineProps<{ modelValue: CaseFormData }>()
const emit = defineEmits<{ 'update:modelValue': [value: CaseFormData] }>()
const caseData = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const caseStatus = computed({
  get: () => props.modelValue.status !== 'disabled' && props.modelValue.status !== undefined,
  set: (v) => { emit('update:modelValue', { ...props.modelValue, status: v ? 'active' : 'disabled' }) },
})
</script>
