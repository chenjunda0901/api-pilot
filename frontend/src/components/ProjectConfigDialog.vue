<template>
  <el-dialog v-model="visible" title="项目配置" width="480px" :close-on-click-modal="false" @close="handleClose" destroy-on-close>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="auto">
      <el-form-item prop="name" label="项目名称">
        <el-input v-model="form.name" placeholder="输入项目名称" maxlength="50" />
      </el-form-item>
      <el-form-item prop="description" label="项目描述">
        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="输入项目描述（可选）" maxlength="200" />
      </el-form-item>
      <el-form-item label="项目可见性">
        <el-switch
          v-model="form.is_public"
          active-text="公开"
          inactive-text="私有"
          :active-value="true"
          :inactive-value="false"
        />
        <p class="config-hint">公开项目对所有用户可见，私有项目仅创建者可见</p>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import request from '../api/request'
import { msgSuccess, msgError } from '../utils/message'
import { logger } from '../utils/logger'
import type { FormInstance } from 'element-plus'
import { useRequireLogin } from '../composables/useRequireLogin'

const { requireLogin } = useRequireLogin()

const props = defineProps<{
  modelValue: boolean
  projectId: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref<FormInstance | null>(null)
const saving = ref(false)

const form = reactive({
  name: '',
  description: '',
  is_public: false,
})

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { max: 50, message: '项目名称不超过 50 字', trigger: 'blur' },
  ],
  description: [{ max: 200, message: '项目描述不超过 200 字', trigger: 'blur' }],
}

watch(() => props.modelValue, async (v) => {
  if (v) {
    try {
      const res = await request.get(`/projects/${props.projectId}`)
      form.name = res.data.name || ''
      form.description = res.data.description || ''
      form.is_public = res.data.is_public ?? false
    } catch (err) {
      logger.error('[ProjectConfigDialog] load project config failed:', err)
      msgError('加载项目配置失败')
      // handled by interceptor
    }
  }
})

async function handleSave() {
  if (!(await requireLogin('保存项目配置'))) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await request.put(`/projects/${props.projectId}`, {
      name: form.name,
      description: form.description,
      is_public: form.is_public,
    })
    msgSuccess('项目配置已更新')
    emit('saved')
    handleClose()
  } catch (err) {
    logger.error('[ProjectConfigDialog] save project config failed:', err)
    msgError('保存项目配置失败')
    // error handled by interceptor
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

/* ===== 配置提示文本 ===== */
.config-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: var(--space-1) 0 0 0;
  line-height: var(--leading-normal);
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

/* ===== 开关组件间距优化 ===== */
:deep(.el-form-item) {
  margin-bottom: var(--space-5);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  :deep(.el-dialog),
  :deep(.el-input__wrapper),
  :deep(.el-button),
  :deep(.el-switch__core),
  :deep(.el-textarea__inner) {
    transition-duration: 0.01ms !important;
  }
}
</style>
