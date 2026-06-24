<template>
  <div v-if="visible" class="readonly-banner" :class="mode" role="status" aria-live="polite">
    <div class="readonly-banner__icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
        stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="4" y="10" width="16" height="10" rx="2" />
        <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </svg>
    </div>
    <div class="readonly-banner__text">
      <template v-if="mode === 'guest'">
        您正在以访客模式浏览种子演示项目，登录后可 Fork 到您的私有副本进行编辑。
      </template>
      <template v-else-if="mode === 'seed'">
        这是公开的种子演示项目（只读）。Fork 到您的私有副本即可自由编辑所有内容。
      </template>
    </div>
    <div class="readonly-banner__actions">
      <template v-if="mode === 'guest'">
        <el-button type="primary" size="small" @click="goLogin">立即登录</el-button>
      </template>
      <template v-else-if="mode === 'seed'">
        <el-button
          v-if="hasPrivateCopy"
          type="primary"
          size="small"
          @click="goPrivateCopy"
        >前往我的副本</el-button>
        <el-button
          v-else
          type="primary"
          size="small"
          :loading="forking"
          @click="handleFork"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;display:inline-block;vertical-align:-2px;">
            <circle cx="6" cy="3" r="2" />
            <circle cx="18" cy="3" r="2" />
            <circle cx="12" cy="21" r="2" />
            <path d="M6 5v3a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V5" />
            <path d="M12 12v7" />
          </svg>
          Fork 到我的副本
        </el-button>
      </template>
      <button class="readonly-banner__close" @click="dismissBanner" :title="$t('common.dismiss') || '不再提示'" aria-label="关闭提示">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { useUserStore } from "../../stores/userStore"
import { useProjectStore } from "../../stores/projectStore"
import { RoutePaths } from "../../router/paths"
import { forkSeedProject } from "../../api/projects"
import { logger } from "../../utils/logger"

defineOptions({ name: "ReadOnlyBanner" })

const props = defineProps<{
  force?: "guest" | "seed" | null
}>()
const userStore = useUserStore()
const projectStore = useProjectStore()
const router = useRouter()

const DISMISS_KEY_PREFIX = "api_pilot_readonly_dismissed_"

const dismissed = ref(false)
const forking = ref(false)

const mode = computed<"guest" | "seed" | null>(() => {
  if (props.force) return props.force
  if (userStore.isGuest) return "guest"
  if (projectStore.isReadOnly) return "seed"
  return null
})

const dismissKey = computed(() => {
  const pid = projectStore.currentProjectId ?? "guest"
  return DISMISS_KEY_PREFIX + pid
})

function checkDismissed() {
  try {
    dismissed.value = localStorage.getItem(dismissKey.value) === "true"
  } catch {
    dismissed.value = false
  }
}

watch(
  () => projectStore.currentProjectId,
  () => {
    checkDismissed()
  },
  { immediate: true }
)

watch(
  () => userStore.isGuest,
  () => {
    checkDismissed()
  }
)

const visible = computed(() => mode.value !== null && !dismissed.value)

const hasPrivateCopy = computed(() => {
  return projectStore.projects.some(
    (p) => p.global_demo !== 1 && p.id !== projectStore.currentProjectId
  )
})

function goLogin() {
  void router.push({ path: RoutePaths.login, query: { redirect: router.currentRoute.value.fullPath } })
}

function goPrivateCopy() {
  const target = projectStore.projects.find(
    (p) => p.global_demo !== 1 && p.id !== projectStore.currentProjectId
  )
  if (!target) return
  projectStore.setCurrentProject(target.id)
  void router.push({ path: `/projects/${target.id}/apis` })
}

async function handleFork() {
  if (forking.value) return
  forking.value = true
  try {
    const res = await forkSeedProject()
    const data = (res as unknown as { data: { id: number; name: string; is_new: boolean; message: string } }).data
    if (data?.id) {
      // 刷新项目列表
      await projectStore.fetchProjects(1, 50)
      // 跳转到新项目
      projectStore.setCurrentProject(data.id)
      void router.push({ path: `/projects/${data.id}/apis` })
      ElMessage.success(data.message || "Fork 成功，已为您创建私有副本")
    }
  } catch (err) {
    logger.error("[ReadOnlyBanner] fork failed:", err)
    ElMessage.error("Fork 失败，请稍后重试")
  } finally {
    forking.value = false
  }
}

function dismissBanner() {
  dismissed.value = true
  try {
    localStorage.setItem(dismissKey.value, "true")
  } catch {
    /* localStorage 不可用 */
  }
}
</script>

<style scoped>
.readonly-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2-5) var(--space-4);
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid;
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.readonly-banner.guest {
  background: var(--color-primary-50);
  border-color: var(--color-primary-200);
  color: var(--color-primary-800);
}

.readonly-banner.seed {
  background: var(--color-warning-50);
  border-color: var(--color-warning-200);
  color: var(--color-warning-800);
}

.readonly-banner__icon {
  display: inline-flex;
  flex-shrink: 0;
}

.readonly-banner__text {
  flex: 1;
  min-width: 0;
}

.readonly-banner__actions {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--space-2);
}

.readonly-banner__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: opacity var(--duration-fast) var(--ease-smooth), background-color var(--duration-fast) var(--ease-smooth);
}

.readonly-banner__close:hover {
  opacity: 1;
  background: var(--color-black-alpha-08);
}

html.dark .readonly-banner__close:hover {
  background: var(--color-white-alpha-12);
}

html.dark .readonly-banner.guest {
  background: var(--color-primary-alpha-12);
  border-color: var(--color-primary-alpha-40);
  color: var(--color-primary-200);
}

html.dark .readonly-banner.seed {
  background: var(--color-warning-alpha-12);
  border-color: var(--color-warning-alpha-40);
  color: var(--color-warning-200);
}
</style>
