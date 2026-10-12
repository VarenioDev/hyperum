/**
 * API-функции для рекомендаций.
 */
import { api } from './client'

export interface RecommendedTask {
  task_id: string
  code: string
  text: string
  type: string
  options: Record<string, unknown> | null
  difficulty: number | null
}

export interface NextTaskRecommendation {
  skill_id: string
  skill_name: string
  skill_mastery: number
  reason: string
  task: RecommendedTask
}

export async function getNextRecommendation(): Promise<NextTaskRecommendation | null> {
  const { data } = await api.get<NextTaskRecommendation | null>(
    '/recommendations/next'
  )
  return data
}