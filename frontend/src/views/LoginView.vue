<template>
  <div class="login-page">
    <div class="login-card" role="main" :aria-label="$t('auth.loginForm')">
      <div class="login-left">
        <div class="brand-mark">AP</div>
        <h1 class="brand-name">API Pilot</h1>
        <p class="brand-desc">{{ $t('auth.platformDesc') }}</p>
        <div class="brand-divider"></div>
        <p class="brand-tagline">{{ $t('auth.tagline') }}</p>
        <div class="brand-features">
          <div class="feature">{{ $t('auth.featureApi') }}</div>
          <div class="feature">{{ $t('auth.featureTest') }}</div>
          <div class="feature">{{ $t('auth.featureData') }}</div>
        </div>
      </div>
      <div class="login-right">
        <div class="form-wrapper">
        <div class="form-head">
          <span class="form-head-title" id="login-title">{{ $t('auth.login') }}</span>
        </div>
        <el-form :model="form" :rules="rules" ref="formRef" @keyup.enter="handleLogin" class="login-form" @submit.prevent aria-labelledby="login-title">
          <el-form-item prop="username">
            <label for="login-username" class="sr-only">{{ $t('auth.username') }}</label>
            <el-input id="login-username" v-model="form.username" :placeholder="$t('auth.usernamePlaceholder')" :aria-label="$t('auth.username')" autocomplete="username" />
          </el-form-item>
          <el-form-item prop="password">
            <label for="login-password" class="sr-only">{{ $t('auth.password') }}</label>
            <el-input id="login-password" v-model="form.password" type="password" :placeholder="$t('auth.passwordPlaceholder')" show-password :aria-label="$t('auth.password')" />
          </el-form-item>
          <el-checkbox v-model="form.rememberMe" class="remember-me">
            {{ $t('auth.rememberUsername') }}
          </el-checkbox>
          <el-form-item>
            <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin" :aria-label="loading ? $t('auth.loggingIn') : $t('auth.loginButton')">
              {{ loading ? $t('auth.loggingIn') : $t('auth.login') }}
            </el-button>
          </el-form-item>
        </el-form>
        <p class="demo-hint">
          {{ $t('auth.noAccount') }}<router-link to="/register" class="switch-link">{{ $t('auth.registerNow') }}</router-link>
        </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { msgSuccess, msgError } from '../utils/message'
import { MSG } from '../constants/messages'
import { useUserStore } from '../stores/userStore'


const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '', rememberMe: false })

// 记住用户名：仅在用户主动勾选"记住用户名"时写入 localStorage
const REMEMBER_KEY = 'remembered_username'
try {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.username = saved
    form.rememberMe = true
  }
} catch { /* localStorage 不可用 */ }

// 取消勾选时立即清除已保存的用户名
watch(() => form.rememberMe, (val) => {
  if (!val) {
    try { localStorage.removeItem(REMEMBER_KEY) } catch { /* ignore */ }
  }
})

const usernameValidator = (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
  if (!value || !value.trim()) {
    callback(t('auth.usernameRequired'))
    return
  }
  callback()
}

const passwordValidator = (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
  if (!value) {
    callback(t('auth.passwordRequired'))
    return
  }
  if (value.length < 6) {
    callback(t('auth.passwordMinLength'))
    return
  }
  callback()
}

const rules = {
  username: [{ required: true, validator: usernameValidator, trigger: ['blur', 'change'] }],
  password: [{ required: true, validator: passwordValidator, trigger: ['blur', 'change'] }],
}

