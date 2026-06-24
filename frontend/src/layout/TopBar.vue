<template>
  <div class="topbar" role="banner">
    <div class="left">
      <button class="hamburger-btn" @click="$emit('toggle-sidebar')" :aria-label="$t('topbar.menu') || '菜单'">
        <Menu :size="18" />
      </button>
      <div class="topbar-project-selector">
      <el-dropdown v-model:visible="projectDropdownVisible" trigger="click" @command="handleProjectCommand" @visible-change="onProjectDropdownVisibleChange">
        <button class="project-dropdown-trigger" :aria-haspopup="true" :aria-expanded="projectDropdownVisible" aria-label="选择项目">
          <folder-kanban :size="14" />
          <span class="project-trigger-name" :class="{ 'is-placeholder': !currentProject?.name }">{{
            currentProject?.name || $t('topbar.selectProject')
          }}</span>
          <span v-if="currentProject" class="project-vis-badge" :class="currentProject.is_public ? 'is-public' : 'is-private'">
            {{ currentProject.is_public ? "公开" : "私有" }}
          </span>
          <span v-if="currentProject?.global_demo === 1" class="project-vis-badge is-demo">演示</span>
          <chevron-down :size="12" :class="{ 'rotated': projectDropdownVisible }" />
        </button>
        <template #dropdown>
          <div class="project-dropdown-panel">
            <div class="pd-search">
              <svg viewBox="0 0 16 16" fill="none" width="14" height="14" class="pd-search-icon">
                <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5" />
                <path d="M11 11L15 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
              </svg>
              <input v-model="projectSearchKeyword" :placeholder="$t('topbar.searchProjectPlaceholder')" class="pd-search-input" @click.stop />
            </div>
            <div class="pd-section" v-if="filteredPrivateProjects.length > 0">
              <div class="pd-section-label">我的项目</div>
              <el-dropdown-item
                v-for="p in filteredPrivateProjects"
                :key="p.id"
                :command="'switch-' + p.id"
                :class="{ 'project-active': p.id === projectStore.currentProjectId }"
              >
                <span v-if="p.id === projectStore.currentProjectId" class="project-check">&#10003; </span>
                <span class="pd-item-name">{{ p.name }}</span>
                <span v-if="p.is_public" class="pd-item-badge is-public">公开</span>
              </el-dropdown-item>
            </div>
            <div class="pd-section" v-if="filteredDemoProjects.length > 0">
              <div class="pd-section-label">演示项目</div>
              <el-dropdown-item
                v-for="p in filteredDemoProjects"
                :key="p.id"
                :command="'switch-' + p.id"
                :class="{ 'project-active': p.id === projectStore.currentProjectId }"
              >
                <span v-if="p.id === projectStore.currentProjectId" class="project-check">&#10003; </span>
                <span class="pd-item-name">{{ p.name }}</span>
                <span class="pd-item-badge is-demo">演示</span>
              </el-dropdown-item>
            </div>
            <div class="pd-section" v-if="filteredProjects.length === 0">
              <div class="pd-empty-hint">{{ $t('topbar.noMatchProject') }}</div>
            </div>
            <div class="pd-divider"></div>
            <el-dropdown-item command="new-project">
              <plus :size="14" /> {{ $t('topbar.newProject') }}
            </el-dropdown-item>
            <el-dropdown-item command="manage-members" v-if="projectStore.currentProjectId && canManageMembers">
              <users :size="14" /> {{ $t('topbar.manageMembers') || '成员管理' }}
            </el-dropdown-item>
            <el-dropdown-item command="open-settings" v-if="projectStore.currentProjectId && canManageSettings">
              <settings :size="14" /> {{ $t('topbar.projectSettings') }}
            </el-dropdown-item>
            <el-dropdown-item command="import-project" v-if="projectStore.currentProjectId && canEdit">
              <upload :size="14" /> {{ $t('topbar.importProject') }}
            </el-dropdown-item>
            <el-dropdown-item command="export-project" v-if="projectStore.currentProjectId && canExport">
              <download :size="14" /> {{ $t('topbar.exportProject') }}
            </el-dropdown-item>
            <div class="pd-divider" v-if="projectStore.currentProjectId && canEdit"></div>
            <div class="danger-item" v-if="projectStore.currentProjectId && canEdit"><el-dropdown-item command="delete-project">
              <trash-2 :size="14" /> {{ $t('topbar.deleteProject') }}
            </el-dropdown-item></div>
          </div>
        </template>
      </el-dropdown>
    </div>
    </div>

    <div class="center">
      <button class="search-btn" @click="$emit('search')" aria-label="搜索">
        <search :size="14" />
        <span>{{ $t('topbar.searchBtn') }}</span>
        <kbd>Ctrl+K</kbd>
      </button>
    </div>

    <div class="right">
      <!-- 环境选择器：所有项目内页面常驻可见 -->
      <div class="env-selector" v-if="isProjectPage && projectStore.currentProjectId && envStore.environments.length > 0">
        <el-dropdown trigger="click" @command="handleEnvSwitch">
          <button class="env-btn" aria-label="切换环境">
            <Globe :size="13" />
            <span class="env-btn-name">{{ envStore.currentEnv?.name || $t('topbar.selectEnv') }}</span>
            <ChevronsUpDown :size="12" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <div class="pd-section-label">{{ $t('topbar.switchEnv') }}</div>
              <el-dropdown-item
                v-for="env in envStore.environments"
                :key="env.id"
                :command="env.id"
                :class="{ 'env-active': env.id === envStore.currentEnvId }"
              >
                <div class="env-item-content">
                  <div class="env-item-top">
                    <span v-if="env.id === envStore.currentEnvId" class="env-check">&#10003;</span>
                    <span class="env-item-name">{{ env.name }}</span>
                  </div>
                  <span v-if="getEnvDomain(env)" class="env-item-domain" :title="getEnvDomain(env)">{{ getEnvDomain(env) }}</span>
                </div>
              </el-dropdown-item>
              <el-dropdown-item divided command="config">
                <Settings :size="14" style="margin-right: 4px;" /> 配置环境
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 主题切换 -->
      <button class="topbar-action-btn" @click="toggleTheme" :title="theme === 'dark' ? $t('topbar.switchToLight') : $t('topbar.switchToDark')" :aria-label="theme === 'dark' ? $t('topbar.switchToLight') : $t('topbar.switchToDark')">
        <Sun v-if="theme === 'light'" :size="14" />
        <Moon v-else :size="14" />
      </button>

