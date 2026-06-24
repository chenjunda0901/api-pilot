<template>
  <el-dialog v-model="visible" title="个人中心" width="540px" :close-on-click-modal="false" append-to-body class="profile-dialog" @close="handleClose" @opened="onOpened">
    <el-tabs v-model="activeTab">
      <!-- Tab 1: 基本信息 -->
      <el-tab-pane label="基本信息" name="profile">
        <div class="profile-section">
          <div class="profile-avatar-row">
            <div class="profile-avatar" :style="{ background: avatarBg }">{{ initials }}</div>
            <div class="profile-avatar-info">
              <div class="profile-username">{{ user?.username }}</div>
              <div class="profile-role-badge">{{ roleText }}</div>
            </div>
          </div>
          <el-form :model="profileForm" label-position="top" class="profile-form">
            <el-form-item label="用户 ID">
              <div class="user-id-row">
                <el-input :model-value="String(user?.id ?? '-')" disabled />
                <el-button size="small" text @click="copyUserId">复制</el-button>
              </div>
            </el-form-item>
            <el-form-item label="用户名">
              <el-input :model-value="user?.username" disabled />
            </el-form-item>
            <el-form-item label="昵称">
              <el-input v-model="profileForm.nickname" placeholder="输入昵称" maxlength="50" show-word-limit />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" placeholder="输入邮箱（选填）" maxlength="100">
                <template #suffix>
                  <span v-if="profileForm.email && !emailValid" class="field-error-hint">格式不正确</span>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="角色">
              <el-input :model-value="roleText" disabled />
            </el-form-item>
            <el-form-item label="注册时间">
              <el-input :model-value="formatDisplayDate(user?.created_at)" disabled />
            </el-form-item>
          </el-form>
        </div>
        <div class="tab-footer">
          <el-button :loading="savingProfile" :disabled="!profileChanged || !emailValid" type="primary" @click="saveProfile">保存修改</el-button>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 账号安全 -->
      <el-tab-pane label="账号安全" name="security">
        <div class="security-section">
          <div class="security-card">
            <h4 class="security-card-title">修改密码</h4>
            <el-form :model="pwdForm" label-position="top" class="pwd-form">
              <el-form-item label="当前密码">
                <el-input v-model="pwdForm.oldPassword" type="password" placeholder="请输入当前密码" show-password />
              </el-form-item>
              <el-form-item label="新密码">
                <el-input v-model="pwdForm.newPassword" type="password" placeholder="至少 6 个字符" show-password />
                <div v-if="pwdForm.newPassword" class="password-strength">
                  <div class="strength-bar">
                    <div class="strength-segment" :class="strengthLevel >= 1 ? 'active weak' : ''"></div>
                    <div class="strength-segment" :class="strengthLevel >= 2 ? 'active medium' : ''"></div>
                    <div class="strength-segment" :class="strengthLevel >= 3 ? 'active strong' : ''"></div>
                  </div>
                  <span class="strength-text" :class="strengthClass">{{ strengthLabel }}</span>
                </div>
              </el-form-item>
              <el-form-item label="确认新密码">
                <el-input v-model="pwdForm.confirmPassword" type="password" placeholder="再次输入新密码" show-password />
                <p v-if="pwdForm.confirmPassword && pwdForm.newPassword !== pwdForm.confirmPassword" class="field-error-hint">两次输入的密码不一致</p>
              </el-form-item>
            </el-form>
            <el-button type="primary" :loading="changingPwd" :disabled="!pwdFormValid" @click="changePassword" style="margin-top: var(--space-2);">确认修改</el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useUserStore } from '../stores/userStore'
