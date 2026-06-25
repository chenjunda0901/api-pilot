<template>
  <div class="register-page" :class="{ 'mobile-keyboard-open': isKeyboardVisible }">
    <div class="register-orb register-orb-1"></div>
    <div class="register-orb register-orb-2"></div>
    <div class="register-card" role="main" :aria-label="$t('auth.registerForm')">
      <div class="register-left">
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
      <div class="register-right">
        <div class="form-wrapper">
        <div class="form-head">
          <span class="form-head-title" id="register-title">{{ $t('auth.createAccount') }}</span>
        </div>
          :model="form"
          :rules="rules"
          ref="formRef"
          @keyup.enter="handleRegister"
          @submit.prevent
          class="register-form"
          aria-labelledby="register-title"
        >
          <el-form-item :label="$t('auth.username')" prop="username">
            <label for="reg-username" class="sr-only">{{ $t('auth.username') }}</label>
            <el-input id="reg-username" v-model="form.username" :placeholder="$t('auth.usernamePlaceholderReg')" maxlength="20" show-word-limit :aria-label="$t('auth.username')" />
          </el-form-item>
          <el-form-item :label="$t('auth.password')" prop="password">
            <label for="reg-password" class="sr-only">{{ $t('auth.password') }}</label>
            <el-input
              id="reg-password"
              v-model="form.password"
              type="password"
              :placeholder="$t('auth.passwordPlaceholderReg')"
              show-password
              maxlength="128"
              autocomplete="new-password"
              :aria-label="$t('auth.password')"
            />
            <div v-if="form.password" class="password-strength">
              <div class="password-strength-bar">
                <div
                  class="password-strength-bar-fill"
                  :class="['level-' + passwordStrength.level]"
                ></div>
              </div>
              <span class="password-strength-text" :class="['text-level-' + passwordStrength.level]">
                {{ passwordStrength.text }}
              </span>
            </div>
          </el-form-item>
          <el-form-item :label="$t('auth.confirmPassword')" prop="confirmPassword">
            <label for="reg-confirm-password" class="sr-only">{{ $t('auth.confirmPassword') }}</label>
            <el-input
              id="reg-confirm-password"
              v-model="form.confirmPassword"
              type="password"
              :placeholder="$t('auth.confirmPasswordPlaceholder')"
              show-password
              maxlength="128"
              :aria-label="$t('auth.confirmPassword')"
            />
          </el-form-item>
          <el-form-item prop="nickname">
            <template #label>
              <span class="form-item-label">
                {{ $t('auth.nickname') }}
                <span class="optional-tag">{{ $t('auth.optional') }}</span>
              </span>
            </template>
            <label for="reg-nickname" class="sr-only">{{ $t('auth.nickname') }}</label>
            <el-input id="reg-nickname" v-model="form.nickname" :placeholder="$t('auth.nicknamePlaceholder')" maxlength="20" :aria-label="$t('auth.nickname')" />
          </el-form-item>
          <el-form-item prop="email">
            <template #label>
              <span class="form-item-label">
                {{ $t('auth.email') }}
                <span class="optional-tag">{{ $t('auth.optional') }}</span>
              </span>
            </template>
            <label for="reg-email" class="sr-only">{{ $t('auth.email') }}</label>
            <el-input id="reg-email" v-model="form.email" :placeholder="$t('auth.emailPlaceholder')" maxlength="255" autocomplete="email" :aria-label="$t('auth.email')" />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              class="register-btn"
              :loading="loading"
              @click="handleRegister"
              :aria-label="loading ? $t('auth.registering') : $t('auth.register')"
            >
              {{ loading ? $t('auth.registering') : $t('auth.register') }}
            </el-button>
          </el-form-item>
        </el-form>
        <p class="demo-hint">
          {{ $t('auth.hasAccount') }}<router-link to="/login" class="switch-link">{{ $t('auth.goToLogin') }}</router-link>
        </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import { useI18n } from "vue-i18n"
import { ElMessageBox } from "element-plus"
import { MSG } from "../constants/messages"
import { msgSuccess, msgError } from "../utils/message"
import { useUserStore } from "../stores/userStore"
import { useProjectStore } from "../stores/projectStore"

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()
const projectStore = useProjectStore()
const formRef = ref()
const loading = ref(false)
const isKeyboardVisible = ref(false)
const abortController = ref<AbortController | null>(null)

let originalHeight = 0

function handleResize() {
  if (window.visualViewport) {
    isKeyboardVisible.value = window.visualViewport.height < originalHeight * 0.8
  }
}

onMounted(() => {
  originalHeight = window.innerHeight
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', handleResize)
  }

})

onUnmounted(() => {
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleResize)
  }
  abortController.value?.abort()
})
const form = reactive({ username: "", password: "", confirmPassword: "", nickname: "", email: "" })