<!-- 用户 -->
      <template v-if="userStore.user">
        <el-dropdown @command="handleCommand" trigger="click">
          <button class="avatar-btn" aria-label="用户菜单">
            <span class="avatar-name">{{ userStore.user?.nickname || userStore.user?.username }}</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <div class="user-dropdown-header">
                <span class="user-dropdown-avatar" :style="{ background: avatarBg }">{{ initials }}</span>
                <div class="user-dropdown-info">
                  <span class="user-dropdown-name">{{ userStore.user?.nickname || userStore.user?.username }}</span>
                  <span class="user-dropdown-email">{{ userStore.user?.email || "" }}</span>
                </div>
              </div>
              <el-dropdown-item command="profile">
                <user :size="14" />{{ $t('auth.profile') }}
              </el-dropdown-item>
              <el-dropdown-item command="new-project">
                <folder-plus :size="14" />{{ $t('nav.newProject') }}
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <log-out :size="14" />{{ $t('auth.logout') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <button class="login-btn" @click="showLogin" aria-label="登录">
          <user :size="14" />
          <span>{{ $t('auth.login') }}</span>
        </button>
      </template>
    </div>

    <ProfileCenterDialog v-model:visible="showProfileDialog" />

    <!-- 新建项目对话框 -->
    <el-dialog v-model="showNewProjectDialog" title="新建项目" width="420px" :close-on-click-modal="false" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-form-item label="项目名称">
          <el-input v-model="newProjectForm.name" placeholder="输入项目名称" maxlength="50" @keyup.enter="confirmCreateProject" />
        </el-form-item>
        <el-form-item label="项目可见性">
          <el-radio-group v-model="newProjectForm.is_public" size="small">
            <el-radio-button :value="false">私有</el-radio-button>
            <el-radio-button :value="true">公开</el-radio-button>
          </el-radio-group>
          <p class="new-project-hint">{{ newProjectForm.is_public ? '公开项目对所有用户可见' : '私有项目仅创建者可见' }}</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewProjectDialog = false">取消</el-button>
        <el-button type="primary" :loading="creatingProject || projectStore.isCreating" :disabled="!newProjectForm.name.trim()" @click="confirmCreateProject">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from "vue"
import { useRouter, useRoute } from "vue-router"
import { useI18n } from "vue-i18n"
import { ElMessageBox } from "element-plus"
import { msgSuccess, msgError } from "../utils/message"
import type { ApiError } from "../types/common"
import { logger } from "../utils/logger"
import { useUserStore } from "../stores/userStore"
import { useProjectStore } from "../stores/projectStore"
import { useEnvStore } from "../stores/envStore"
import { useTheme } from "../composables/useTheme"
import { useRequireLogin } from "../composables/useRequireLogin"
import { useProjectPermission } from "../composables/useProjectPermission"
import {
  Search, User, FolderKanban, FolderPlus, ChevronDown,
  Plus, Settings, Trash2, LogOut, Upload, Download,
  Sun, Moon, Globe, ChevronsUpDown, Menu, Users,
} from "lucide-vue-next"
import request from "../api/request"
import ProfileCenterDialog from "../components/ProfileCenterDialog.vue"
import { RoutePaths } from "../router/paths"

defineEmits<{ search: []; 'toggle-sidebar': [] }>()

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const userStore = useUserStore()
const projectStore = useProjectStore()
const envStore = useEnvStore()
const { theme, toggleTheme } = useTheme()
const { requireLogin } = useRequireLogin()
const { canManageMembers, canManageSettings, canExport, canEdit } = useProjectPermission()

const showProfileDialog = ref(false)
const projectSearchKeyword = ref("")
const projectDropdownVisible = ref(false)

function toggleProjectDropdown() {
  projectDropdownVisible.value = !projectDropdownVisible.value
}

function onProjectDropdownVisibleChange(visible: boolean) {
  projectDropdownVisible.value = visible
}

// ── 新建项目对话框 ──
const showNewProjectDialog = ref(false)
const creatingProject = ref(false)
const newProjectForm = reactive({ name: '', is_public: false })

const filteredProjects = computed(() => {
  const kw = projectSearchKeyword.value.trim().toLowerCase()
  if (!kw) return projectStore.projects
  return projectStore.projects.filter((p: { name: string }) => p.name.toLowerCase().includes(kw))
})

const privateProjects = computed(() => {
  return projectStore.projects.filter((p: { global_demo?: number }) => (p.global_demo ?? 0) !== 1)
})

const demoProjects = computed(() => {
  return projectStore.projects.filter((p: { global_demo?: number }) => (p.global_demo ?? 0) === 1)
})

const filteredPrivateProjects = computed(() => {
  const kw = projectSearchKeyword.value.trim().toLowerCase()
  if (!kw) return privateProjects.value
  return privateProjects.value.filter((p: { name: string }) => p.name.toLowerCase().includes(kw))
})

const filteredDemoProjects = computed(() => {
  const kw = projectSearchKeyword.value.trim().toLowerCase()
  if (!kw) return demoProjects.value
  return demoProjects.value.filter((p: { name: string }) => p.name.toLowerCase().includes(kw))
})

// 环境选择器在所有项目内页面常驻可见（接口/场景/报告/设置等）
const isProjectPage = computed(() => route.path.includes('/projects/'))
const currentProject = computed(() => {
  return projectStore.projects.find((p) => p.id === projectStore.currentProjectId)
})

const avatarBg = computed(() => {
  const displayName = userStore.user?.nickname || userStore.user?.username || "U"
  // 中深色调：与界面协调 + 白色文字足够清晰（中文汉字需要更高对比度）
  const colors = [
    'var(--avatar-palette-1)',
    'var(--avatar-palette-2)',
    'var(--avatar-palette-3)',
    'var(--avatar-palette-4)',
    'var(--avatar-palette-5)',
    'var(--avatar-palette-6)',
    'var(--avatar-palette-7)',
    'var(--avatar-palette-8)',
    'var(--avatar-palette-9)',
    'var(--avatar-palette-10)',
  ]
  let hash = 0
  for (let i = 0; i < displayName.length; i++) {
    hash = displayName.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
})

const initials = computed(() => {
  const displayName = userStore.user?.nickname || userStore.user?.username || "U"
  return displayName.slice(0, 1)
})

function showLogin() {
  router.push(RoutePaths.login).catch(() => { window.location.hash = "#/login" })
}

async function handleCommand(cmd: string) {
  if (cmd === "profile") {
    showProfileDialog.value = true
  } else if (cmd === "new-project") {
    if (!await requireLogin("新建项目")) return
    newProjectForm.name = ''
    newProjectForm.is_public = false
    showNewProjectDialog.value = true
  } else if (cmd === "logout") {
    try {
      await ElMessageBox.confirm("确定要退出登录吗？", "退出确认", {
        confirmButtonText: "退出", cancelButtonText: "取消", type: "info",
      })
    } catch {
      return // 用户取消退出
    }
    try {
      await userStore.logout()
    } catch (err) {
      logger.error('[TopBar] logout error:', err)
      msgError('登出失败，请重试')
    }
    // 强制跳转到登录页，确保状态完全刷新
    window.location.href = '#/login'
    window.location.reload()
  }
}

function handleEnvSwitch(cmd: string | number) {
  if (cmd === 'config') {
    const pid = projectStore.currentProjectId
    if (pid) {
      void router.push(`${RoutePaths.settings(pid)}?tab=env`)
    }
    return
  }
  envStore.switchEnv(cmd as number)
  // 切换环境后派发全局事件，触发当前页数据刷新
  window.dispatchEvent(new CustomEvent('env:changed', { detail: { envId: cmd } }))
}

/** 从环境的服务列表中提取域名值（优先 is_base，否则取第一个） */
function getEnvDomain(env: {
  services?: Array<{ url?: string; is_base?: boolean }>
  variables?: Array<{ key: string; value: string; enabled: boolean }>
}): string {
  const svcs = env.services
  if (!svcs || !svcs.length) return ''
  const base = svcs.find(s => s.is_base) || svcs[0]
  if (!base?.url) return ''
  let raw = base.url.trim()
  // 解析 {{变量}}：合并项目全局变量 + 当前环境变量
  if (/\{\{.+?\}\}/.test(raw)) {
    const varMap = new Map<string, string>()
    // 项目全局变量（对所有环境生效）
    for (const v of envStore.projectGlobalVars) {
      if (v.key && v.enabled !== false) varMap.set(v.key, v.value || '')
    }
    // 环境变量覆盖同名全局变量
    for (const v of env.variables || []) {
      if (v.key && v.enabled !== false) varMap.set(v.key, v.value || '')
    }
    raw = raw.replace(/\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/g, (_match, key: string) => {
      return varMap.has(key) ? varMap.get(key) || '' : `{{${key}}}`
    })
  }
  try {
    return new URL(raw).host
  } catch {
    // 非 URL 格式，截取 host 部分
    const match = raw.match(/^https?:\/\/([^/]+)/)
    return match ? match[1] : raw
  }
}

async function confirmCreateProject() {
  const name = newProjectForm.name.trim()
  if (!name) return
  creatingProject.value = true
  try {
    const newProj = await projectStore.createProject(name, newProjectForm.is_public)
    if (newProj) {
      await projectStore.fetchProjects()
      msgSuccess("项目已创建")
      showNewProjectDialog.value = false
      void router.push(RoutePaths.apiList(newProj.id))
    }
  } catch (e: unknown) {
    const msg = (e as ApiError).response?.data?.message || "创建项目失败"
    msgError(msg)
  } finally {
    creatingProject.value = false
  }
}

async function handleProjectCommand(cmd: string) {
  if (cmd === "new-project") {
    if (!await requireLogin("新建项目")) return
    newProjectForm.name = ''
    newProjectForm.is_public = false
    showNewProjectDialog.value = true
  } else if (cmd === "manage-members") {
    void router.push(`${RoutePaths.settings(projectStore.currentProjectId)}?tab=member`)
  } else if (cmd === "open-settings") {
    void router.push(RoutePaths.settings(projectStore.currentProjectId))
  } else if (cmd === "import-project") {
    void router.push(`${RoutePaths.settings(projectStore.currentProjectId)}?tab=import`)
  } else if (cmd === "export-project") {
    void router.push(`${RoutePaths.settings(projectStore.currentProjectId)}?tab=export`)
  } else if (cmd === "delete-project") {
    if (!await requireLogin("删除项目")) return
    try {
      const projName = currentProject.value?.name || ""
      const { value } = await ElMessageBox.prompt(
        `此操作不可逆，将永久删除「${projName}」及所有关联数据。请输入项目名称「${projName}」确认删除：`,
        "删除项目",
        {
          confirmButtonText: "确认删除",
          cancelButtonText: "取消",
          type: "warning",
          inputPattern: new RegExp(`^${projName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`),
          inputErrorMessage: "输入的项目名称不匹配",
          inputPlaceholder: "请输入项目名称",
        }
      )
      if (value !== projName) return
      const deletingId = projectStore.currentProjectId
      await request.delete(`/projects/${deletingId}`)
      msgSuccess("项目已删除")
      await projectStore.fetchProjects()
      if (projectStore.currentProjectId === deletingId) {
        const first = projectStore.projects[0]
        if (first) projectStore.setCurrentProject(first.id)
      }
      void router.push(RoutePaths.dashboard)
    } catch { /* cancelled */ }
  } else if (cmd.startsWith("switch-")) {
    const id = parseInt(cmd.replace("switch-", ""))
    projectStore.setCurrentProject(id)
    if (route.params.id) {
      void router.push({ path: route.path.replace(/\/projects\/\d+/, `/projects/${id}`) })
    } else {
      void router.push(RoutePaths.dashboard)
    }
  }
}
</script>

<style scoped>
/* ── 顶栏容器 — 统一高度与间距 ── */
.topbar {
  height: var(--height-topbar);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-4);
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
  overflow: visible;
  position: relative;
  z-index: var(--z-topbar, 900);
}

.project-dropdown-panel {
  min-width: 260px;
  padding: var(--space-2-5);
  border-radius: var(--radius-xl);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-top: 1px solid var(--color-primary-alpha-12);
  box-shadow: 0 16px 40px var(--color-neutral-alpha-12);
}

.pd-search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2-5);
  margin-bottom: var(--space-2);
  border-radius: var(--radius-lg);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
}

