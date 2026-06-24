// ============================================================
// 项目类型
// ============================================================

export interface Project {
  id: number
  name: string
  description: string
  is_public: boolean
  global_demo?: number
  created_by: number
  created_at: string
  updated_at: string
  scene_count?: number
  role?: string
}
