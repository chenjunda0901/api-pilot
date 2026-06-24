<template>
  <div class="member-manager">
    <!-- 头部操作栏 -->
    <div class="member-toolbar">
      <span class="member-count">共 {{ members.length }} 名成员</span>
      <el-button size="small" type="primary" @click="showInviteDialog = true">
        <UserPlus :size="14" style="margin-right: 4px" />邀请成员
      </el-button>
    </div>

    <!-- 邀请对话框 -->
    <el-dialog v-model="showInviteDialog" title="邀请成员" width="420px" :close-on-click-modal="false">
      <el-form :model="inviteForm" label-position="top">
        <el-form-item label="用户 ID" :rules="[{ required: true, message: '请输入用户 ID' }]">
          <el-input-number
            v-model="inviteForm.user_id"
            :min="1"
            style="width: 100%"
            placeholder="输入用户的数字 ID"
          />
          <span class="form-hint">请输入被邀请用户的数字 ID（对方可在「个人中心 → 基本信息 → 用户 ID」中查看）</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="inviteForm.role" style="width: 100%">
            <el-option label="访客 (viewer) — 只读权限" value="viewer" />
            <el-option label="成员 (member) — 基础权限" value="member" />
            <el-option label="编辑者 (editor) — 读写权限" value="editor" />
            <el-option label="项目管理员 (owner) — 完全控制" value="owner" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInviteDialog = false">取消</el-button>
        <el-button type="primary" :loading="inviting" :disabled="!inviteForm.user_id" @click="handleInvite">邀请</el-button>
      </template>
    </el-dialog>

    <!-- 角色修改对话框 -->
    <el-dialog v-model="showRoleDialog" title="修改角色" width="380px">
      <el-select v-model="editRoleForm.role" style="width: 100%">
          <el-option label="访客 (viewer) — 只读" value="viewer" />
          <el-option label="成员 (member) — 基础" value="member" />
          <el-option label="编辑者 (editor) — 读写" value="editor" />
          <el-option label="项目管理员 (owner) — 完全控制" value="owner" />
        </el-select>
      <template #footer>
        <el-button @click="showRoleDialog = false">取消</el-button>
        <el-button type="primary" :loading="updatingRole" @click="handleUpdateRole">确认</el-button>
      </template>
    </el-dialog>

    <!-- 成员列表 -->
    <div v-if="!isLoggedIn" class="member-empty">
      <div class="empty-icon"><Users :size="40" /></div>
      <p>请登录后查看成员列表</p>
    </div>

    <div v-else-if="members.length === 0" class="member-empty">
      <div class="empty-icon"><Users :size="40" /></div>
      <p>暂无成员，点击上方按钮邀请</p>
    </div>

    <div v-else class="member-list" v-loading="loading">
      <div
        v-for="m in members"
        :key="m.user_id"
        class="member-row"
      >
        <div class="member-avatar" :style="{ background: getAvatarColor(m.nickname || m.username) }">
          {{ getInitial(m.nickname || m.username) }}
        </div>
        <div class="member-info">
          <div class="member-name">
            {{ m.nickname || m.username }}
            <el-tag v-if="m.user_id === currentUserId" size="small" type="info" effect="plain">我</el-tag>
          </div>
          <div class="member-username">@{{ m.username }}</div>
        </div>
        <div class="member-email" v-if="m.email">{{ m.email }}</div>
        <div class="member-role">
          <el-tag
            :type="roleTagType(m.role)"
            size="small"
            effect="plain"
          >
            {{ roleLabel(m.role) }}
          </el-tag>
        </div>
        <div class="member-actions">
          <el-button
            v-if="canManage && m.user_id !== currentUserId"
            size="small"
            text
            @click="openRoleDialog(m)"
          >
            <Shield :size="14" />角色
          </el-button>
          <el-button
            v-if="canManage && m.user_id !== currentUserId"
            size="small"
            text
            type="danger"
            @click="handleRemove(m)"
          >
            <UserX :size="14" />移除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import request from '../api/request'
import { msgSuccess, msgError } from '../utils/message'
import { logger, isSilentAuthError } from '../utils/logger'
import { useUserStore } from '../stores/userStore'
import { useProjectStore } from '../stores/projectStore'
import { UserPlus, Users, Shield, UserX } from 'lucide-vue-next'
import { useRequireLogin } from '../composables/useRequireLogin'

const { requireLogin } = useRequireLogin()

const props = defineProps<{
  projectId: number
}>()

const userStore = useUserStore()
const projectStore = useProjectStore()
const currentUserId = computed(() => userStore.user?.id ?? 0)
const isLoggedIn = computed(() => !!userStore.user)
const canManage = computed(() => {
  const user = userStore.user
  if (!user) return false
  // 系统管理员可管理所有项目成员
  if (user.role === 'admin') return true
  // 通过项目成员角色判断（owner 为项目管理员，而非系统角色）
  const project = projectStore.projects.find((p) => p.id === props.projectId)
  if (project?.created_by === user.id) return true
  return project?.role === 'owner'
})

interface Member {
  id: number
  user_id: number
  username: string
  nickname: string
  email: string
  role: string
  created_at: string
}

const members = ref<Member[]>([])
const loading = ref(false)
const showInviteDialog = ref(false)
const showRoleDialog = ref(false)
const inviting = ref(false)
const updatingRole = ref(false)
const inviteForm = ref<{ user_id: number | null; role: string }>({ user_id: null, role: 'member' })
const editRoleForm = ref<{ user_id: number; role: string }>({ user_id: 0, role: 'member' })

function getInitial(name: string): string {
  return name?.charAt(0) || '?'
}