async function handleLogin() {
  if (loading.value) return

  if (!formRef.value) {
    msgError(t('auth.formInitError'))
    return
  }
  let valid = true
  try {
    await formRef.value.validate()
  } catch {
    valid = false
  }
  if (!valid) return

  loading.value = true

  const controller = new AbortController()
  const SUBMIT_TIMEOUT = 30000
  let isCompleted = false
  const timer = setTimeout(() => {
    // 仅在请求尚未完成时才中止，避免丢弃已成功返回的响应
    if (loading.value && !isCompleted) {
      loading.value = false
      controller.abort()
      msgError(t('common.timeout'))
    }
  }, SUBMIT_TIMEOUT)

  try {
    // 等待登录完成，确保 token 已保存
    await userStore.login(form.username, form.password, controller.signal)
    isCompleted = true
    msgSuccess(MSG.LOGIN_SUCCESS)

    // 从 hintBar 新窗口打开的登录场景：登录成功后关闭窗口
    // 原页面通过 localStorage 轮询感知登录状态，会自动恢复认证并重试操作
    const from = (route.query.from as string) || ''
    if (from === 'hint') {
      // 登录完成后延迟关闭，确保 token 已写入
      setTimeout(() => {
        try {
          window.close()
        } catch {
          // 浏览器阻止关闭时的降级：通知 opener 窗口
          window.opener?.postMessage({ type: 'LOGIN_SUCCESS' }, window.location.origin)
          void router.push('/dashboard')
        }
      }, 500)
      return
    }

    // 记住密码：根据勾选状态持久化用户名
    try {
      if (form.rememberMe) {
        localStorage.setItem(REMEMBER_KEY, form.username)
      } else {
        localStorage.removeItem(REMEMBER_KEY)
      }
    } catch { /* localStorage 不可用 */ }

    // 优先用 sessionStorage（hintBar 触发时设置），其次用 query.redirect（router guard 触发时设置）
    const sessionRedirect = sessionStorage.getItem('login_redirect')
    const queryRedirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    if (sessionRedirect) sessionStorage.removeItem('login_redirect')
    const target = sessionRedirect || queryRedirect || '/'
    router.push(target).catch(() => {
      // router.push 可能因导航守卫冲突失败，降级为 location 跳转
      window.location.hash = target.startsWith('/') ? target : `/#${target}`
    })
  } catch (e: unknown) {
    // 超时/主动取消的请求不显示错误
    if ((e as Error)?.name === 'AbortError') return
    const error = e as { response?: { data?: { code?: string; message?: string; detail?: string } } }
    const errorCode = error.response?.data?.code
    // 优先使用 message，其次 detail（FastAPI 风格），最后是通用错误信息
    const errorMsg = error.response?.data?.message || error.response?.data?.detail
    
    // 根据错误码显示不同的提示
    if (errorCode === 'AUTH_011') {
      // 账号被锁定
      msgError(errorMsg || t('auth.accountLocked'))
    } else if (errorCode === 'AUTH_003') {
      // 密码错误或账号不存在
      msgError(errorMsg || t('auth.invalidCredentials'))
    } else if (errorMsg) {
      // 后端返回了具体的错误信息，直接显示
      msgError(errorMsg)
    } else {
      // 完全无法获取错误信息时的兜底
      msgError(t('auth.loginFailed'))
    }
    // 登录失败后自动聚焦到用户名输入框
    nextTick(() => {
      formRef.value?.$el?.querySelector('.el-form-item.is-error input')?.focus()
        ?? document.getElementById('login-username')?.focus()
    }).catch(() => { /* ignore focus failure */ })
  } finally {
    clearTimeout(timer)
    loading.value = false
  }
}


</script>

<style scoped>
/* ===== 登录页 — 完整样式（v11 Soft Sage 设计系统） ===== */

.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-6);
  background: linear-gradient(135deg, var(--color-primary-50) 0%, var(--color-primary-100) 50%, var(--surface-bg) 100%);
  overflow: hidden;
}

/* 主卡片 */
.login-card {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  max-width: 820px;
  min-height: 480px;
  background: var(--surface-card-alpha-82);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: var(--transition-base);
}
/* 卡片顶部品牌色渐变装饰条 */
.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--grad-primary);
  z-index: 2;
  border-radius: var(--radius-2xl) var(--radius-2xl) 0 0;
}

