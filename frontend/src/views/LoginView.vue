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
</style>

<style src="./LoginView.css"></style>