function getAvatarColor(name: string): string {
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
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function roleTagType(role: string): string {
  const map: Record<string, string> = {
    owner: 'danger',
    editor: 'warning',
    member: 'primary',
    viewer: 'info',
    admin: 'danger',
  }
  return map[role] || 'info'
}

function roleLabel(role: string): string {
  const map: Record<string, string> = {
    owner: '项目管理员',
    editor: '编辑者',
    member: '成员',
    viewer: '访客',
    admin: '系统管理员',
  }
  return map[role] || role
}

async function fetchMembers() {
  loading.value = true
  try {
    const res = await request.get(`/projects/${props.projectId}/members`)
    members.value = res.data || []
  } catch (e: unknown) {
    if (!isSilentAuthError(e)) {
      logger.error('[MemberManager] Failed to load members:', e)
      msgError('加载成员列表失败')
    }
  } finally {
    loading.value = false
  }
}

async function handleInvite() {
  if (!(await requireLogin('邀请成员'))) return
  inviting.value = true
  try {
    const res = await request.post(`/projects/${props.projectId}/members`, {
      user_id: inviteForm.value.user_id,
      role: inviteForm.value.role,
    })
    msgSuccess(res.message || '邀请成功')
    inviteForm.value = { user_id: null, role: 'member' }
    showInviteDialog.value = false
    await fetchMembers()
  } catch (e: unknown) {
    msgError((e as Error)?.message || '邀请失败')
  } finally {
    inviting.value = false
  }
}

function openRoleDialog(m: Member) {
  editRoleForm.value = { user_id: m.user_id, role: m.role }
  showRoleDialog.value = true
}

async function handleUpdateRole() {
  if (!(await requireLogin('修改角色'))) return
  updatingRole.value = true
  try {
    const res = await request.put(
      `/projects/${props.projectId}/members/${editRoleForm.value.user_id}/role`,
      { role: editRoleForm.value.role }
    )
    msgSuccess(res.message || '角色已更新')
    showRoleDialog.value = false
    await fetchMembers()
  } catch (e: unknown) {
    msgError((e as Error)?.message || '更新失败')
  } finally {
    updatingRole.value = false
  }
}

async function handleRemove(m: Member) {
  if (!(await requireLogin('移除成员'))) return
  const { ElMessageBox } = await import('element-plus')
  try {
    await ElMessageBox.confirm(
      `确定将 ${m.nickname || m.username} 移出项目？`,
      '移除成员',
      { confirmButtonText: '确定移除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const res = await request.delete(`/projects/${props.projectId}/members/${m.user_id}`)
    msgSuccess(res.message || '成员已移除')
    await fetchMembers()
  } catch (e: unknown) {
    msgError((e as Error)?.message || '移除失败')
  }
}

onMounted(async () => {
  // 未登录时不发起请求，避免 401 控制台错误
  if (!isLoggedIn.value) return
  await fetchMembers()
})
</script>

<style scoped>
/* 成员管理器 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角/阴影均使用 CSS 变量，确保暗色模式自动适配
 */
.member-manager {
  padding: var(--space-1) 0;
}
.member-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}
.member-count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}

/* 空状态 — 与全局 .empty-state 风格对齐 */
.member-empty {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}
.member-empty .empty-icon {
  margin-bottom: var(--space-2);
  opacity: 0.5;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-xl);
  background: var(--grad-primary-subtle);
  color: var(--primary-400);
  display: flex;
  align-items: center;
  justify-content: center;
}
.member-empty p {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 240px;
  line-height: var(--leading-relaxed);
}

/* 成员列表 — 使用 design tokens 统一风格 */
.member-list {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface-card);
  box-shadow: var(--shadow-xs);
}
.member-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-subtle);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-spring);
}
.member-row:last-child {
  border-bottom: none;
}
.member-row:hover {
  background: var(--surface-hover);
  transform: translateX(2px);
}

/* 头像 — 品牌化（与 ProfileCenterDialog / TopBar 一致） */
.member-avatar {
  font-family: var(--font-sans);
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  color: var(--text-inverse);
  font-weight: var(--weight-bold);
  font-size: var(--font-size-lg);
  letter-spacing: var(--tracking-tight);
  text-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--duration-fast) var(--ease-spring),
              box-shadow var(--duration-base) var(--ease-out);
  box-shadow: var(--shadow-sm);
}
.member-avatar:hover {
  transform: scale(1.06);
  box-shadow: var(--shadow-md);
}

/* 成员信息 */
.member-info {
  flex: 1;
  min-width: 0;
}
.member-name {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: var(--tracking-tight);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}
.member-username {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--spacing-xs);
}
.member-email {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  flex-shrink: 0;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.member-role {
  flex-shrink: 0;
}
.member-actions {
  flex-shrink: 0;
  display: flex;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-smooth);
}
.member-row:hover .member-actions {
  opacity: 1;
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--spacing-xs);
  display: block;
  line-height: var(--leading-relaxed);
}

/* 暗色模式适配 */
html.dark .member-list {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-xs);
}
html.dark .member-row {
  border-color: var(--border-subtle);
}
html.dark .member-row:hover {
  background: var(--surface-hover);
}
html.dark .member-name { color: var(--text-primary); }
html.dark .member-email { color: var(--text-muted); }
html.dark .member-avatar {
  box-shadow: var(--shadow-sm);
}
html.dark .member-avatar:hover {
  box-shadow: var(--shadow-md);
}

/* 移动端：始终显示操作按钮 */
@media (max-width: 768px) {
  .member-actions { opacity: 1; }
  .member-email { display: none; }
}
</style>
