/**
 * 统一导出工具模块
 * 提供浏览器端 Blob 下载、JSON 导出以及服务端文件导出的统一入口，
 * 供后续业务代码复用，避免导出逻辑分散在各视图/组合式函数中。
 */
import request from '../api/request'

export interface DownloadBlobPayload {
  blob: Blob
  filename: string
}

/** 触发浏览器下载一个内存中的 Blob。 */
export function downloadBlob({ blob, filename }: DownloadBlobPayload): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

/** 将数据序列化为格式化 JSON 并触发下载。 */
export function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  downloadBlob({ blob, filename })
}

/** 当服务端导出返回空响应体时由 `exportRemoteFile` 抛出。 */
export class EmptyExportDataError extends Error {
  constructor(message = '导出数据为空') {
    super(message)
    this.name = 'EmptyExportDataError'
    Object.setPrototypeOf(this, EmptyExportDataError.prototype)
  }
}

/**
 * 通过共享的 axios 实例请求服务端文件并触发浏览器下载。
 * - 响应体为空时抛出 `EmptyExportDataError`；
 * - 网络/HTTP 错误会重新抛出，由调用方决定如何向用户提示。
 */
export async function exportRemoteFile(url: string, filename: string): Promise<void> {
  const blob = (await request.get(url, { responseType: 'blob' })) as unknown as Blob
  if (!blob || blob.size === 0) {
    throw new EmptyExportDataError()
  }
  downloadBlob({ blob, filename })
}
