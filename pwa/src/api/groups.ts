/**
 * API-функции для работы с классами и регистрацией.
 */
import { api } from './client'

// ─── Типы ───────────────────────────────────────────────────

export interface Group {
  id: string
  name: string
  subject: string
  kind: string
  invite_code: string | null
  students_count: number
  pending_count: number
  created_at: string
}

export interface StudentBrief {
  id: string
  full_name: string
  email: string | null
  status: 'active' | 'pending' | 'blocked'
  mastery_avg: number | null
  joined_at: string | null
}

export interface GroupDetail extends Group {
  students: StudentBrief[]
}

export interface GroupByCode {
  name: string
  subject: string
  teacher_name: string
}

export interface JoinPayload {
  code: string
  full_name: string
  email: string
  password: string
}

export interface JoinResponse {
  status: string
  message: string
  group_name: string
}

// ─── Публичные (без авторизации) ────────────────────────────

export async function getGroupByCode(code: string): Promise<GroupByCode> {
  const { data } = await api.get<GroupByCode>(`/groups/by-code/${code}`)
  return data
}

export async function joinByCode(payload: JoinPayload): Promise<JoinResponse> {
  const { data } = await api.post<JoinResponse>('/groups/join', payload)
  return data
}

// ─── Для учителя ────────────────────────────────────────────

export async function listGroups(): Promise<Group[]> {
  const { data } = await api.get<Group[]>('/groups')
  return data
}

export async function getGroupDetail(groupId: string): Promise<GroupDetail> {
  const { data } = await api.get<GroupDetail>(`/groups/${groupId}`)
  return data
}

export async function createGroup(payload: {
  name: string
  subject?: string
  kind?: string
}): Promise<Group> {
  const { data } = await api.post('/groups', payload)
  return data
}

export async function regenerateCode(groupId: string): Promise<{ invite_code: string }> {
  const { data } = await api.post(`/groups/${groupId}/regenerate-code`)
  return data
}

export async function approveStudent(groupId: string, studentId: string) {
  const { data } = await api.post(
    `/groups/${groupId}/approve/${studentId}`
  )
  return data
}

export async function rejectStudent(groupId: string, studentId: string) {
  const { data } = await api.post(
    `/groups/${groupId}/reject/${studentId}`
  )
  return data
}