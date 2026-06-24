<template>
  <div class="tree-panel">
    <div class="panel-head">
      <span class="panel-title">场景目录</span>
      <div v-if="canEdit" class="panel-actions">
        <el-tooltip content="新建目录" placement="top">
          <button class="icon-btn" aria-label="新建目录" @click="startNewCategory"><FolderPlus :size="14" /></button>
        </el-tooltip>
        <el-tooltip content="新建场景" placement="top">
          <button class="icon-btn" aria-label="新建场景" @click="createScene"><FilePlus :size="14" /></button>
        </el-tooltip>
        <el-tooltip content="刷新" placement="top">
          <button class="icon-btn" aria-label="刷新" @click="loadTree"><RefreshCw :size="14" /></button>
        </el-tooltip>
      </div>
      <div v-else class="panel-actions">
        <el-tooltip content="刷新" placement="top">
          <button class="icon-btn" aria-label="刷新" @click="loadTree"><RefreshCw :size="14" /></button>
        </el-tooltip>
      </div>
    </div>
    <div v-if="newCategoryInput" class="tree-inline-input">
      <el-input
        v-model="newCategoryName"
        size="small"
        placeholder="目录名称"
        aria-label="目录名称"
        ref="newCatInput"
        @keyup.enter="createCategory"
        @blur="cancelNewCategory"
        @keydown.esc="cancelNewCategoryForce"
      />
    </div>
    <div class="tree-scroll">
      <SkeletonCard :count="3" v-if="treeLoading" />
      <div v-else-if="categories.length === 0" class="tree-empty">
        <FolderOpen :size="32" class="tree-empty-icon" />
        <p>暂无目录</p>
        <button v-if="canEdit" class="btn-text" @click="startNewCategory">新建目录</button>
      </div>
      <div v-else class="tree-list">
        <div v-for="cat in categories" :key="cat.id" class="tree-folder">
          <div
            class="tree-folder-head"
            role="button"
            :aria-expanded="isExpanded(cat)"
            :aria-label="cat.name"
            @click.stop="toggleExpand(cat)"
            tabindex="0"
            @keydown.enter="toggleExpand(cat)"
            @contextmenu.prevent="showCatMenu($event, cat)"
          >
            <ChevronRight :size="13" class="tree-chevron" :class="{ rotated: isExpanded(cat) }" />
            <FolderOpen :size="14" class="tree-folder-icon" v-if="isExpanded(cat)" />
            <Folder :size="14" class="tree-folder-icon" v-else />
            <span class="tree-folder-name">{{ cat.name }}</span>
            <span class="tree-badge" v-if="cat.scenes.length > 0">{{ cat.scenes.length }}</span>
          </div>
          <div v-show="isExpanded(cat)" class="tree-children">
            <div
              v-for="s in cat.scenes"
              :key="s.id"
              class="tree-scene"
              role="treeitem"
              :aria-selected="selectedSceneId === s.id"
              :aria-label="s.name"
              tabindex="0"
              :class="{ selected: selectedSceneId === s.id }"
              @click.stop="selectScene(s)"
              @keydown.enter="selectScene(s)"
              @contextmenu.prevent="showSceneMenu($event, s, cat)"
            >
              <FileText :size="13" class="tree-scene-icon" />
              <span class="tree-scene-name">{{ s.name }}</span>
              <button v-if="canEdit" class="tree-scene-delete" @click.stop="deleteScene(s)" title="删除场景" aria-label="删除场景">
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="tree-footer">
      <span class="tree-stats">{{ treeStats }}</span>
    </div>
    <!-- 目录右键菜单 -->
    <TreeContextMenu
      :visible="catMenu.visible"
      :x="catMenu.x"
      :y="catMenu.y"
      :items="catMenuItems"
      @close="closeCatMenu"
    />
    <!-- 场景右键菜单 -->
    <TreeContextMenu
      :visible="sceneMenu.visible"
      :x="sceneMenu.x"
      :y="sceneMenu.y"
      :items="sceneMenuItems"
      @close="closeSceneMenu"
    />
    <!-- 重命名弹窗 -->
    <RenameDialog
      v-model="renameDialog.visible"
      :title="renameDialog.title"
      :placeholder="renameDialog.placeholder"
      :default-value="renameDialog.value"
      @confirm="onRenameConfirm"
      @cancel="renameDialog.visible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue"
