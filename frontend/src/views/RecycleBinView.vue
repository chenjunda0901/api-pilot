<template>
  <div v-if="!canViewRecycleBin" class="no-permission-wrap">
    <div class="no-permission-card">
      <div class="no-permission-icon">
        <Trash2 :size="48" />
      </div>
      <div class="no-permission-title">无访问权限</div>
      <div class="no-permission-desc">回收站仅对具有编辑权限的用户开放，请联系项目管理员获取权限。</div>
    </div>
  </div>
  <PageLayout
    v-else
    :title="$t('recycleBin.title')"
    :subtitle="$t('recycleBin.subtitle')"
    :kicker="$t('recycleBin.kicker')"
    :loading="loading"
    :error="error"
    :empty="!loading && !error && items.length === 0"
    :empty-title="$t('recycleBin.emptyTitle')"
    :empty-description="$t('recycleBin.emptyDesc')"
    :empty-icon="Trash2"
    empty-illustration="recycle"
    @retry="loadItems()"
  >
    <template #hero-meta>
      <div class="recycle-hero-note">{{ $t('recycleBin.note') }}</div>
      <div class="recycle-hero-chip-row">
        <span class="recycle-hero-chip">{{ activeTab === 'apis' ? $t('recycleBin.apisTab') : activeTab === 'scenes' ? $t('recycleBin.scenesTab') : $t('recycleBin.casesTab') }}{{ $t('recycleBin.categoryLabel') }}</span>
        <span class="recycle-hero-chip">{{ $t('recycleBin.retentionDays') }}</span>
        <span class="recycle-hero-chip">{{ $t('recycleBin.recoverFirst') }}</span>
      </div>
    </template>

    <template #hero-extra>
      <div class="recycle-hero-stats">
        <div class="recycle-hero-stat"><span class="recycle-hero-val">{{ items.length }}</span><span class="recycle-hero-lbl">{{ $t('recycleBin.currentItems') }}</span></div>
        <div class="recycle-hero-stat"><span class="recycle-hero-val">{{ tabs.find((tab) => tab.key === activeTab)?.count || 0 }}</span><span class="recycle-hero-lbl">{{ $t('recycleBin.currentCategory') }}</span></div>
      </div>
    </template>

    <template #filter>
      <div class="recycle-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="recycle-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }} <span v-if="tab.count">{{ tab.count }}</span>
        </button>
      </div>
    </template>

    <template #empty-action>
      <el-button size="small" @click="$router.push('/projects/' + projectId + '/scenes')">
        {{ $t('recycleBin.goToScenes') }}
      </el-button>
    </template>

    <div class="recycle-table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-name">{{ $t('recycleBin.nameHeader') }}</th>
            <th class="col-type">{{ $t('recycleBin.typeHeader') }}</th>
            <th class="col-date">{{ $t('recycleBin.deletedAtHeader') }}</th>
            <th class="col-actions">{{ $t('recycleBin.actionsHeader') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id + '-' + activeTab">
            <td class="col-name">{{ item.name }}</td>
            <td class="col-type">{{ typeLabel }}</td>
            <td class="col-date">{{ formatDate(item.deleted_at) }}</td>
            <td class="col-actions">
              <el-button size="small" type="primary" link :loading="restoring === item.id" :disabled="!!restoring || !!deleting" @click="restoreItem(item.id)">{{ $t('recycleBin.restore') }}</el-button>
              <el-button size="small" type="danger" link :loading="deleting === item.id" :disabled="!!restoring || !!deleting" @click="permanentDelete(item.id)">{{ $t('recycleBin.permanentDelete') }}</el-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRequireLogin } from '../composables/useRequireLogin'
import { useProjectPermission } from '../composables/useProjectPermission'
import request from '@/api/request'
import { ElMessageBox } from 'element-plus'
import { Trash2 } from 'lucide-vue-next'
import PageLayout from '../components/common/PageLayout.vue'
import { msgSuccess, msgError, msgWarning } from '@/utils/message'

const route = useRoute()
const { t: $t } = useI18n()
const { requireLogin } = useRequireLogin()
const { canViewRecycleBin } = useProjectPermission()
const projectId = computed(() => Number(route.params.id))

const tabs = ref([
  { key: 'apis', label: $t('recycleBin.apisTab'), count: 0 },
  { key: 'scenes', label: $t('recycleBin.scenesTab'), count: 0 },
  { key: 'cases', label: $t('recycleBin.casesTab'), count: 0 },
])
const activeTab = ref('apis')
const items = ref<{ id: number; name: string; deleted_at: string }[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const restoring = ref<number | null>(null)  // id of item being restored
const deleting = ref<number | null>(null)   // id of item being permanently deleted

const typeLabel = computed(() => {
  const map: Record<string, string> = { apis: $t('recycleBin.apisTab'), scenes: $t('recycleBin.scenesTab'), cases: $t('recycleBin.casesTab') }
  return map[activeTab.value] || ''
})

function formatDate(d: string) {
  if (!d) return '-'
  return d.replace('T', ' ').substring(0, 19)
}

async function loadItems() {
  loading.value = true
  try {
    const res = await request.get(`/projects/${projectId.value}/${activeTab.value}/recycle/list`)
    items.value = res.data.items || []
    // Update count
    const tab = tabs.value.find(t => t.key === activeTab.value)
    if (tab) tab.count = items.value.length
  } catch (e) {
    const err = e as { response?: { status?: number } }
    if (err?.response?.status !== 401) {
      error.value = $t('recycleBin.loadFailedMsg')
    }
    items.value = []
  } finally {
    loading.value = false
  }
}

async function restoreItem(id: number) {
  if (!(await requireLogin($t('recycleBin.restore')))) return
  restoring.value = id
  try {
    const res = await request.post(`/projects/${projectId.value}/${activeTab.value}/${id}/restore`)
    msgSuccess($t('recycleBin.restored'))
    // 检查恢复的项目父目录是否存在
    if (res.data?.parent_exists === false) {
      msgWarning($t('recycleBin.parentDeletedRestoredToRoot'))
    }
    void loadItems()
  } catch (e: unknown) {
    msgError($t('recycleBin.restoreFailed'))
  } finally {
    restoring.value = null
  }
}

async function permanentDelete(id: number) {
  if (!(await requireLogin($t('recycleBin.permanentDelete')))) return
  try {
    await ElMessageBox.confirm($t('recycleBin.permanentDeleteConfirm'), $t('recycleBin.cautionTitle'), {
      confirmButtonText: $t('recycleBin.confirmPermanentDelete'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
    })
    deleting.value = id
    await request.delete(`/projects/${projectId.value}/${activeTab.value}/${id}/permanent`)
    msgSuccess($t('recycleBin.permanentlyDeleted'))
    void loadItems()
  } catch (e: unknown) {
    // ElMessageBox 取消（'cancel'/'close'）不提示，仅 API 错误提示
    if (e !== 'cancel' && e !== 'close') {
      msgError($t('recycleBin.permanentDeleteFailed'))
    }
  }
  finally {
    deleting.value = null
  }
}

watch(activeTab, loadItems, { immediate: true })
</script>

<style scoped>
/* ===== 无权限页面 ===== */
.no-permission-wrap {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-16);
}
.no-permission-card {
  text-align: center;
  max-width: 400px;
}
.no-permission-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xl);
  background: var(--color-warning-alpha-10);
  color: var(--color-warning-500);
}
.no-permission-title {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}
.no-permission-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

