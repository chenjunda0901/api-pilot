// frontend/src/composables/useStepEditor.ts
import { ref, computed, watch, type Ref } from 'vue'
import { msgWarning } from '../utils/message'

interface ExtractVar {
  variable: string
  path: string
  source: string
  header_name: string
  description: string
}

interface Step {
  id?: number
  _key?: string
  method: string
  label: string
  enabled: boolean
  path: string
  node_type: string
  query_params: { value: string; [key: string]: unknown }[]
  headers: { value: string; [key: string]: unknown }[]
  request_body: string
  assertions: unknown[]
  extract_vars: ExtractVar[]
  extract_count?: number
  condition_expression?: string
  wait_duration?: number
  depends_on_step_id?: number | null
  loop_count?: number | null
  loop_variable?: string
  wait_mode?: string
  wait_min?: number | null
  wait_max?: number | null
  name?: string
  [key: string]: unknown
}

interface Scene {
  id?: number
  name?: string
  [key: string]: unknown
}

interface EnvironmentService {
  is_base?: boolean
  url?: string
  [key: string]: unknown
}

interface EnvRef {
  id: number
  services?: EnvironmentService[]
  [key: string]: unknown
}

interface BodyModel {
  type: string
  content: string
}

interface DataFlowStep {
  index: number
  label: string
  method: string
  referencedVars: string[]
  extractedVars: string[]
}

export interface StepEditorOptions {
  steps: Ref<Step[]>
  selectedScene: Ref<Scene | null>
  editingName: Ref<string>
  envId: Ref<number | null>
  envs: Ref<EnvRef[]>
  runScene: (scene: Scene) => void
  runSceneStress: (scene: Scene) => void
}