const passwordStrength = computed(() => {
  const password = form.password
  if (!password) {
    return { level: 0, text: '' }
  }

  let charTypes = 0
  if (/[a-z]/.test(password)) charTypes++
  if (/[A-Z]/.test(password)) charTypes++
  if (/[0-9]/.test(password)) charTypes++
  if (/[^a-zA-Z0-9]/.test(password)) charTypes++

  const len = password.length
  let level = 1
  let text = t('auth.passwordWeak')

  if (len > 12 && charTypes >= 3) {
    level = 3
    text = t('auth.passwordStrong')
  } else if (len >= 6 && charTypes >= 2) {
    level = 2
    text = t('auth.passwordMedium')
  }

  return { level, text }
})
const usernameValidator = (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
  if (!value) {
    callback(t('auth.usernameRequired'))
    return
  }
  // 长度校验
  if (value.length < 4) {
    callback(t('auth.usernameLengthError'))
    return
  }
  if (value.length > 20) {
    callback(t('auth.usernameTooLong'))
    return
  }
  // 特殊字符校验
  if (/[^a-zA-Z0-9_]/.test(value)) {
    callback(t('auth.specialCharError'))
    return
  }
  // 格式校验
  if (!/^[a-zA-Z0-9_]{4,20}$/.test(value)) {
    callback(t('auth.usernameFormatError'))
    return
  }
  callback()
}
const emailValidator = (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
  // 邮箱为非必填
  if (!value || !value.trim()) {
    callback()
    return
  }
  const trimmed = value.trim()
  // 邮箱长度验证（最大 255 字符）
  if (trimmed.length > 255) {
    callback(t('auth.emailTooLong'))
    return
  }
  // 邮箱格式验证
  if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(trimmed)) {
    callback(t('auth.emailFormatError'))
    return
  }
  callback()
}
// 密码验证：至少 6 位任意字符
const passwordValidator = (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
  if (!value) {
    callback(t('auth.passwordRequired'))
    return
  }
  if (value.length < 6) {
    callback(t('auth.passwordMinLength'))
    return
  }
  if (value.length > 128) {
    callback(t('auth.passwordTooLong'))
    return
  }
  callback()
}
const rules = {
  username: [{ required: true, validator: usernameValidator, trigger: ["blur", "change"] }],
  password: [
    { required: true, validator: passwordValidator, trigger: ["blur", "change"] },
  ],
  confirmPassword: [
    { required: true, message: t('auth.confirmPasswordRequired'), trigger: ["blur", "change"] },
    {
      validator: (_rule: import('element-plus').FormItemRule, value: string, callback: (msg?: string) => void) => {
        if (value !== form.password) callback(t('auth.passwordMismatch'))
        else callback()
      },
      trigger: ["blur", "change"],
    },
  ],
  email: [{ required: false, validator: emailValidator, trigger: ["blur", "change"] }],
  nickname: [],
}

async function handleRegister() {
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

  const controller = new AbortController()
  abortController.value = controller
  const SUBMIT_TIMEOUT = 30000
  const timer = setTimeout(() => {
    if (loading.value) {
      controller.abort()
      loading.value = false
      msgError(t('common.timeout'))
    }
  }, SUBMIT_TIMEOUT)

  loading.value = true
  try {
    await userStore.register(form.username, form.password, form.nickname, form.email, controller.signal)
    msgSuccess(MSG.REGISTER_SUCCESS)
    // 重置表单，避免返回注册页时看到旧数据
    form.username = ''
    form.password = ''
    form.confirmPassword = ''
    form.nickname = ''
    form.email = ''
    const redirect = sessionStorage.getItem("login_redirect")
    sessionStorage.removeItem("login_redirect")

    // 注册后加载项目列表，确认私有副本已创建
    let hasPrivateProject = false
    let firstProjectId: number | null = null
    try {
      await projectStore.fetchProjects()
      const privateProjects = projectStore.projects.filter((p: { global_demo?: number }) => (p.global_demo ?? 0) !== 1)
      hasPrivateProject = privateProjects.length > 0
      firstProjectId = privateProjects[0]?.id ?? null
    } catch {
      // 项目列表获取失败不阻塞注册流程
    }

    void router.push(redirect || "/dashboard?newuser=1")

    // 新用户欢迎引导
    if (hasPrivateProject && firstProjectId) {
      setTimeout(() => {
        void ElMessageBox.alert(
          t('auth.welcomeWithProjectDesc'),
          t('auth.welcome'),
          {
            confirmButtonText: t('auth.startExploring'),
            type: 'success',
          }
        )
      }, 800)
    } else if (projectStore.projects.length === 0) {
      setTimeout(() => {
        void ElMessageBox.confirm(
          t('auth.noProjectAfterRegister'),
          t('auth.welcome'),
          {
            confirmButtonText: t('auth.createFirstProject'),
            cancelButtonText: t('auth.later'),
            type: 'info',
          }
        ).then(() => {
          void router.push("/dashboard?newuser=1&create=1")
        })
      }, 500)
    }
  } catch (e: unknown) {
    // 超时/主动取消的请求不显示错误
    if ((e as Error)?.name === 'AbortError') return
    const errData = (e as { response?: { data?: { message?: string; detail?: string } } })?.response?.data
    const msg = errData?.message || errData?.detail
    msgError(msg || t('auth.registerFailed'))
    // 注册失败后清空密码字段，聚焦到用户名输入框
    form.password = ''
    form.confirmPassword = ''
    // 自动聚焦到第一个错误字段
    formRef.value?.$el?.querySelector('.el-form-item.is-error input')?.focus()
  } finally {
    clearTimeout(timer)
    abortController.value = null
    loading.value = false
  }
}
</script>

<style scoped>
</style>

<style src="./RegisterView.css"></style>
