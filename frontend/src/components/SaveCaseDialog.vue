<template>
  <el-dialog v-model="visible" title="另存为用例" width="480px" :close-on-click-modal="false" @close="handleClose" destroy-on-close>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="auto">
      <el-form-item prop="name">
        <template #label>
          <span>用例名称 <span style="color:var(--error)">*</span></span>
        </template>
        <el-input v-model="form.name" placeholder="输入用例名称" maxlength="100" />
      </el-form-item>
      <el-form-item prop="category_id">
        <template #label>
          <span>分类</span>
        </template>
        <el-select v-model="form.category_id" placeholder="选择分类（可选）" clearable style="width: 100%">
          <el-option
            v-for="cat in props.categories || []"
            :key="cat.id"
            :label="cat.name"
            :value="cat.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item prop="case_type">
        <template #label>
          <span>用例类型 <span style="color:var(--error)">*</span></span>
        </template>
        <el-select v-model="form.case_type" placeholder="选择类型" style="width: 200px">
          <el-option label="正向" value="positive" />
          <el-option label="负向" value="negative" />
          <el-option label="边界值" value="boundary" />
          <el-option label="安全性" value="security" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级">
        <el-radio-group v-model="form.priority">
          <el-radio value="P0" title="阻塞">P0</el-radio>
          <el-radio value="P1" title="严重">P1</el-radio>
          <el-radio value="P2" title="一般">P2</el-radio>
          <el-radio value="P3" title="轻微">P3</el-radio>
        </el-radio-group>
        <div class="priority-tooltip">P0=阻塞 P1=严重 P2=一般 P3=轻微</div>
      </el-form-item>
      <el-form-item label="标签">
        <div class="tag-input-wrapper">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入标签名后回车创建"
            size="default"
            style="width: 100%"
          >
          </el-select>
        </div>
        <p class="form-hint">标签可用于分组和筛选用例（如：冒烟、回归、P0）</p>
      </el-form-item>
      <div class="save-hint">将基于当前已保存的接口定义创建测试用例，包含当前请求参数配置</div>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存用例</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import { msgSuccess, msgError } from '../utils/message'
import { logger } from '../utils/logger'
import type { FormInstance } from 'element-plus'
import { useRequireLogin } from '../composables/useRequireLogin'
import { RoutePaths } from '../router/paths'

const router = useRouter()
const { requireLogin } = useRequireLogin()

const props = defineProps<{
  modelValue: boolean
  projectId: number
  apiId: number
  apiName: string
  requestBody?: Record<string, unknown>
  extractRules?: Record<string, unknown>[]
  requestHeaders?: Array<{ key: string; value: string; enabled?: boolean }>
  requestParams?: Array<{ key: string; value: string; enabled?: boolean }>
  assertions?: Array<Record<string, unknown>>
  categories?: Array<{ id: number; name: string }>
  preScript?: string
  postScript?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [data: unknown]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref<FormInstance | null>(null)
const saving = ref(false)

const form = reactive({
  name: `${props.apiName} 用例`,
  priority: 'P2',
  case_type: 'positive',
  category_id: null as number | null,
  tags: [] as string[],
})


// 当弹窗打开时，用最新的接口名重置用例名称
watch(() => props.modelValue, (val) => {
  if (val) {
    form.name = `${props.apiName} 用例`
  }
})

const rules = {
  name: [
    { required: true, message: '请输入用例名称', trigger: 'blur' },
    { max: 100, message: '用例名称不能超过 100 个字符', trigger: 'blur' },
  ],
  case_type: [
    { required: true, message: '请选择用例类型', trigger: 'change' },
  ],
  category_id: [],
}

async function handleSave() {
  if (!(await requireLogin('保存用例'))) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  // Data integrity check
  if (!props.apiId) {
    msgError('接口ID无效，无法创建用例')
    return
  }

  // Validate assertions format
  if (props.assertions && !Array.isArray(props.assertions)) {
    msgError('断言数据格式错误')
    return
  }

  // Validate extract rules format
  if (props.extractRules && !Array.isArray(props.extractRules)) {
    msgError('变量提取规则格式错误')
    return
  }

  saving.value = true
  try {
    // Serialize request body with error handling
    let bodyStr: string | null = null
    if (props.requestBody) {
      try {
        bodyStr = JSON.stringify(props.requestBody)
      } catch (err) {
        logger.error('[SaveCaseDialog] Failed to serialize request body:', err)
        msgError('请求体序列化失败')
        return
      }
    }

    const res = await request.post(`/projects/${props.projectId}/cases`, {
      name: form.name,
      api_id: props.apiId,
      priority: form.priority,
      case_type: form.case_type,
      category_id: form.category_id,
      tags: Array.isArray(form.tags) ? form.tags.join(',') : (form.tags || ''),
      request_body: bodyStr,
      request_headers: props.requestHeaders || [],
      request_params: props.requestParams || [],
      assertions: props.assertions || [],
      extract_vars: props.extractRules || [],
      pre_script: props.preScript || '',
      post_script: props.postScript || '',
    })
    msgSuccess('用例已创建')
    emit('saved', res.data)
    handleClose()
    // 跳转到用例详情页面
    if (res.data?.id) {
      void router.push(RoutePaths.caseDetail(props.projectId, res.data.id))
    }
  } catch (err: unknown) {
    logger.error('[SaveCaseDialog] save case failed:', err)
    const e = err as { response?: { data?: { message?: string; detail?: string } }; message?: string }
    const errorMsg = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '保存用例失败'
    msgError(errorMsg)
  } finally {
    saving.value = false
  }
}

function handleClose() {
  visible.value = false
}
</script>

<style scoped>
/* ===== 对话框底部按钮区 ===== */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

/* ===== 优先级提示文本 ===== */
.priority-tooltip {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

/* ===== 保存提示框 — 品牌化渐变背景 ===== */
.save-hint {
  font-size: var(--text-sm);
  color: var(--primary-600);
  background: var(--grad-primary-subtle);
  padding: var(--space-2-5) var(--space-3-5);
  border-radius: var(--radius-md);
  margin-top: var(--space-2);
  border: 1px solid var(--color-primary-alpha-10);
  line-height: var(--leading-normal);
}

/* ===== 表单提示文本 ===== */
.form-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

/* ===== 优先级单选框优化 ===== */
:deep(.el-radio) {
  margin-right: var(--space-2);
  font-weight: var(--weight-semibold);
}
:deep(.el-radio__label) {
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
}
:deep(.el-radio__input.is-checked .el-radio__label) {
  color: var(--primary-600);
}
:deep(.el-radio-group) {
  display: flex;
  gap: var(--space-1);
}

/* ===== 表单标签样式增强 ===== */
:deep(.el-form-item__label) {
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}

/* ===== 必填标记样式 ===== */
:deep(.el-form-item.is-required:not(.is-no-asterisk) > .el-form-item__label-wrap > .el-form-item__label::before) {
  color: var(--error);
}

/* ===== 暗色模式适配 ===== */
html.dark .save-hint {
  background: var(--grad-primary-subtle);
  border-color: var(--color-primary-alpha-12);
  color: var(--primary-400);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  :deep(.el-dialog),
  :deep(.el-input__wrapper),
  :deep(.el-button),
  :deep(.el-radio__input),
  :deep(.el-select__wrapper) {
    transition-duration: 0.01ms !important;
  }
}
</style>
