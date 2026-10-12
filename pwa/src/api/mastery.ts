/**
 * API-функции для работы с mastery.
 */
import { api } from './client'

export interface MasteryItem {
  skill_id: string
  skill_name: string
  mastery: number
  attempts: number
  correct: number
  updated_at: string | null
}

export interface StudentMastery {
  student_id: string
  full_name: string
  skills: MasteryItem[]
}

export async function getMyMastery(): Promise<StudentMastery> {
  const { data } = await api.get<StudentMastery>('/mastery/me')
  return data
}

export interface MasterySummary {
  total_skills: number
  mastered: number
  learning: number
  weak: number
  avg_mastery: number
  responses_last_14d: number
  top_weak_skills: MasteryItem[]
}

export async function getMyMasterySummary(): Promise<MasterySummary> {
  const { data } = await api.get<MasterySummary>('/mastery/me/summary')
  return data
}

/** Утилита: получить «слабые» навыки (mastery < 0.5) */
export function getWeakSkills(skills: MasteryItem[], threshold = 0.5): MasteryItem[] {
  return skills
    .filter((s) => s.mastery < threshold)
    .sort((a, b) => a.mastery - b.mastery)
}

/** Утилита: цвет по mastery */
export function masteryColor(m: number): string {
  if (m >= 0.8) return 'text-mastery-strong'
  if (m >= 0.5) return 'text-mastery-medium'
  return 'text-mastery-weak'
}

export function masteryBgColor(m: number): string {
  if (m >= 0.8) return 'bg-mastery-strong'
  if (m >= 0.5) return 'bg-mastery-medium'
  return 'bg-mastery-weak'
}