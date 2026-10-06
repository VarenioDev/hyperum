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