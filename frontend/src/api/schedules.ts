import request from './request'

export function previewNextRuns(cron: string, count = 5) {
  return request.get<{ runs: string[] }>(`/schedules/preview-next`, { params: { cron, count } })
}