.pd-search-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font: inherit;
  color: var(--text-primary);
}

.pd-section-label {
  padding: var(--space-2) var(--space-2) 6px;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.pd-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
}

.pd-divider {
  height: 1px;
  margin: var(--space-2) 0;
  background: var(--border-default);
}

.pd-empty-hint {
  padding: var(--space-3) var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.project-active {
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
}
.left, .center, .right {
  display: flex;
  align-items: center;
}
.left {
  flex: 0 0 auto;
}

/* ── 移动端汉堡菜单按钮 ── */
.hamburger-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color 160ms var(--ease-smooth), color 160ms var(--ease-smooth);
}
.hamburger-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
@media (max-width: 767px) {
  .hamburger-btn {
    display: inline-flex;
  }
}
.center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: var(--space-1);
  overflow: hidden;
}
.right {
  flex: 0 0 auto;
  gap: var(--space-4);
}

/* ── 面包屑 ── */
.breadcrumb-wrap {
  display: flex;
  align-items: center;
  min-width: 0;
}

/* ── 项目下拉 ── */
.project-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: 0 var(--space-3);
  height: 38px;
  background: linear-gradient(180deg, var(--color-white-alpha-96), var(--color-white-alpha-98));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth),
    transform var(--duration-fast) var(--ease-smooth);
  font-family: inherit;
  box-shadow: 0 1px 4px var(--color-neutral-alpha-04);
}
.project-dropdown-trigger:hover {
  background: var(--surface-hover);
  border-color: var(--primary-200);
  box-shadow: 0 0 0 1px var(--color-primary-alpha-06), var(--shadow-xs);
  transform: translateY(-1px);
}
.project-vis-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  line-height: 1;
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-full);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
  margin-left: auto;
}
.project-vis-badge.is-public {
  background: var(--color-success-alpha-10);
  color: var(--color-success);
}
.project-vis-badge.is-private {
  background: var(--surface-hover);
  color: var(--text-muted);
}
.project-vis-badge.is-demo {
  background: var(--color-primary-alpha-10);
  color: var(--color-primary);
}