import { ElMessageBox } from "element-plus"
import { MSG } from "../constants/messages"
import { msgSuccess, msgError } from "../utils/message"
import { logger } from "../utils/logger"
import request from "../api/request"
import SkeletonCard from "../components/SkeletonCard.vue"
import {
  FolderOpen,
  FolderPlus,
  FilePlus,
  RefreshCw,
  ChevronRight,
  FileText,
  Folder,
  Edit,
  Trash2,
  Plus,
  Copy,
} from "lucide-vue-next"
import TreeContextMenu from "./tree/TreeContextMenu.vue"
import RenameDialog from "./RenameDialog.vue"
import { useRequireLogin } from "../composables/useRequireLogin"

const props = defineProps<{
  projectId: number
  selectedSceneId: number | null
  canEdit?: boolean
}>()

interface SceneItem {
  id: number
  name: string
  category_id?: number
  description?: string
}

interface CategoryItem {
  id: number
  name: string
  scenes: SceneItem[]
  _expanded?: boolean
}

const emit = defineEmits<{
  (e: "select-scene", scene: SceneItem): void
  (e: "scene-created", sceneId: number): void
  (e: "scene-deleted", sceneId: number): void
}>()

const { requireLogin } = useRequireLogin()

// ===== 目录树状态 =====
const categories = ref<CategoryItem[]>([])
const treeLoading = ref(false)
const newCategoryInput = ref(false)
const newCategoryName = ref("")
const newCatInput = ref<{ focus: () => void } | null>(null)

// 本地展开状态追踪
const expandedIds = ref(new Set<number>())

function toggleExpand(cat: CategoryItem) {
  const newSet = new Set(expandedIds.value)
  if (newSet.has(cat.id)) {
    newSet.delete(cat.id)
  } else {
    newSet.add(cat.id)
  }
  expandedIds.value = newSet
}

function isExpanded(cat: CategoryItem): boolean {
  return expandedIds.value.has(cat.id)
}

// 右键菜单状态
const catMenu = ref<{ visible: boolean; x: number; y: number; cat: CategoryItem | null }>({
  visible: false,
  x: 0,
  y: 0,
  cat: null,
})
const sceneMenu = ref<{ visible: boolean; x: number; y: number; scene: SceneItem | null; cat: CategoryItem | null }>({
  visible: false,
  x: 0,
  y: 0,
  scene: null,
  cat: null,
})
const renameDialog = ref<{
  visible: boolean
  title: string
  placeholder: string
  value: string
  type: string
  target: CategoryItem | SceneItem | null
}>({ visible: false, title: "", placeholder: "", value: "", type: "", target: null })

// 目录右键菜单
interface ContextMenuItem {
  label?: string
  icon?: object
  action?: () => void | Promise<void>
  divider?: boolean
  danger?: boolean
}

const catMenuItems = computed<ContextMenuItem[]>(() => {
  if (!props.canEdit) return []
  return [
    { label: "重命名", icon: Edit, action: () => startRenameCat(catMenu.value.cat) },
    { label: "新建场景", icon: Plus, action: () => createSceneInCat(catMenu.value.cat) },
    { divider: true },
    {
      label: "删除目录",
      icon: Trash2,
      danger: true,
      action: () => deleteCategory(catMenu.value.cat),
    },
  ]
})

const sceneMenuItems = computed<ContextMenuItem[]>(() => {
  if (!props.canEdit) return []
  return [
    { label: "重命名", icon: Edit, action: () => startRenameScene(sceneMenu.value.scene) },
    { label: "复制场景", icon: Copy, action: () => duplicateScene(sceneMenu.value.scene) },
    { divider: true },
    {
      label: "删除场景",
      icon: Trash2,
      danger: true,
      action: () => deleteScene(sceneMenu.value.scene),
    },
  ]
})

function showCatMenu(e: MouseEvent, cat: CategoryItem) {
  sceneMenu.value.visible = false
  catMenu.value = { visible: true, x: e.clientX, y: e.clientY, cat }
}
function closeCatMenu() {
  catMenu.value.visible = false
}

function showSceneMenu(e: MouseEvent, scene: SceneItem, cat: CategoryItem) {
  catMenu.value.visible = false
  sceneMenu.value = { visible: true, x: e.clientX, y: e.clientY, scene, cat }
}
function closeSceneMenu() {
  sceneMenu.value.visible = false
}

