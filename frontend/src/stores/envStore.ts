// frontend/src/stores/envStore.ts
import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { listEnvironments, upsertEnvironmentVariable } from "@/api/environments"
import { getGlobalConfig } from "@/api/projects"
import { logger } from "@/utils/logger"
import { globalSWRCache } from "@/composables/useSWR"

export interface ServiceItem {
  name: string
  module: string
  url: string
  is_base?: boolean
}

export interface VariableEntry {
  key: string
  value: string
  enabled: boolean
}

export interface EnvHeader {
  key: string
  value: string
  enabled: boolean
}

// ── 敏感变量保护 ─────────────────────────────────────────────────────────────
// 名称含以下关键词的环境变量被视为"敏感"，
// 用户编写的脚本只能读取、不能通过 pm.variables.set 修改。
// 这可以防止恶意脚本批量窃取或篡改内网 API 密钥等敏感配置。
const _SENSITIVE_KEYS_RE = /password|secret|key|token|credential|private|auth|bearer|api[_-]?token/i

export function isVariableSensitive(key: string): boolean {
  return _SENSITIVE_KEYS_RE.test(key)
}

export interface Environment {
  id: number
  name: string
  base_url: string
  variables: VariableEntry[]
  services: ServiceItem[]
  headers: EnvHeader[]
}

