/**
 * API-функции для отправки ответов.
 */
import { api } from './client'

export interface SubmitResponsePayload {
  task_id: string
  assignment_id?: string
  answer: string
  time_sec?: number
  skipped?: boolean
  surrendered?: boolean
}

export interface ResponseResult {
  correct: boolean
  expected: string | null
  explanation: string | null
  new_mastery: number | null
  skipped: boolean
}

export async function submitResponse(
  payload: SubmitResponsePayload
): Promise<ResponseResult> {
  const { data } = await api.post<ResponseResult>('/responses', payload)
  return data
}

export interface MyResponse {
  id: string
  task_id: string
  code: string | null
  task_text: string | null
  expected: string | null
  answer: string
  correct: boolean | null
  skipped: boolean
  time_sec: number | null
  created_at: string
  assignment_title: string | null
  skill_name: string | null
  context: 'assignment' | 'practice' | 'legacy'
  surrendered: boolean
}

export async function getMyResponses(
  limit = 50,
  offset = 0
): Promise<MyResponse[]> {
  const { data } = await api.get<MyResponse[]>('/responses/my', {
    params: { limit, offset },
  })
  return data
}
