// ============================================================
// 标签页类型
// ============================================================

export interface TabItem {
  key: string
  label: string
  type: "route" | "api" | "case"
  icon?: string
  method?: string
  apiId?: number
  caseId?: number
  closable: boolean
  pinned?: boolean
  editableName?: boolean
  categoryId?: string
  projectId?: number
}
