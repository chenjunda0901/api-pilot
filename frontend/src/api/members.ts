import request from './request'

export interface MemberItem {
  id: number
  user_id: number
  username: string
  nickname: string
  email: string
  role: string
  created_at: string
}

export interface MemberAddRequest {
  user_id: number
  role: string
}

export interface MemberUpdateRoleRequest {
  role: string
}

// ── 成员列表 ──
export function listMembers(projectId: number) {
  return request.get<MemberItem[]>(`/projects/${projectId}/members`)
}

// ── 添加成员 ──
export function addMember(projectId: number, data: MemberAddRequest) {
  return request.post<MemberItem>(`/projects/${projectId}/members`, data)
}

// ── 修改成员角色 ──
export function updateMemberRole(projectId: number, userId: number, data: MemberUpdateRoleRequest) {
  return request.put(`/projects/${projectId}/members/${userId}/role`, data)
}

// ── 移除成员 ──
export function removeMember(projectId: number, userId: number) {
  return request.delete(`/projects/${projectId}/members/${userId}`)
}

// ── 退出项目 ──
export function leaveProject(projectId: number) {
  return request.post(`/projects/${projectId}/members/leave`)
}