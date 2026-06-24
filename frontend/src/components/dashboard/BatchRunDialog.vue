<template>
  <Teleport to="body">
    <div v-if="visible" class="batch-run-overlay" @click.self="$emit('update:visible', false)">
      <div class="batch-run-dialog">
        <div class="batch-run-header">
          <h3 class="batch-run-title">
            <Zap :size="16" class="batch-run-title-icon" />
            {{ $t('dashboard.batchRunTitle') }}
          </h3>
          <button class="batch-run-close" @click="$emit('update:visible', false)">&times;</button>
        </div>
        <div class="batch-run-body">
          <div class="batch-run-env-selector">
            <label class="batch-run-env-label">{{ $t('dashboard.execEnv') }}：</label>
            <select
              v-model="selectedEnvId"
              class="batch-run-env-select"
            >
              <option v-for="env in envList" :key="env.id" :value="env.id">{{ env.name }}</option>
            </select>
          </div>
          <p class="batch-run-hint">{{ $t('dashboard.selectScenes') }}</p>
          <label class="batch-run-select-all" @click.prevent="toggleAllScenes">
            <input type="checkbox" :checked="selectedSceneIds.size === sceneList.length" class="batch-run-checkbox" />
            <span>{{ $t('dashboard.selectAll') }}</span>
            <span class="batch-run-count">{{ selectedSceneIds.size }} / {{ sceneList.length }}</span>
          </label>
          <div class="batch-run-list">
            <label
              v-for="s in sceneList"
              :key="s.id"
              class="batch-run-item"
              :class="{ checked: selectedSceneIds.has(s.id) }"
            >
              <input
                type="checkbox"
                :checked="selectedSceneIds.has(s.id)"
                class="batch-run-checkbox"
                @change="toggleScene(s.id)"
              />
              <span class="batch-run-item-name">{{ s.name }}</span>
              <span class="batch-run-item-steps">{{ s.step_count || 0 }} {{ $t('dashboard.stepsUnit') }}</span>
            </label>
          </div>
        </div>
        <div class="batch-run-footer">
          <button class="batch-run-cancel" @click="$emit('update:visible', false)">{{ $t('dashboard.cancel') }}</button>
          <button
            class="batch-run-confirm"
            :disabled="selectedSceneIds.size === 0 || batchRunLoading"
            @click="executeBatchRun"
          >
            <Play :size="14" v-if="!batchRunLoading" />
            <span class="rerun-spinner" v-else></span>
            {{ $t('dashboard.executeCount', { count: selectedSceneIds.size }) }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Play, Zap } from 'lucide-vue-next'
import { listScenes, runScene } from '../../api/scenes'
import { msgSuccess, msgError, msgInfo } from '../../utils/message'
import type { TestScene } from '../../types'

const props = defineProps<{
  visible: boolean
  projectId: number
  envList: Array<{ id: number; name: string }>
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  execute: [payload: { count: number }]
}>()

const { t } = useI18n()

const selectedEnvId = ref<number | null>(null)
const sceneList = ref<TestScene[]>([])
const selectedSceneIds = ref<Set<number>>(new Set())
const batchRunLoading = ref(false)

watch(() => props.visible, async (val) => {
  if (val) {
    await loadScenes()
  }
})

async function loadScenes() {
  const pid = props.projectId
  if (!pid) return
  try {
    const res = await listScenes(pid, { page_size: 100 })
    sceneList.value = res.data.items || []
    selectedSceneIds.value = new Set(sceneList.value.map((s) => s.id))
    if (sceneList.value.length === 0) {
      msgInfo(t('dashboard.noScenesHint') || '暂无场景，请先创建场景')
      emit('update:visible', false)
      return
    }
    if (props.envList.length > 0 && !selectedEnvId.value) {
      selectedEnvId.value = props.envList[0]?.id ?? 0
    }
  } catch {
    msgError(t('dashboard.loadScenesFailed') || '加载场景列表失败')
    emit('update:visible', false)
  }
}

async function executeBatchRun() {
  const pid = props.projectId
  if (!pid || selectedSceneIds.value.size === 0) return
  if (!selectedEnvId.value) {
    msgError(t('dashboard.selectEnvFirst') || '请选择执行环境')
    return
  }
  batchRunLoading.value = true
  try {
    const promises = Array.from(selectedSceneIds.value).map(id =>
      runScene(pid, id, selectedEnvId.value!)
    )
    await Promise.allSettled(promises)
    const count = selectedSceneIds.value.size
    msgSuccess(t('dashboard.batchRunTriggered', { count }) || `已触发 ${count} 个场景执行`)
    emit('execute', { count })
    emit('update:visible', false)
  } finally {
    batchRunLoading.value = false
  }
}

function toggleScene(id: number) {
  const next = new Set(selectedSceneIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedSceneIds.value = next
}

function toggleAllScenes() {
  if (selectedSceneIds.value.size === sceneList.value.length) {
    selectedSceneIds.value = new Set()
  } else {
    selectedSceneIds.value = new Set(sceneList.value.map((s) => s.id))
  }
}
</script>