/* 新建项目对话框提示文本 */
.new-project-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: var(--space-1) 0 0 0;
  line-height: var(--leading-normal);
}
.project-trigger-name {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-trigger-name.is-placeholder {
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}

.project-dropdown-trigger svg:last-child {
  transition: transform var(--duration-fast) var(--ease-smooth);
}

.project-dropdown-trigger svg:last-child.rotated {
  transform: rotate(180deg);
}

/* ── 搜索按钮 — 幽灵按钮样式 ── */
.search-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  height: 38px;
  min-width: 240px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: var(--transition-base);
  font-family: inherit;
}
.search-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
  box-shadow: 0 6px 18px var(--color-neutral-alpha-04);
  transform: translateY(-1px);
}
.search-btn kbd {
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  padding: var(--space-0-5) var(--space-1-5);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  line-height: 1;
  margin-left: auto;
}
.search-btn:hover kbd {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--surface-card);
}

/* ── 统一操作按钮 — 微交互升级 ── */
.topbar-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background-color 160ms var(--ease-smooth),
    border-color 160ms var(--ease-smooth),
    color 160ms var(--ease-smooth),
    box-shadow 160ms var(--ease-smooth),
    transform 160ms var(--ease-smooth);
}
.topbar-action-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: 0 1px 4px var(--color-black-alpha-03);
}
.topbar-action-btn:active {
  transform: scale(0.95);
}
.topbar-action-btn.active {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border-color: var(--primary-200);
}