function startRenameCat(cat: CategoryItem | null) {
  if (!cat) return
  renameDialog.value = {
    visible: true,
    title: "重命名目录",
    placeholder: "目录名称",
    value: cat.name,
    type: "cat",
    target: cat,
  }
}

async function createSceneInCat(cat: CategoryItem) {
  if (!await requireLogin("新建场景")) return
  const res = await request.post<unknown, { data: SceneItem }>(`/projects/${props.projectId}/scenes`, {
    name: "新场景",
    category_id: cat.id,
    steps: [],
    edges: [],
  })
  msgSuccess("场景已创建")
  emit("scene-created", res.data.id)
  await loadTree()
}

function startRenameScene(scene: SceneItem | null) {
  if (!scene) return
  renameDialog.value = {
    visible: true,
    title: "重命名场景",
    placeholder: "场景名称",
    value: scene.name,
    type: "scene",
    target: scene,
  }
}

async function duplicateScene(scene: SceneItem) {
  if (!await requireLogin("复制场景")) return
  const res = await request.post<unknown, { data?: SceneItem }>(`/projects/${props.projectId}/scenes/${scene.id}/duplicate`)
  msgSuccess("场景已复制")
  await loadTree()
  if (res.data?.id) emit("scene-created", res.data.id)
}

async function onRenameConfirm(name: string) {
  const rd = renameDialog.value
  if (!name || name === rd.value) return
  if (rd.type === "cat") {
    if (!await requireLogin("重命名目录")) return
    await request.put(`/projects/${props.projectId}/scene-categories/${rd.target.id}`, { name })
    msgSuccess("目录已重命名")
  } else if (rd.type === "scene") {
    if (!await requireLogin("重命名场景")) return
    await request.put(`/projects/${props.projectId}/scenes/${rd.target.id}`, { name })
    msgSuccess("场景已重命名")
  }
  await loadTree()
}

const treeStats = computed(() => {
  const total = categories.value.reduce((sum: number, c: CategoryItem) => sum + (c.scenes?.length || 0), 0)
  return `共 ${total} 个场景`
})

async function loadTree() {
  treeLoading.value = true
  try {
    const res = await request.get<unknown, { data: CategoryItem[] }>(`/projects/${props.projectId}/scene-categories`)
    categories.value = (res.data || []).map((c: CategoryItem) => ({
      ...c,
    }))
    // 初始化展开状态
    expandedIds.value = new Set(categories.value.map(c => c.id))
    // 没有选中场景时，自动选中第一个有场景的接口目录下的第一个场景
    if (!props.selectedSceneId) {
      for (const cat of categories.value) {
        if (cat.scenes && cat.scenes.length > 0) {
          selectScene(cat.scenes[0])
          break
        }
      }
    }
  } finally {
    treeLoading.value = false
  }
}

function startNewCategory() {
  newCategoryName.value = ""
  newCategoryInput.value = true
  void nextTick(() => newCatInput.value?.focus())
}

function cancelNewCategory() {
  newCategoryInput.value = false
  newCategoryName.value = ""
}

function cancelNewCategoryForce() {
  newCategoryInput.value = false
  newCategoryName.value = ""
}

async function createCategory() {
  if (!await requireLogin("新建目录")) return
  try {
    if (!newCategoryName.value.trim()) return
    await request.post(`/projects/${props.projectId}/scene-categories`, {
      name: newCategoryName.value.trim(),
    })
    newCategoryInput.value = false
    newCategoryName.value = ""
    msgSuccess("目录已创建")
    await loadTree()
  } catch (err) {
    logger.error('[SceneTree] create category failed:', err)
    msgError('创建目录失败')
    /* 由 request 拦截器处理 */
  }
}

async function deleteCategory(cat: CategoryItem) {
  if (cat.id === 0) return
  if (!await requireLogin("删除目录")) return
  try {
    await ElMessageBox.confirm(MSG.DELETE_CATEGORY_CONFIRM(cat.name), "确认", { type: "warning" })
    await request.delete(`/projects/${props.projectId}/scene-categories/${cat.id}`)
    msgSuccess("目录已删除")
    await loadTree()
  } catch (err) {
    logger.error('[SceneTree] delete category failed:', err)
    msgError('删除目录失败')
    /* cancel */
  }
}