/* ===== Hero 区域补充样式 ===== */
.recycle-hero-note {
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.recycle-hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.recycle-hero-chip {
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-full);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.recycle-hero-stats {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.recycle-hero-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 88px;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  transition: transform var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

.recycle-hero-stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.recycle-hero-val {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1;
}

.recycle-hero-lbl {
  margin-top: var(--space-1);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* ===== Tab 切换栏（filter slot 内） ===== */
.recycle-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
}

.recycle-tab {
  padding: var(--space-2) var(--space-4);
  border: none;
  background: transparent;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--duration-fast) var(--ease-smooth);
  font-family: inherit;
}

.recycle-tab:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.recycle-tab.active {
  color: var(--primary-600);
  border-bottom-color: var(--primary-500);
}

.recycle-tab:focus-visible {
  outline: var(--focus-ring-width) solid var(--primary-500);
  outline-offset: 2px;
}

.recycle-tab span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--space-4-5);
  height: var(--space-4-5);
  padding: 0 var(--space-1-5);
  font-size: var(--text-xs);
  background: var(--surface-nested);
  border-radius: var(--radius-full);
  margin-left: var(--space-1);
  border: 1px solid var(--border-subtle);
}

/* ===== 表格容器 ===== */
.recycle-table-card {
  width: 100%;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.recycle-table {
  width: 100%;
  border-collapse: collapse;
}

.recycle-table th {
  text-align: left;
  padding: var(--space-2-5) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  background: var(--surface-hover);
  border-bottom: 1px solid var(--border-default);
}

.recycle-table td {
  padding: var(--space-2-5) var(--space-4);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--border-default);
}