/* ── 用户名按钮 ── */
.avatar-btn {
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-3);
  background: transparent;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.avatar-btn:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

/* 用户名文字 */
.avatar-name {
  line-height: 1.2;
}

/* ── 登录按钮 ── */
.login-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: 0 20px;
  height: 36px;
  background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  transition: background-color var(--duration-base) var(--ease-smooth),
    border-color var(--duration-base) var(--ease-smooth),
    color var(--duration-base) var(--ease-smooth),
    box-shadow var(--duration-base) var(--ease-smooth),
    transform var(--duration-base) var(--ease-smooth);
  box-shadow: 0 2px 8px var(--color-primary-alpha-30);
  font-family: inherit;
  letter-spacing: 0.02em;
}
.login-btn:hover {
  background: linear-gradient(135deg, var(--primary-600), var(--primary-700));
  box-shadow: 0 10px 22px var(--color-primary-alpha-20);
  transform: translateY(-1px);
}
.login-btn:active {
  transform: translateY(0) scale(0.98);
}

/* ── 环境选择器 ── */
.env-selector { display: flex; align-items: center; }
.env-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  height: 32px;
  padding: 0 10px;
  background: var(--surface-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  font-family: inherit;
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth),
    transform var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
}
.env-btn:hover {
  background: var(--color-primary-alpha-06);
  color: var(--text-primary);
  border-color: var(--primary-200);
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px var(--color-primary-alpha-06), var(--shadow-xs);
}
.env-btn-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 环境下拉项：名称 + 域名值（上下两行布局） */
.env-item-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
}
.env-item-top {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
}
.env-item-name {
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}
.env-item-domain {
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 20px;
}

