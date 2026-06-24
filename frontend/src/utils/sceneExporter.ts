/**
 * 场景导入/导出工具
 * 支持 JSON 格式的场景序列化与反序列化
 */

export interface ExportedScene {
  version: string
  exported_at: string
  scene: {
    name: string
    steps: Array<{
      name: string
      type: string
      api_id?: number | null
      enabled: boolean
      loop_count: number | null
      condition: string
      depends_on_step_id: number | null
      timeout: number
      retry_count: number
      failure_strategy: string
      assert_mode: string
      overrides?: { params: unknown[]; headers: unknown[] }
      assertions: unknown[]
      extract_vars: unknown[]
      wait_duration?: number | null
    }>
    edges: Array<{
      edge_id: string
      source_node_id: string
      target_node_id: string
      source_handle?: string | null
      label?: string
    }>
    variables: Record<string, string>
    config: {
      concurrency: number
      retry_count: number
      cookie_sharing: boolean
      random_range: number
    }
  }
}

export interface SceneExportData {
  name: string
  steps: Array<{
    _key: string
    id?: number
    label: string
    method?: string
    path: string
    node_type: string
    enabled: boolean
    loop_count?: number | null
    condition_expression?: string
    depends_on_step_id?: number | null
    wait_duration?: number | null
    headers: unknown[]
    query_params: unknown[]
    assertions: unknown[]
    extract_vars: unknown[]
  }>
  edges?: Array<{
    edge_id: string
    source_node_id: string
    target_node_id: string
    source_handle?: string | null
    label?: string
  }>
  config?: {
    concurrency?: number
    thread_count?: number
    on_failure?: string
    env_id?: number | null
    global_cookie?: boolean | number
    step_delay?: number
    step_delay_random?: boolean | number
    step_delay_min?: number
    step_delay_max?: number
  }
}

export function exportSceneToJson(sceneData: SceneExportData): string {
  const exported: ExportedScene = {
    version: '1.0',
    exported_at: new Date().toISOString(),
    scene: {
      name: sceneData.name || '未命名场景',
      steps: (sceneData.steps || []).map((step) => ({
        name: step.label || '未命名步骤',
        type: step.node_type === 'wait' ? 'wait' : 'http',
        api_id: step.api_id ?? null,
        enabled: step.enabled ?? true,
        loop_count: step.loop_count ?? 1,
        condition: step.condition_expression || '',
        depends_on_step_id: step.depends_on_step_id ?? null,
        timeout: 10000,
        retry_count: 0,
        failure_strategy: 'stop',
        assert_mode: 'strict',
        overrides: {
          params: step.query_params || [],
          headers: step.headers || [],
        },
        assertions: step.assertions || [],
        extract_vars: step.extract_vars || [],
        ...(step.node_type === 'wait' && step.wait_duration != null
          ? { wait_duration: step.wait_duration }
          : {}),
      })),
      edges: (sceneData.edges || []).map((edge) => ({
        edge_id: edge.edge_id,
        source_node_id: edge.source_node_id,
        target_node_id: edge.target_node_id,
        source_handle: edge.source_handle ?? null,
        label: edge.label || '',
      })),
      variables: {},
      config: {
        concurrency: sceneData.config?.concurrency ?? sceneData.config?.thread_count ?? 1,
        retry_count: 0,
        cookie_sharing: Boolean(sceneData.config?.global_cookie),
        random_range: sceneData.config?.step_delay_random ? 1 : 1,
      },
    },
  }
  return JSON.stringify(exported, null, 2)
}

export function downloadSceneJson(sceneData: SceneExportData): void {
  const json = exportSceneToJson(sceneData)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${sceneData.name || 'scene'}_${new Date().toISOString().slice(0, 10)}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function importSceneFromJson(file: File): Promise<ExportedScene> {
  const text = await file.text()
  const parsed = JSON.parse(text)
  if (!parsed.version || !parsed.scene) {
    throw new Error('无效的场景文件格式：缺少 version 或 scene 字段')
  }
  return parsed as ExportedScene
}