import request from '../api/request'
import { msgSuccess, msgError } from '../utils/message'
import { logger } from '../utils/logger'
import { ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const visible = defineModel<boolean>('visible')
const activeTab = ref('profile')
const savingProfile = ref(false)
const changingPwd = ref(false)

const user = computed(() => userStore.user)

const avatarBg = computed(() => {
  const name = user.value?.username || 'U'
  const colors = [
    'var(--avatar-palette-1)', 'var(--avatar-palette-2)', 'var(--avatar-palette-3)',
    'var(--avatar-palette-4)', 'var(--avatar-palette-5)', 'var(--avatar-palette-6)',
    'var(--avatar-palette-7)', 'var(--avatar-palette-8)', 'var(--avatar-palette-9)',
    'var(--avatar-palette-10)',
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
})

const initials = computed(() => {
  const name = user.value?.nickname || user.value?.username || 'U'
  return name.slice(0, 1)
})

const roleText = computed(() => {
  const map: Record<string, string> = { admin: '系统管理员', member: '普通成员', owner: '所有者', editor: '编辑者', viewer: '查看者' }
  return map[user.value?.role ?? ''] || user.value?.role || '-'
})

function formatDisplayDate(dateStr?: string): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${day} ${h}:${min}`
  } catch {
    return dateStr
  }
}

// ---- 基本信息 Tab ----
const profileForm = reactive({ nickname: '', email: '' })
const _origProfile = reactive({ nickname: '', email: '' })

watch(() => visible.value, (v) => {
  if (v) {
    activeTab.value = 'profile'
    profileForm.nickname = user.value?.nickname || ''
    profileForm.email = user.value?.email || ''
    _origProfile.nickname = profileForm.nickname
    _origProfile.email = profileForm.email
    // 重置密码表单
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
  }
})

function onOpened() {
  // 确保对话框打开后内容可见（修复 destroy-on-close + append-to-body 导致内容为空的问题）
  activeTab.value = 'profile'
}

const profileChanged = computed(() =>
  profileForm.nickname !== _origProfile.nickname || profileForm.email !== _origProfile.email
)

const emailValid = computed(() => {
  if (!profileForm.email) return true  // 选填
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profileForm.email)
})

async function saveProfile() {
  if (!emailValid.value) return
  savingProfile.value = true
  try {
    await request.put('/auth/me', { nickname: profileForm.nickname, email: profileForm.email })
    msgSuccess('已保存')
    await userStore.fetchUserInfo()
    _origProfile.nickname = profileForm.nickname
    _origProfile.email = profileForm.email
  } catch (err) {
    logger.error('[ProfileCenterDialog] save profile failed:', err)
    msgError('保存个人信息失败')
    // handled by interceptor
  } finally {
    savingProfile.value = false
  }
}

function copyUserId() {
  const id = String(user.value?.id ?? '')
  if (!id) return
  navigator.clipboard.writeText(id).then(() => {
    msgSuccess('用户 ID 已复制')
  }).catch(() => {
    msgError('复制失败')
  })
}

// ---- 账号安全 Tab ----
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

const strengthLevel = computed(() => {
  const pw = pwdForm.newPassword
  if (!pw) return 0
  // 简化规则：仅检查长度 >= 6
  return pw.length >= 6 ? 1 : 0
})

const strengthLabel = computed((): string => ['', '合格'][strengthLevel.value] ?? '')
const strengthClass = computed((): string => ['', 'ok'][strengthLevel.value] ?? '')

const pwdFormValid = computed(() =>
  pwdForm.oldPassword.length > 0 &&
  pwdForm.newPassword.length >= 6 &&
  pwdForm.newPassword === pwdForm.confirmPassword
)

async function changePassword() {
  changingPwd.value = true
  try {
    await request.put('/auth/password', {
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword,
    })
    msgSuccess($t('common.passwordChanged') || '密码修改成功')
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
  } catch (err) {
    // handled by interceptor
  } finally {
    changingPwd.value = false
  }
}

// ---- 关闭确认 ----
async function handleClose() {
  if (profileChanged.value) {
    try {
      await ElMessageBox.confirm($t('common.unsavedChangesWarning') || '您有未保存的更改，确定要离开吗？', '提示', {
        confirmButtonText: $t('common.discardChanges') || '放弃更改',
        cancelButtonText: $t('common.continueEditing') || '继续编辑',
        type: 'warning',
      })
      visible.value = false
    } catch {
      /* user cancelled */
    }
  } else {
    visible.value = false
  }
}
</script>

<style scoped>
/* ===== 头像行 — 品牌化升级 =====
 * 策略：使用 design tokens 统一颜色/间距/圆角/阴影
 * 暗色模式通过 html.dark 选择器自动适配
 */
.profile-avatar-row {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  margin-bottom: var(--space-6);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-nested);
  border-radius: var(--radius-xl) var(--radius-xl) var(--radius-sm) var(--radius-sm);
  position: relative;
  overflow: hidden;
}
.profile-avatar-row::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--grad-primary);
  opacity: 0.6;
}

/* 头像 — 带边框环 */
.profile-avatar {
  font-family: var(--font-sans);
  width: var(--width-avatar, 64px);
  height: var(--width-avatar, 64px);
  border-radius: var(--radius-full);
  color: var(--text-inverse, #fdfdff);
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  transition: transform var(--duration-base) var(--ease-spring),
    box-shadow var(--duration-base) var(--ease-out);
  box-shadow: var(--shadow-md);
}
.profile-avatar:hover {
  transform: scale(1.05) translateY(-1px);
  box-shadow: var(--shadow-lg);
}

/* 头像信息区 */
.profile-avatar-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}
.profile-username {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  letter-spacing: var(--tracking-tight);
}

/* 角色徽章 — 精致药丸 */
.profile-role-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--spacing-xs) var(--space-3);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-full);
  width: fit-content;
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border: 1px solid var(--color-primary-alpha-12);
  transition: background var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth);
}
.profile-role-badge:hover {
  background: var(--color-primary-alpha-16);
}

/* ===== 表单区域 — 统一视觉层次 ===== */
.profile-section {
  padding: var(--space-1) 0;
}
.user-id-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
}
.user-id-row .el-input {
  flex: 1;
}
.profile-form,
.pwd-form {
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* 表单项增强 — 与 SettingsView 的 .form-row 风格对齐 */
.profile-form :deep(.el-form-item),
.pwd-form :deep(.el-form-item) {
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-nested);
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  transition: border-color var(--duration-fast) var(--ease-smooth),
    background-color var(--duration-fast) var(--ease-smooth);
}
.profile-form :deep(.el-form-item:hover),
.pwd-form :deep(.el-form-item:hover) {
  border-color: var(--border-default);
  background: var(--surface-card);
}

/* 表单标签统一样式 */
.profile-form :deep(.el-form-item__label),
.pwd-form :deep(.el-form-item__label) {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  padding-bottom: var(--space-2);
}

/* 输入框增强 */
.profile-form :deep(.el-input__wrapper),
.pwd-form :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  transition: box-shadow var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth);
}
.profile-form :deep(.el-input__wrapper:focus-within),
.pwd-form :deep(.el-input__wrapper:focus-within) {
  box-shadow: var(--shadow-focus);
}

/* Tab 底部保存栏 */
.tab-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  margin-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-nested);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-xl) var(--radius-xl);
  gap: var(--space-3);
}
.tab-footer :deep(.el-button) {
  padding: var(--spacing-sm) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: var(--weight-semibold);
  transition: transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-base) var(--ease-out);
}
.tab-footer :deep(.el-button--primary):hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* ===== 密码强度指示器 — 精致升级 ===== */
.password-strength {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
}
.strength-bar {
  display: flex;
  gap: var(--space-1);
  flex: 1;
}
.strength-segment {
  height: 4px;
  flex: 1;
  border-radius: var(--radius-2xs);
  background: var(--surface-muted);
  transition: background var(--duration-slow) var(--ease-smooth),
    transform var(--duration-slow) var(--ease-out);
}
.strength-segment.active.weak { background: var(--error); }
.strength-segment.active.medium { background: var(--warning); }
.strength-segment.active.strong { background: var(--success); }

.strength-text {
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  min-width: var(--size-icon-md, 28px);
  text-align: center;
  letter-spacing: var(--tracking-wide);
}
.strength-text.weak { color: var(--error); }
.strength-text.medium { color: var(--warning); }
.strength-text.strong { color: var(--success); }

/* ===== 安全卡片 — 视觉强化 ===== */
.security-card {
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  position: relative;
  overflow: hidden;
}
.security-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, var(--warning), var(--error));
  opacity: 0.7;
  border-radius: var(--radius-full) 0 0 var(--radius-full);
}
.security-card-title {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.security-card-title::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--warning);
}

/* 字段错误提示 */
.field-error-hint {
  font-size: var(--text-2xs);
  color: var(--error);
  font-weight: var(--weight-medium);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  animation: field-shake 0.35s var(--ease-smooth);
}

@keyframes field-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px); }
  75% { transform: translateX(3px); }
}

/* ===== el-tabs 微调 — 品牌一致性 ===== */
:deep(.el-tabs__header) {
  margin-bottom: var(--space-5);
}
:deep(.el-tabs__nav-wrap::after) {
  background: var(--border-subtle);
}
:deep(.el-tabs__item) {
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  padding: 0 var(--space-5);
  height: var(--height-tabs);
  line-height: var(--height-tabs);
  transition: color var(--duration-fast) var(--ease-smooth);
}
:deep(.el-tabs__item.is-active) {
  color: var(--primary-600);
  font-weight: var(--weight-bold);
}
:deep(.el-tabs__active-bar) {
  background: var(--primary-500);
  border-radius: var(--radius-2xs) var(--radius-2xs) 0 0;
  height: 3px;
}

/* ===== 暗色模式全面适配 ===== */
html.dark .profile-avatar-row {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}
html.dark .profile-avatar-row::before {
  opacity: 0.4;
}
html.dark .profile-avatar {
  box-shadow: var(--shadow-md);
}
html.dark .profile-avatar:hover {
  box-shadow: var(--shadow-lg);
}
html.dark .profile-role-badge {
  background: var(--color-primary-alpha-12);
  color: var(--primary-400);
  border-color: var(--color-primary-alpha-18);
}
html.dark .profile-role-badge:hover {
  background: var(--color-primary-alpha-16);
  border-color: var(--color-primary-alpha-24);
}
html.dark .profile-form :deep(.el-form-item),
html.dark .pwd-form :deep(.el-form-item) {
  background: var(--color-neutral-alpha-03);
  border-color: transparent;
}
html.dark .profile-form :deep(.el-form-item:hover),
html.dark .pwd-form :deep(.el-form-item:hover) {
  border-color: var(--border-default);
  background: var(--color-neutral-alpha-06);
}
html.dark .tab-footer {
  background: var(--color-neutral-alpha-06);
  border-color: var(--border-subtle);
}
html.dark .password-strength {
  background: var(--color-neutral-alpha-06);
}
html.dark .strength-segment {
  background: var(--color-neutral-alpha-08);
}
html.dark .security-card {
  background: var(--color-neutral-alpha-06);
  border-color: var(--border-subtle);
}
html.dark .security-card::before {
  opacity: 0.5;
}

/* 确保个人中心弹窗始终在最上层 */
:deep(.profile-dialog) {
  z-index: var(--z-modal);
}
</style>