async function createScene() {
  if (!await requireLogin("新建场景")) return
  const res = await request.post<unknown, { data: { id: number } }>(`/projects/${props.projectId}/scenes`, {
    name: "新场景",
    steps: [],
    edges: [],
  })
  msgSuccess(MSG.CREATE_SCENE)
  emit("scene-created", res.data.id)
  await loadTree()
}

async function deleteScene(s: SceneItem) {
  if (!await requireLogin("删除场景")) return
  try {
    await ElMessageBox.confirm(MSG.DELETE_SCENE_CONFIRM(s.name), "确认", { type: "warning" })
    await request.delete(`/projects/${props.projectId}/scenes/${s.id}`)
    emit("scene-deleted", s.id)
    msgSuccess(MSG.DELETE_SUCCESS)
    await loadTree()
  } catch (err) {
    logger.error('[SceneTree] delete scene failed:', err)
    msgError('删除场景失败')
    /* cancel */
  }
}

function selectScene(s: SceneItem) {
  if (props.selectedSceneId === s.id) return
  emit("select-scene", s)
}

defineExpose({ createScene, categories, loadTree })

onMounted(() => {
  void loadTree()
  // 点击空白处关闭所有右键菜单
  document.addEventListener("click", closeAllMenus)
})

onUnmounted(() => {
  document.removeEventListener("click", closeAllMenus)
})

function closeAllMenus() {
  catMenu.value.visible = false
  sceneMenu.value.visible = false
}
</script>

<style scoped>
/* ===== 树面板容器 ===== */
.tree-panel {
  width: var(--width-sidebar);
  min-width: var(--width-sidebar);
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border-right: 1px solid var(--border-subtle);
  position: relative;
  z-index: var(--z-base);
}

/* ===== 面板头部 ===== */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  min-height: var(--height-header);
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  letter-spacing: var(--tracking-tight);
}

.panel-actions {
  display: flex;
  gap: var(--space-1);
  align-items: center;
}

/* ===== 树滚动区域 ===== */
.tree-scroll {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}
.tree-scroll::-webkit-scrollbar {
  width: 4px;
}
.tree-scroll::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}
.tree-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}
.tree-scroll::-webkit-scrollbar-thumb:active {
  background: var(--scrollbar-thumb-active);
}
.tree-scroll::-webkit-scrollbar-track {
  background: transparent;
}

/* ===== 空状态 ===== */
.tree-empty {
  padding: var(--space-10) var(--space-4);
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.tree-empty-icon {
  opacity: 0.45;
  color: var(--text-secondary);
  width: var(--size-icon-lg);
  height: var(--size-icon-lg);
}

/* ===== 行内输入框 ===== */
.tree-inline-input {
  padding: var(--space-2) var(--space-3);
}

/* ===== 目录节点 ===== */
.tree-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.tree-folder {
  /* 目录容器基本样式由子元素撑开 */
}

/* 目录头部 - 8px 间距规范 */
.tree-folder-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
  user-select: none;
  border-radius: var(--radius-md);
  margin: 0 var(--space-1);
  transition: var(--transition-fast);
  position: relative;
}

.tree-folder-head:hover {
  background: var(--surface-hover);
}

.tree-folder-head:hover .tree-folder-icon {
  color: var(--primary-500);
  opacity: 1;
}

/* 展开/折叠箭头 - 动画优化 */
.tree-chevron {
  transition: transform var(--duration-base) var(--ease-spring);
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
}

.tree-chevron.rotated {
  transform: rotate(90deg);
}

/* 目录图标 - 大小和颜色优化 */
.tree-folder-icon {
  color: var(--color-warning);
  flex-shrink: 0;
  opacity: 0.75;
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
  transition: var(--transition-fast);
}

.tree-folder-head:hover .tree-folder-icon {
  opacity: 1;
  transform: scale(1.05);
}

/* 目录名称 */
.tree-folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: var(--weight-medium);
}

/* 场景计数徽章 */
.tree-badge {
  font-size: var(--text-2xs);
  color: var(--primary-600);
  background: var(--color-primary-alpha-12);
  padding: 0 var(--space-2);
  border-radius: var(--radius-full);
  font-weight: var(--weight-semibold);
  min-width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.tree-folder-head:hover .tree-badge {
  background: var(--color-primary-alpha-20);
  transform: scale(1.05);
}

/* ===== 子节点容器 - 展开动画 ===== */
.tree-children {
  padding-left: var(--space-4);
  animation: tree-expand var(--duration-base) var(--ease-out);
}

@keyframes tree-expand {
  from {
    opacity: 0;
    transform: translateY(-4px);
    max-height: 0;
  }
  to {
    opacity: 1;
    transform: translateY(0);
    max-height: 800px;
  }
}

/* ===== 场景节点 - 8px 间距规范 ===== */
.tree-scene {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-7);
  cursor: pointer;
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
  margin: var(--space-0-5) var(--space-1);
  transition: var(--transition-fast);
  position: relative;
  min-height: var(--height-row-compact);
}

