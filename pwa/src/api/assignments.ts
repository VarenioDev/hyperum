/**
 * API-функции для работы с назначениями.
 */
import { api } from './client'

export interface MyAssignment {
  id: string
  title: string
  topic: string
  status: string
  deadline: string | null
  task_count: number
  completed_count: number
  created_at: string
}

export interface AssignmentTask {
  position: number
  task_id: string
  code: string
  text: string
  type: string
  options: Record<string, unknown> | null
}

export async function getMyAssignments(): Promise<MyAssignment[]> {
  const { data } = await api.get<MyAssignment[]>('/assignments/my')
  return data
}

export async function getAssignmentTasks(
  assignmentId: string
): Promise<AssignmentTask[]> {
  const { data } = await api.get<AssignmentTask[]>(
    `/assignments/${assignmentId}/tasks`
  )
  return data
}

// ─── Для учителя ────────────────────────────────────────────

export interface GeneratedTask {
  task_id: string
  code: string
  text: string
  skill_id: string | null
  difficulty: number | null
  mastery: number | null
  score: number | null
}

export interface GeneratedStudentTest {
  student_id: string
  full_name: string
  tasks: GeneratedTask[]
  blocked_skills: string[]
}

export interface GeneratedTest {
  class_name: string
  topic: string
  n_tasks: number
  students: GeneratedStudentTest[]
  usage_stats: Record<string, number> | null
}

export interface GenerateRequest {
  group_id: string
  topic: string
  n_tasks: number
}

export interface SaveRequest {
  title: string
  group_id: string
  topic: string
  students: GeneratedStudentTest[]
}

export async function getTopics(): Promise<string[]> {
  const { data } = await api.get<string[]>('/tasks/topics')
  return data
}

export async function generateTest(
  payload: GenerateRequest
): Promise<GeneratedTest> {
  const { data } = await api.post<GeneratedTest>(
    '/assignments/generate',
    payload
  )
  return data
}

export async function saveGeneratedTest(
  payload: SaveRequest
): Promise<{ assignment_id: string; status: string }> {
  const { data } = await api.post('/assignments/save', payload)
  return data
}

export async function sendAssignment(
  assignmentId: string
): Promise<{
  assignment_id: string
  status: string
  students_count: number
  message: string
}> {
  const { data } = await api.post(`/assignments/${assignmentId}/send`)
  return data
}