/* 左侧品牌区 */
.login-left {
  flex: 0 0 320px;
  padding: var(--space-10) var(--space-7);
  background: linear-gradient(160deg, var(--primary-600) 0%, var(--primary-500) 50%, var(--primary-400) 100%);
  background-size: 200% 200%;
  animation: brand-hue 30s infinite alternate var(--ease-smooth, ease);
  color: var(--text-inverse);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-mark {
  width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-xl); font-weight: var(--weight-bold);
  background: var(--color-white-alpha-20);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.brand-name {
  font-size: var(--text-2xl); font-weight: var(--weight-bold);
  line-height: 1.2; margin: 0 0 var(--space-2);
}

.brand-desc {
  font-size: var(--text-sm); color: var(--text-inverse);
  line-height: 1.6; margin: 0 0 var(--space-5);
}

.brand-divider {
  width: 40px; height: 2px;
  background: var(--color-white-alpha-30);
  border-radius: var(--radius-2xs); margin-bottom: var(--space-5);
}

.brand-tagline {
  font-size: var(--text-xs); color: var(--text-inverse);
  line-height: 1.6; margin: 0 0 var(--space-5);
  letter-spacing: 0.04em;
}

.brand-features { display: flex; flex-direction: column; gap: var(--space-2); }
.brand-features .feature {
  font-size: var(--text-xs); color: var(--color-white-alpha-90);
  padding-left: var(--space-3);
  position: relative;
}
.brand-features .feature::before {
  content: '';
  position: absolute; left: 0; top: 6px;
  width: 5px; height: 5px;
  background: var(--color-white-alpha-60);
  border-radius: 50%;
}

/* 右侧表单区 */
.login-right {
  flex: 1;
  padding: var(--space-10) var(--space-9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

/* 表单包裹容器 — 居中布局，最大宽度 400px */
.form-wrapper {
  width: 100%;
  max-width: 400px;
}

.form-head { margin-bottom: var(--space-6); }
.form-head-title {
  font-size: var(--text-xl); font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 表单 */
.login-form { width: 100%; }
.login-form :deep(.el-form-item) { margin-bottom: var(--space-4); }
/* 输入框统一高度 44px，内边距使用 tokens */
.login-form :deep(.el-input__wrapper) {
  height: var(--height-input-lg);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-default) inset;
  transition: box-shadow var(--duration-base) var(--ease-smooth);
}
.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--primary-300) inset;
}
.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px var(--primary-500),
    0 0 0 3px var(--color-primary-alpha-12),
    0 0 8px var(--color-primary-alpha-10) !important;
}

.remember-me {
  margin-bottom: var(--space-5);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* 登录按钮 */
.login-btn {
  width: 100%; height: 44px;
  font-size: var(--text-sm); font-weight: var(--weight-semibold);
  border-radius: var(--radius-md);
  background: var(--grad-primary);
  border: none;
  letter-spacing: 0.03em;
  transition: background-color var(--duration-base) var(--ease-smooth), opacity var(--duration-base) var(--ease-smooth);
}
.login-btn:hover {
  background: var(--grad-primary-hover);
}
.login-btn:active { opacity: 0.9; }
.login-btn.is-loading,
.login-btn[loading] {
  opacity: 0.85;
}

/* 链接提示 */
.demo-hint {
  text-align: center; margin-top: var(--space-4);
  font-size: var(--text-sm); color: var(--text-muted);
}
.switch-link {
  color: var(--primary-500);
  font-weight: var(--weight-medium);
  text-decoration: none;
  transition: color var(--duration-fast);
}
.switch-link:hover { color: var(--primary-700); text-decoration: underline; }

/* 无障碍：仅屏幕阅读器可见 */
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0, 0, 0, 0);
  white-space: nowrap; border: 0;
}

/* 响应式：移动端单列布局 */
@media (max-width: 640px) {
  .login-page { padding: var(--space-4); align-items: flex-start; padding-top: var(--space-12); }
  .login-card { flex-direction: column; max-width: 420px; min-height: auto; }
  .login-left {
    flex: none; padding: var(--space-7) var(--space-6) var(--space-5);
  }
  .login-right { padding: var(--space-6) var(--space-6) var(--space-8); }
  .form-wrapper { max-width: 100%; }
}

/* ===== 表单错误信息 ===== */
.login-form :deep(.el-form-item__error) {
  color: var(--error-text);
  font-size: var(--text-xs);
  padding-top: var(--space-1);
  position: static;
  line-height: 1.4;
}

/* ===== 暗色模式 ===== */
html.dark .login-page {
  background:
    radial-gradient(ellipse at 30% 20%, var(--color-primary-alpha-06) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 80%, var(--color-primary-alpha-05) 0%, transparent 50%),
    linear-gradient(160deg, var(--surface-bg) 0%, var(--surface-bg) 50%, var(--surface-nested) 100%);
}
html.dark .login-card {
  background: var(--surface-card);
  border: 1px solid var(--color-white-alpha-08);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
html.dark .login-card::before {
  opacity: 0.6;
}
html.dark .form-head-title {
  color: var(--text-primary);
}
html.dark .remember-me {
  color: var(--text-secondary);
}
html.dark .remember-me :deep(.el-checkbox__label) {
  color: var(--text-secondary);
}
html.dark .demo-hint {
  color: var(--text-muted);
}
html.dark .switch-link {
  color: var(--primary-400);
}
html.dark .switch-link:hover {
  color: var(--primary-300);
}
html.dark .login-form :deep(.el-input__wrapper) {
  background: var(--surface-input);
}
html.dark .login-form :deep(.el-input__inner) {
  color: var(--text-primary);
}
html.dark .login-form :deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
}

/* 品牌区渐变色相偏移动画 */
@keyframes brand-hue {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
</style>