/* ── 用户下拉 — 品牌化升级 ── */
.user-dropdown-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3-5);
  margin: -4px -4px 6px;
  background: var(--surface-nested);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  position: relative;
  overflow: hidden;
}
.user-dropdown-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--grad-primary);
  opacity: 0.5;
}
.user-dropdown-avatar {
  font-family: var(--font-sans);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: var(--text-on-primary);
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: -0.02em;
  text-shadow: 0 1px 2px var(--color-black-alpha-18);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow:
    0 2px 10px var(--color-neutral-alpha-08),
    0 0 0 2px var(--color-white-alpha-70),
    0 0 0 4px var(--color-primary-alpha-10);
}
.user-dropdown-info { display: flex; flex-direction: column; gap: var(--space-0-5); }
.user-dropdown-name {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  letter-spacing: var(--tracking-tight);
}
.user-dropdown-email {
  font-size: var(--text-sm);
  color: var(--text-muted);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 项目下拉面板 ── */
.project-dropdown-panel {
  padding: var(--space-2) 0;
  min-width: 240px;
}
.pd-section { padding: var(--space-1) 0; }
.pd-section-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: var(--space-1-5) var(--space-4) var(--space-1);
}
.pd-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: var(--space-1-5) 0;
}
.pd-search {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-1);
}
.pd-search-icon { flex-shrink: 0; color: var(--text-muted); }
.pd-search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
  color: var(--text-primary);
  outline: none;
  min-width: 0;
  font-family: inherit;
}
.pd-search-input::placeholder { color: var(--text-muted); }
.pd-empty-hint {
  padding: var(--space-5) var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.project-check {
  color: var(--primary-500);
  font-weight: var(--weight-bold);
  margin-right: 4px;
}
.pd-item-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pd-item-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: var(--weight-semibold);
  border-radius: 4px;
  margin-left: 6px;
  line-height: 1.4;
}
.pd-item-badge.is-public {
  background: var(--color-success-alpha-10);
  color: var(--color-success);
}
.pd-item-badge.is-demo {
  background: var(--color-primary-alpha-10);
  color: var(--color-primary);
}
:deep(.project-active) {
  background: var(--surface-selected);
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
}
.danger-item { color: var(--error); }
:deep(.danger-item) { color: var(--error); }
.env-check { color: var(--primary-500); }
.env-active { font-weight: var(--weight-semibold); }