.recycle-table tbody tr {
  transition: background var(--duration-fast) var(--ease-smooth);
}

.recycle-table tbody tr:hover td {
  background: var(--surface-hover) !important;
}

.recycle-table tr:last-child td {
  border-bottom: none;
}

.col-name { min-width: 200px; }
.col-type { width: 80px; }
.col-date { width: 180px; color: var(--text-muted); font-family: var(--font-mono); }
.col-actions { width: 160px; text-align: right; }

.recycle-table .col-actions :deep(.el-button--danger) {
  color: var(--error) !important;
  font-weight: var(--weight-semibold);
}

.recycle-table .col-actions :deep(.el-button--danger:hover) {
  background: var(--color-error-alpha-08) !important;
}

/* ===== 暗色模式适配 ===== */
html.dark .recycle-table-card { background: var(--surface-card); border-color: var(--border-subtle); }
html.dark .recycle-item { background: var(--surface-card); border-color: var(--border-subtle); }
html.dark .recycle-item:hover { background: var(--surface-hover); }
html.dark .recycle-name { color: var(--text-primary); }
html.dark .recycle-meta { color: var(--text-muted); }

html.dark .recycle-tab {
  color: var(--text-muted);
}
html.dark .recycle-tab:hover {
  color: var(--text-secondary);
  background: var(--surface-hover);
}
html.dark .recycle-tab.active {
  color: var(--primary-400);
  border-bottom-color: var(--primary-400);
}
html.dark .recycle-tab span {
  background: var(--surface-nested);
  color: var(--text-primary);
}
html.dark .recycle-table th {
  background: var(--surface-nested);
  color: var(--text-muted);
  border-bottom-color: var(--border-default);
}
html.dark .recycle-table td {
  color: var(--text-secondary);
  border-bottom-color: var(--border-default);
}
html.dark .recycle-hint {
  color: var(--text-muted);
}

/* ===== RecycleBin 暗色模式补全 ===== */
html.dark .recycle-table-card {
  box-shadow: var(--shadow-card), 0 0 0 1px var(--color-white-alpha-04);
}
html.dark .recycle-table tbody tr:hover td {
  background: var(--surface-hover) !important;
  box-shadow: inset 2px 0 0 var(--primary-400);
}
html.dark .recycle-table .col-date {
  color: var(--text-muted);
}
html.dark .recycle-hero-val {
  color: var(--text-primary);
}
html.dark .recycle-hero-lbl {
  color: var(--text-muted);
}
html.dark .recycle-tabs {
  border-bottom-color: var(--border-subtle);
}
html.dark .recycle-tab:focus-visible {
  outline-color: var(--primary-400);
}
html.dark .page-desc {
  color: var(--text-secondary);
}

/* Tab 增强 */
:deep(.el-tabs__item) {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}
:deep(.el-tabs__active-bar) {
  height: 2px;
}

/* 页面说明文字增强 */
.page-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-1);
  line-height: var(--leading-normal);
}

/* ===== 响应式适配 ===== */
@media (max-width: 768px) {
  .recycle-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-2);
  }
  .recycle-toolbar .right-actions {
    justify-content: flex-end;
  }
}
@media (max-width: 480px) {
  .recycle-content {
    padding: var(--space-2);
  }
}


</style>
