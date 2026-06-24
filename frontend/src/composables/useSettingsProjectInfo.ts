import { reactive, ref } from 'vue'
import request from '../api/request'
import { downloadJson, downloadBlob } from '../utils/download'
import { msgError, msgSuccess } from '../utils/message'

export type ExportFormat = 'postman' | 'pilot' | 'openapi' | 'environments' | 'full_zip'

interface ProjectInfoState {
  name: string
  description: string
  created_at: string
  is_public: boolean
}

const createProjectInfo = (): ProjectInfoState => ({
  name: '',
  description: '',
  created_at: '',
  is_public: false,
})

const exportConfig = (projectId: number) => ({
  postman: {
    endpoint: 'postman',
    filename: `postman-collection-${projectId}.json`,
    successMessage: 'Postman Collection 已导出',
  },
  openapi: {
    endpoint: 'openapi',
    filename: `openapi-${projectId}.json`,
    successMessage: 'OpenAPI 3.0 规范已导出',
  },
  environments: {
    endpoint: 'environments',
    filename: `environments-${projectId}.json`,
    successMessage: '环境变量已导出',
  },
  pilot: {
    endpoint: 'pilot',
    filename: `pilot-project-${projectId}.json`,
    successMessage: 'API Pilot JSON 已导出',
  },
  full_zip: {
    endpoint: 'full',
    filename: `project-${projectId}-full.zip`,
    successMessage: '完整项目 ZIP 已导出',
  },
})

export function formatProjectCreatedAt(value: string) {
  if (!value) return ''
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    const pad = (part: number) => String(part).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  } catch {
    return value
  }
}

interface UseSettingsProjectInfoOptions {
  projectId: number
  requireLogin: (action: string) => Promise<boolean>
  refreshProjects: () => Promise<void>
}

export function useSettingsProjectInfo(options: UseSettingsProjectInfoOptions) {
  const { projectId, requireLogin, refreshProjects } = options

  const pageLoading = ref(true)
  const pageError = ref<string | null>(null)
  const exporting = ref(false)
  const resetting = ref(false)
  const saving = ref(false)
  const exportFormat = ref<ExportFormat>('pilot')
  const projectInfo = reactive<ProjectInfoState>(createProjectInfo())

  async function reloadProjectInfo() {
    pageLoading.value = true
    pageError.value = null
    try {
      const response = await request.get(`/projects/${projectId}`)
      projectInfo.name = response.data.name
      projectInfo.description = response.data.description
      projectInfo.created_at = response.data.created_at || ''
      projectInfo.is_public = response.data.is_public ?? false
    } catch (error) {
      pageError.value = (error as Error).message || '加载项目信息失败'
    } finally {
      pageLoading.value = false
    }
  }

  async function saveProject() {
    if (saving.value) return
    if (!(await requireLogin('修改项目设置'))) return
    saving.value = true
    try {
      await request.put(`/projects/${projectId}`, {
        name: projectInfo.name,
        description: projectInfo.description,
        is_public: projectInfo.is_public,
      })
      msgSuccess('已保存')
      await refreshProjects()
    } catch (error: unknown) {
      msgError(`保存失败: ${((error as Error).message || '未知错误')}`)
    } finally {
      saving.value = false
    }
  }

  async function handleExport() {
    if (!(await requireLogin('导出数据'))) return
    exporting.value = true
    try {
      const config = exportConfig(projectId)[exportFormat.value]
      if (exportFormat.value === 'full_zip') {
        // ZIP 导出：接收 blob 响应
        const response = await request.get(`/projects/${projectId}/export/${config.endpoint}`, {
          responseType: 'blob',
        })
        const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: 'application/zip' })
        // 优先使用服务端 Content-Disposition 中的文件名
        const contentDisposition = response.headers?.['content-disposition']
        let filename = config.filename
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?([^"]+)"?/)
          if (match) filename = match[1]
        }
        downloadBlob({ blob, filename })
      } else {
        const response = await request.get(`/projects/${projectId}/export/${config.endpoint}`)
        downloadJson(response.data, config.filename)
      }
      msgSuccess(config.successMessage)
    } catch (error: unknown) {
      msgError(`导出失败: ${((error as Error).message || '未知错误')}`)
    } finally {
      exporting.value = false
    }
  }

  async function handleResetSeed() {
    const { ElMessageBox, ElMessage } = await import('element-plus')
    try {
      await ElMessageBox.confirm(
        '重置将清除所有演示数据并重新创建，此操作不可撤销。确定继续？',
        '重置演示数据',
        {
          confirmButtonText: '确定重置',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        },
      )
    } catch {
      return
    }

    resetting.value = true
    try {
      await request.post('/seed/reset')
      ElMessage.success('演示数据已重置')
      window.location.reload()
    } catch (error: unknown) {
      ElMessage.error((error as Error)?.message || '重置失败')
    } finally {
      resetting.value = false
    }
  }

  return {
    exportFormat,
    exporting,
    handleExport,
    handleResetSeed,
    pageError,
    pageLoading,
    projectInfo,
    reloadProjectInfo,
    resetting,
    saving,
    saveProject,
  }
}