/* ── Dark Mode ── */
html.dark .topbar {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
html.dark .project-dropdown-trigger:hover {
  background: var(--surface-hover);
  border-color: var(--border-default);
}
html.dark .project-vis-badge.is-public {
  background: var(--success-bg);
  color: var(--success);
}
html.dark .project-vis-badge.is-private {
  background: var(--surface-hover);
}
html.dark .project-vis-badge.is-demo {
  background: var(--color-primary-alpha-10);
  color: var(--primary-300);
}
html.dark .search-btn {
  color: var(--text-muted);
}
html.dark .search-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
}
html.dark .search-btn kbd {
  background: var(--surface-muted);
  border-color: var(--border-default);
  color: var(--text-muted);
}
html.dark .search-btn:hover kbd {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--surface-card);
}
html.dark .topbar-action-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
}
html.dark .topbar-action-btn.active {
  background: var(--color-primary-alpha-15);
  color: var(--primary-400);
  border-color: var(--color-primary-alpha-30);
}
html.dark .login-btn {
  background: var(--primary-500);
  box-shadow: 0 1px 4px var(--color-black-alpha-15);
}
html.dark .login-btn:hover {
  background: var(--primary-600);
}
html.dark .env-btn {
  background: var(--surface-hover);
  border-color: var(--border-default);
  color: var(--text-secondary);
}
html.dark .env-btn:hover {
  background: var(--color-primary-alpha-08);
  border-color: var(--color-primary-alpha-20);
  color: var(--text-primary);
}
html.dark .user-dropdown-header { background: var(--surface-nested); border-color: transparent; }
html.dark .user-dropdown-avatar {
  box-shadow:
    0 2px 10px var(--color-black-alpha-25),
    0 0 0 2px var(--color-neutral-alpha-90),
    0 0 0 4px var(--color-primary-alpha-12);
}
html.dark .user-dropdown-name { color: var(--text-primary); }
html.dark .pd-section-label { color: var(--text-muted); }
html.dark .pd-divider { background: var(--border-subtle); }
html.dark .pd-search { border-color: var(--border-subtle); }
html.dark .pd-search-input { color: var(--text-primary); }
html.dark .pd-search-input::placeholder { color: var(--text-muted); }
html.dark .pd-search-icon { color: var(--text-muted); }
html.dark .pd-empty-hint { color: var(--text-muted); }
</style>