export const useEnvStore = defineStore("env", () => {
  // --- localStorage persistence ---
  const STORAGE_KEY = "api_pilot_env"

  function loadPersisted(): { envId: number | null; svcUrl: string } {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) return JSON.parse(raw)
    } catch {
      /* ignore */
    }
    return { envId: null, svcUrl: "" }
  }

  function savePersisted(envId: number | null, svcUrl: string) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ envId, svcUrl }))
    } catch {
      /* ignore */
    }
  }

  const persisted = loadPersisted()

  const environments = ref<Environment[]>([])
  const currentEnvId = ref<number | null>(persisted.envId)
  const currentBaseUrl = ref("")
  const currentServiceUrl = ref(persisted.svcUrl)
  const currentServiceName = ref("")

  // --- 项目全局变量和公共参数 ---
  const projectGlobalVars = ref<VariableEntry[]>([])
  const projectGlobalHeaders = ref<EnvHeader[]>([])
  const _globalConfigFetchedAt = ref<number>(0)

  const currentEnv = computed<Environment | null>(
    () => environments.value.find((e) => e.id === currentEnvId.value) || null
  )

  const currentEnvServices = computed<ServiceItem[]>(() => currentEnv.value?.services || [])

  const defaultService = computed(() => {
    const svcs = currentEnvServices.value
    return svcs.find((s) => s.is_base) || svcs[0] || null
  })

  // 合并后的全局变量：项目全局变量 + 环境变量（环境变量优先）
  const mergedVariables = computed<VariableEntry[]>(() => {
    const map = new Map<string, VariableEntry>()
    // 先放入项目全局变量
    for (const v of projectGlobalVars.value) {
      if (v.key) {
        map.set(v.key, { key: v.key, value: v.value || "", enabled: v.enabled !== false })
      }
    }
    // 环境变量覆盖（同名时覆盖项目全局变量）
    const env = currentEnv.value
    if (env) {
      for (const v of env.variables) {
        if (v.key) {
          map.set(v.key, {
            key: v.key,
            value: v.value || "",
            enabled: v.enabled !== false,
          })
        }
      }
    }
    return Array.from(map.values())
  })

  // 解析后的服务 URL：将 {{varName}} 替换为实际变量值
  const resolvedServiceUrl = computed(() => {
    return resolveUrl(currentServiceUrl.value || '')
  })

  /** 将 URL 中的 {{varName}} 模板替换为合并后的实际变量值 */
  function resolveUrl(url: string): string {
    if (!url) return url
    const vars = mergedVariables.value
    for (const v of vars) {
      if (v.key && v.enabled !== false) {
        // 使用 replaceAll 避免变量名中正则特殊字符导致出错
        url = url.replaceAll(`{{${v.key}}}`, v.value || '')
      }
    }
    return url
  }

  // 合并后的全局 Headers
  const mergedHeaders = computed(() => {
    const map = new Map<string, EnvHeader>()
    for (const h of projectGlobalHeaders.value) {
      if (h.key) map.set(h.key, h)
    }
    const env = currentEnv.value
    if (env) {
      for (const h of env.headers) {
        if (h.key) map.set(h.key, h)
      }
    }
    return Array.from(map.values())
  })

  async function fetchEnvs(projectId: number) {
    const swrKey = `envs:${projectId}`
    const cached = globalSWRCache.getCache(swrKey)
    if (cached) {
      environments.value = cached as Environment[]
      restorePersistedEnv()
      return
    }
    try {
      const data = await globalSWRCache.get(swrKey, async () => {
        const res = await listEnvironments(projectId)
        // 后端返回 JSON 字符串，需要解析
        const rawEnvs = res.data || []
        return rawEnvs.map((e: Record<string, unknown>) => {
          function safeParse(val: unknown, fallback: unknown[] = []) {
            if (typeof val === 'string') {
              try {
                return JSON.parse(val || '[]', (key, value) => {
                  if (key === '__proto__') return undefined
                  return value
                })
              } catch { return fallback }
            }
            return val || fallback
          }
          return {
            id: e.id,
            name: e.name,
            base_url: (e.base_url as string) || "",
            services: safeParse(e.services),
            variables: safeParse(e.variables),
            headers: safeParse(e.headers),
          }
        }) as Environment[]
      }, { ttl: 60000 })
      environments.value = data as Environment[]
      restorePersistedEnv()
    } catch (err) {
      logger.error('[envStore] fetchEnvs failed:', err)
      environments.value = []
    }
  }

  /** 恢复持久化的环境选择状态 */
  function restorePersistedEnv() {
    const persisted = loadPersisted()
    const stillExists =
      persisted.envId && environments.value.some((e) => e.id === persisted.envId)
    if (stillExists) {
      currentEnvId.value = persisted.envId
      currentServiceUrl.value = persisted.svcUrl
      updateBaseUrl(true)
    } else if (environments.value.length > 0) {
      currentEnvId.value = environments.value[0]?.id ?? null
      updateBaseUrl()
      savePersisted(currentEnvId.value, currentServiceUrl.value)
    } else {
      currentEnvId.value = null
    }
  }

  async function fetchGlobalConfig(projectId: number, force = false) {
    const swrKey = `globalConfig:${projectId}`
    // 缓存有效期 30s
    if (!force && Date.now() - _globalConfigFetchedAt.value < 30_000) return
    try {
      const data = await globalSWRCache.get(swrKey, async () => {
        const res = await getGlobalConfig(projectId)
        return res.data || {}
      }, { ttl: 30000 })
      const config = data as any
      const _safeReviver = (key: string, value: unknown) => key === '__proto__' ? undefined : value
      const rawVars = typeof config.global_variables === 'string'
        ? JSON.parse(config.global_variables || '[]', _safeReviver)
        : (config.global_variables || [])
      const rawHeaders = typeof config.global_params?.headers === 'string'
        ? JSON.parse(config.global_params.headers || '[]', _safeReviver)
        : (config.global_params?.headers || [])
      projectGlobalVars.value = rawVars
      projectGlobalHeaders.value = rawHeaders
      _globalConfigFetchedAt.value = Date.now()
    } catch (err) {
      logger.error('[envStore] fetchGlobalConfig failed:', err)
      projectGlobalVars.value = []
      projectGlobalHeaders.value = []
    }
  }

  function updateBaseUrl(preserveServiceUrl = false) {
    const env = currentEnv.value
    const svcs = env?.services || []
    const def = svcs.find((s) => s.is_base) || svcs[0]
    if (def) {
      currentBaseUrl.value = def.url || ""
      if (!preserveServiceUrl || !currentServiceUrl.value) {
        currentServiceUrl.value = def.url || ""
        currentServiceName.value = def.name || def.module || ""
      } else {
        currentServiceName.value = def.name || def.module || ""
      }
    } else if (env?.base_url) {
      // Services 为空时使用 base_url 作为兜底
      currentBaseUrl.value = env.base_url
      if (!preserveServiceUrl || !currentServiceUrl.value) {
        currentServiceUrl.value = env.base_url
        currentServiceName.value = ""
      }
    } else {
      currentBaseUrl.value = ""
      currentServiceUrl.value = ""
      currentServiceName.value = ""
    }
  }

  function switchEnv(envId: number) {
    currentEnvId.value = envId
    updateBaseUrl()
    savePersisted(envId, currentServiceUrl.value)
  }

  function switchService(url: string) {
    currentServiceUrl.value = url
    const svc = currentEnvServices.value.find((s) => s.url === url)
    if (svc) currentServiceName.value = svc.name || svc.module || ""
    savePersisted(currentEnvId.value, url)
  }

  async function addVariable(projectId: number, key: string, value: string) {
    const env = currentEnv.value
    if (!env || !env.id) {
      logger.warn("[envStore] 没有选中环境，无法添加变量")
      return
    }
    try {
      await upsertEnvironmentVariable(projectId, env.id, key, value)
      // 更新本地缓存
      const vars: VariableEntry[] = JSON.parse(JSON.stringify(env.variables || []))
      const idx = vars.findIndex((v) => v.key === key)
      if (idx >= 0) {
        vars[idx] = { ...vars[idx], value }
      } else {
        vars.push({ key, value, enabled: true })
      }
      env.variables = vars
    } catch (err) {
      logger.error('[envStore] addVariable failed:', err)
      throw err
    }
  }

  function resetState() {
    environments.value = []
    currentEnvId.value = null
    currentBaseUrl.value = ""
    currentServiceUrl.value = ""
    currentServiceName.value = ""
    projectGlobalVars.value = []
    projectGlobalHeaders.value = []
    _globalConfigFetchedAt.value = 0
    savePersisted(null, "")
  }

  return {
    environments,
    currentEnvId,
    currentBaseUrl,
    currentServiceUrl,
    resolvedServiceUrl,
    currentServiceName,
    currentEnv,
    currentEnvServices,
    defaultService,
    projectGlobalVars,
    projectGlobalHeaders,
    mergedVariables,
    mergedHeaders,
    allVariablesForPreview: {
      get services() {
        let svcs = currentEnv.value?.services
        if (typeof svcs === 'string') {
          try { svcs = JSON.parse(svcs) } catch { svcs = [] }
        }
        return Array.isArray(svcs) ? svcs : []
      },
      get variables() {
        const vars = mergedVariables.value
        if (Array.isArray(vars)) return vars
        if (typeof vars === 'string') {
          try { return JSON.parse(vars) as VariableEntry[] } catch { return [] }
        }
        return []
      },
      get headers() {
        let hdrs = currentEnv.value?.headers
        if (typeof hdrs === 'string') {
          try { hdrs = JSON.parse(hdrs) } catch { hdrs = [] }
        }
        return Array.isArray(hdrs) ? hdrs : []
      },
    },
    fetchEnvs,
    fetchGlobalConfig,
    switchEnv,
    switchService,
    updateBaseUrl,
    addVariable,
    resolveUrl,
    resetState,
  }
})
