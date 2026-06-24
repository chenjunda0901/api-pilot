// ============================================================
// 搜索类型
// ============================================================

export interface SearchResults {
  apis: SearchItem[]
  cases: SearchItem[]
  scenes: SearchItem[]
}

export interface SearchItem {
  type: "api" | "case" | "scene"
  id: number
  title: string
  subtitle: string
}