.tree-scene:hover {
  background: var(--surface-hover);
  transform: translateX(2px);
}

.tree-scene:hover .tree-scene-icon {
  color: var(--primary-500);
  opacity: 1;
}

.tree-scene:active {
  transform: translateX(0);
}

/* 场景选中状态 - 左侧 accent bar */
.tree-scene.selected {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  box-shadow: inset 3px 0 0 var(--primary-500);
}

.tree-scene.selected .tree-scene-name {
  font-weight: var(--weight-semibold);
  color: var(--primary-600);
}

.tree-scene.selected .tree-scene-icon {
  color: var(--primary-500);
  opacity: 1;
}

/* 场景图标 */
.tree-scene-icon {
  flex-shrink: 0;
  color: var(--primary-400);
  opacity: 0.75;
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
  transition: var(--transition-fast);
}

/* 场景名称 */
.tree-scene-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  transition: var(--transition-fast);
}

/* 场景删除按钮 - hover时显示 */
.tree-scene-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: var(--transition-fast);
  flex-shrink: 0;
  padding: 0;
}

.tree-scene:hover .tree-scene-delete {
  opacity: 1;
}

/* 键盘聚焦时也显示删除按钮（a11y） */
.tree-scene-delete:focus-visible {
  opacity: 1;
}

.tree-scene:focus-within .tree-scene-delete {
  opacity: 1;
}

.tree-scene-delete:hover {
  background: var(--color-error-alpha-12, rgba(217, 92, 92, 0.12));
  color: var(--color-error, #d95c5c);
}

/* ===== 图标按钮 ===== */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--height-row-compact);
  height: var(--height-row-compact);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.icon-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  transform: scale(1.05);
}

.icon-btn:active {
  transform: scale(var(--press-scale));
  background: var(--surface-selected);
}

/* ===== 文本按钮 ===== */
.btn-text {
  background: none;
  border: none;
  color: var(--primary-600);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}

.btn-text:hover {
  background: var(--color-primary-alpha-06);
  color: var(--primary-700);
}

/* ===== 树底部统计 ===== */
.tree-footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.tree-stats {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

/* ===== 暗色模式适配 ===== */
html.dark .tree-panel {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .panel-head {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .panel-title {
  color: var(--text-primary);
}

html.dark .tree-folder-head:hover {
  background: var(--surface-hover);
}

html.dark .tree-folder-name {
  color: var(--text-primary);
}

html.dark .tree-scene:hover {
  background: var(--surface-hover);
}

html.dark .tree-scene.selected {
  background: var(--color-primary-alpha-12);
  color: var(--primary-400);
  box-shadow: inset 3px 0 0 var(--primary-400);
}

html.dark .tree-scene.selected .tree-scene-name {
  color: var(--primary-400);
}

html.dark .tree-scene-name {
  color: var(--text-primary);
}

html.dark .tree-badge {
  background: var(--color-primary-alpha-16);
  color: var(--primary-400);
}

html.dark .tree-stats {
  color: var(--text-muted);
}

/* ===== 兼容性暗色覆盖（保留原有类名） ===== */
html.dark .scene-tree {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .scene-tree-header {
  background: var(--surface-hover);
  border-color: var(--border-subtle);
}

html.dark .scene-tree-search {
  background: var(--surface-input);
  border-color: var(--border-default);
  color: var(--text-primary);
}

html.dark .scene-tree-search::placeholder {
  color: var(--text-muted);
}

html.dark .tree-node {
  color: var(--text-secondary);
}

html.dark .tree-node:hover {
  background: var(--surface-hover);
}

html.dark .tree-node.active {
  background: var(--surface-selected);
  color: var(--primary-400);
}

html.dark .tree-node-count {
  background: var(--surface-hover);
  color: var(--text-muted);
}

html.dark .tree-group-label {
  color: var(--text-muted);
}

html.dark .scene-tree-empty {
  color: var(--text-muted);
}
</style>