export function useStepEditor(options: StepEditorOptions) {
  const { steps, selectedScene, editingName, envId, envs, runScene, runSceneStress } = options

  // ===== 步骤选择 =====
  const selectedStepKey = ref<string | null>(null)
  const selectedStep = ref<Step | null>(null)
  const stepDetailTab = ref('params')
  const showStepDetail = ref(false)

  // 参考 ApiDetail.detectDefaultTab：自动跳转到第一个有内容的 tab
  function detectStepDefaultTab(step: Step | null): string {
    if (!step) return 'params'
    if (step.request_body) return 'body'
    if (step.query_params && step.query_params.length > 0) return 'params'
    if (step.headers && step.headers.length > 0) return 'headers'
    if (step.assertions && step.assertions.length > 0) return 'assertions'
    if (step.extract_vars && step.extract_vars.length > 0) return 'extract'
    return 'params'
  }

  function selectStep(step: Step) {
    const key = step.id || step._key
    selectedStepKey.value = key as string
    selectedStep.value = step
    stepDetailTab.value = detectStepDefaultTab(step)
    showStepDetail.value = true
  }

  const currentStepIndex = computed(() => {
    if (!selectedStep.value) return -1
    return steps.value.findIndex(
      (s: Step) => s.id === selectedStep.value!.id || s._key === selectedStep.value!._key
    )
  })

  const stepBreadcrumb = computed(() => {
    const idx = currentStepIndex.value
    if (idx < 0) return ''
    const sceneName = editingName.value || (selectedScene.value && selectedScene.value.name) || ''
    return `${sceneName} · 步骤 ${idx + 1}/${steps.value.length}`
  })

  const hasPrevStep = computed(() => currentStepIndex.value > 0)
  const hasNextStep = computed(
    () => currentStepIndex.value >= 0 && currentStepIndex.value < steps.value.length - 1
  )

  function goToPrevStep() {
    if (!hasPrevStep.value) return
    selectStep(steps.value[currentStepIndex.value - 1])
  }

  function goToNextStep() {
    if (!hasNextStep.value) return
    selectStep(steps.value[currentStepIndex.value + 1])
  }

  function onRunCommand(cmd: string) {
    if (!selectedScene.value) return
    if (cmd === 'failed-only') {
      msgWarning('此功能需要上次执行记录，暂执行全部运行')
      runScene(selectedScene.value)
    } else if (cmd === 'stress') {
      runSceneStress(selectedScene.value)
    }
  }

  function onStepDetailClosed() {
    // 保持步骤高亮，不取消选中
  }

  const _dirty = ref(false)
  function markDirty() { _dirty.value = true }

  function stepAction(cmd: string, step: Step, index: number) {
    if (cmd === 'disable') {
      step.enabled = !step.enabled
    } else if (cmd === 'delete') {
      const idx = steps.value.indexOf(step)
      if (idx >= 0) {
        steps.value.splice(idx, 1)
        if (selectedStep.value === step) {
          selectedStepKey.value = null
          selectedStep.value = null
        }
      }
    } else if (cmd === 'insert_above') {
      steps.value.splice(index, 0, createEmptyStep())
    } else if (cmd === 'insert_condition') {
      steps.value.splice(index + 1, 0, createEmptyStep({ node_type: 'condition', condition_expression: 'true', method: '', path: '', label: '条件判断' }))
    } else if (cmd === 'insert_wait') {
      steps.value.splice(index + 1, 0, createEmptyStep({ node_type: 'wait', wait_duration: 500, method: '', path: '', label: '等待' }))
    }
  }

  function createEmptyStep(extra: Partial<Step> = {}): Step {
    return {
      method: 'GET',
      label: '新步骤',
      enabled: true,
      path: '',
      node_type: 'request',
      query_params: [],
      headers: [],
      request_body: '',
      assertions: [],
      extract_vars: [],
      _key: `step_new_${Date.now()}`,
      ...extra,
    }
  }

  function onSortUpdate(newSteps: Step[]) {
    steps.value = newSteps
  }

  function onDragEnd() { markDirty() }

  // ===== 当前环境域名（跟随右侧面板的环境选择） =====
  const selectedServiceUrlInEnv = ref<string | null>(null)

  const currentServiceUrl = computed(() => {
    if (!envId.value) return ''
    if (selectedServiceUrlInEnv.value) return selectedServiceUrlInEnv.value
    const env = envs.value.find((e: EnvRef) => e.id === envId.value)
    if (!env?.services?.length) return ''
    const svc = env.services.find((s: EnvironmentService) => s.is_base) || env.services[0]
    return svc?.url || ''
  })

  const currentEnvServices = computed(() => {
    if (!envId.value) return []
    const env = envs.value.find((e: EnvRef) => e.id === envId.value)
    return env?.services || []
  })

  function switchEnvService(url: string) {
    selectedServiceUrlInEnv.value = url
  }

  function displayUrlVar(val: string) {
    return `{{ ${val} }}`
  }

  // envId 切换时重置手动选择的服务 URL
  watch(envId, () => {
    selectedServiceUrlInEnv.value = null
  })

  // ===== URL 变量高亮 + 点击编辑 =====
  const editingUrl = ref(false)

  const stepUrlSegments = computed(() => {
    const path = (selectedStep.value && selectedStep.value.path) || ''
    const segments: { type: string; value: string }[] = []
    const regex = /\{\{[^}]+\}\}/g
    let lastIndex = 0
    let match: RegExpExecArray | null
    while ((match = regex.exec(path)) !== null) {
      if (match.index > lastIndex) {
        segments.push({ type: 'text', value: path.slice(lastIndex, match.index) })
      }
      segments.push({ type: 'variable', value: match[0].slice(2, -2) })
      lastIndex = match.index + match[0].length
    }
    if (lastIndex < path.length) {
      segments.push({ type: 'text', value: path.slice(lastIndex) })
    }
    return segments
  })

    // ===== 提取变量重名检测 =====
  const duplicateVariables = computed(() => {
    if (!selectedStep.value) return []
    const names = selectedStep.value.extract_vars
      .map((e: ExtractVar) => e.variable)
      .filter((v: string) => v)
    const seen = new Set<string>()
    const duplicates: string[] = []
    for (const name of names) {
      if (seen.has(name)) duplicates.push(name)
      seen.add(name)
    }
    return duplicates
  })

  function checkDuplicateVariable(variableName: string, currentIndex: number): boolean {
    if (!variableName || !selectedStep.value || !selectedStep.value.extract_vars) return false
    return selectedStep.value.extract_vars.some(
      (e: ExtractVar, i: number) => i !== currentIndex && e.variable === variableName
    )
  }

  // ===== 步骤被下游引用计数 =====
  const stepReferenceCounts = computed(() => {
    const extractMap = new Map<number, string[]>()
    steps.value.forEach((step: Step, i: number) => {
      const vars = (step.extract_vars || []).map((e: ExtractVar) => e.variable).filter(Boolean)
      if (vars.length > 0) extractMap.set(i, vars)
    })
    const counts = new Map<number, number>()
    extractMap.forEach((extractedVars, extractIdx) => {
      let refCount = 0
      steps.value.forEach((step: Step, checkIdx: number) => {
        if (checkIdx <= extractIdx) return
        const allText = [
          step.path,
          step.request_body,
          ...step.query_params.map((p: { value: string }) => p.value),
          ...step.headers.map((h: { value: string }) => h.value),
        ].join(' ')
        for (const v of extractedVars) {
          if (allText.includes(`{{${v}}}`) || allText.includes(`{{ ${v} }}`)) {
            refCount++
            break
          }
        }
      })
      if (refCount > 0) counts.set(extractIdx, refCount)
    })
    return counts
  })

  // ===== 数据流视图 =====
  const showDataFlowView = ref(false)

  function extractVariablesFromText(text: string): string[] {
    if (!text) return []
    const regex = /\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/g
    const vars: string[] = []
    let match: RegExpExecArray | null
    while ((match = regex.exec(text)) !== null) {
      vars.push(match[1])
    }
    return vars
  }

  const dataFlowSteps = computed(() => {
    if (!showDataFlowView.value || steps.value.length === 0) return []

    return steps.value.map((step: Step, index: number): DataFlowStep => {
      const referencedVars: string[] = []

      referencedVars.push(...extractVariablesFromText(step.path || ''))

      for (const p of step.query_params || []) {
        referencedVars.push(...extractVariablesFromText(p.value || ''))
      }

      for (const h of step.headers || []) {
        referencedVars.push(...extractVariablesFromText(h.value || ''))
      }

      referencedVars.push(...extractVariablesFromText(step.request_body || ''))

      return {
        index,
        label: step.label || step.name || `步骤 ${index + 1}`,
        method: step.method || 'GET',
        referencedVars: [...new Set(referencedVars)],
        extractedVars: (step.extract_vars || []).map((e: ExtractVar) => e.variable),
      }
    })
  })

  // ===== 步骤 Body：适配 BodyEditor 的 {type, content} 格式 ↔ 步骤的 request_body 字符串 =====
  const stepBodyModel = computed({
    get: (): BodyModel => {
      const str = (selectedStep.value && selectedStep.value.request_body) || ''
      if (!str || str === '{}') return { type: 'none', content: '' }
      try {
        JSON.parse(str)
        return { type: 'json', content: str }
      } catch {
        return { type: 'text', content: str }
      }
    },
    set: (val: BodyModel) => {
      if (!selectedStep.value) return
      if (!val || val.type === 'none') {
        selectedStep.value.request_body = ''
      } else {
        selectedStep.value.request_body = val.content || ''
      }
    },
  })

  // ===== 步骤详情 Tab 配置 =====
  const stepDetailTabs = computed(() => [
    {
      key: 'params',
      label: 'Params',
      count: (selectedStep.value && selectedStep.value.query_params && selectedStep.value.query_params.length) || 0,
    },
    {
      key: 'body',
      label: 'Body',
      count: selectedStep.value && selectedStep.value.request_body ? 1 : 0,
    },
    {
      key: 'headers',
      label: 'Headers',
      count: (selectedStep.value && selectedStep.value.headers && selectedStep.value.headers.length) || 0,
    },
    {
      key: 'assertions',
      label: '断言',
      count: (selectedStep.value && selectedStep.value.assertions && selectedStep.value.assertions.length) || 0,
    },
    {
      key: 'extract',
      label: '提取变量',
      count: (selectedStep.value && selectedStep.value.extract_vars && selectedStep.value.extract_vars.length) || 0,
    },
    { key: 'more', label: '更多', count: 0 },
  ])

  function removeExtract(i: number) {
    const step = selectedStep.value
    if (!step || !step.extract_vars) return
    step.extract_vars.splice(i, 1)
    step.extract_count = step.extract_vars.length
  }

  function addExtract() {
    if (!selectedStep.value) return
    if (!Array.isArray(selectedStep.value.extract_vars)) selectedStep.value.extract_vars = []
    selectedStep.value.extract_vars.push({
      variable: '',
      path: '',
      source: 'body',
      header_name: '',
      description: '',
    })
    selectedStep.value.extract_count = selectedStep.value.extract_vars.length
  }

  function methodTagType(m: string) {
    const methodMap: Record<string, string> = {
      GET: 'success',
      POST: 'primary',
      PUT: 'warning',
      DELETE: 'danger',
    }
    return methodMap[m] || 'info'
  }

  return {
    // 步骤选择
    selectedStepKey,
    selectedStep,
    stepDetailTab,
    showStepDetail,
    selectStep,
    detectStepDefaultTab,
    // 步骤导航
    currentStepIndex,
    stepBreadcrumb,
    hasPrevStep,
    hasNextStep,
    goToPrevStep,
    goToNextStep,
    // 步骤命令
    onRunCommand,
    onStepDetailClosed,
    markDirty,
    dirty: _dirty,
    stepAction,
    createEmptyStep,
    onSortUpdate,
    onDragEnd,
    // 环境服务
    selectedServiceUrlInEnv,
    currentServiceUrl,
    currentEnvServices,
    switchEnvService,
    displayUrlVar,
    // URL 编辑
    editingUrl,
    stepUrlSegments,
    // 变量检测
    duplicateVariables,
    checkDuplicateVariable,
    stepReferenceCounts,
    // 数据流
    showDataFlowView,
    dataFlowSteps,
    // Body 模型
    stepBodyModel,
    stepDetailTabs,
    // 提取操作
    removeExtract,
    addExtract,
    methodTagType,
  }
}
