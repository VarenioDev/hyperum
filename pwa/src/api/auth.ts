/**
 * Функции для работы с auth API.
 */
import { api } from './client'

export interface User {
  id: string
  tenant_id: string
  role: 'owner' | 'student' | 'admin'
  full_name: string
  email: string | null
  created_at: string
}

export interface StudentBrief {
  id: string
  full_name: string
}

export interface MeResponse {
  user: User
  students: StudentBrief[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/login', {
    email,
    password,
  })
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function me(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>('/auth/me')
  return data
}