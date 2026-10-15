import { api } from './client'

export type ResultStatus = 'unanswered' | 'correct' | 'incorrect' | 'skipped' | 'surrendered'
export interface ResultCell { position: number; task_id: string; code: string; status: ResultStatus; answered_at: string | null }
export interface StudentResult {
  student_id: string; task_count: number; answered_count: number; correct_count: number
  state: 'pending' | 'in_progress' | 'completed'; saved_state: string; has_legacy: boolean
}
export interface MatrixStudent extends StudentResult { full_name: string; cells: ResultCell[] }
export interface ResultSummary {
  students_count: number; completed_count: number; started_count: number
  task_count: number; answered_count: number; correct_count: number
}
export interface AssignmentInfo {
  id: string; title: string; topic: string; status: string; group_id: string; class_name: string
  created_at: string; sent_at: string | null
}
export interface AssignmentSummary extends AssignmentInfo { students: StudentResult[]; summary: ResultSummary; has_legacy: boolean }
export interface AssignmentMatrix { assignment: AssignmentInfo; students: MatrixStudent[]; summary: ResultSummary; common_tasks: boolean; has_legacy: boolean }
export interface Attempt {
  id: string; answer: string | null; correct: boolean | null; skipped: boolean; surrendered: boolean
  time_sec: number | null; created_at: string
}
export interface HistoryAttempt extends Attempt {
  task_id: string; assignment_id: string | null; context: 'assignment' | 'practice' | 'legacy'
  code: string; task_text: string; expected: string | null; options: Record<string, unknown> | null; assignment_title: string | null
}
export interface AttemptPage { items: HistoryAttempt[]; has_more: boolean }
export interface ReportTask { task_id: string; code: string; text: string; expected: string | null; options: Record<string, unknown> | null; position: number; skill_name: string | null }
export interface TaskAttempts { task: ReportTask; attempts: Attempt[]; has_more: boolean }
export interface StudentProfile {
  student: { id: string; full_name: string; email: string | null; status: string; last_activity: string | null }
  groups: { id: string; name: string; status: string }[]
  summary: { total_skills: number; mastered: number; learning: number; weak: number }
  weak_skills: { skill_id: string; name: string; topic: string | null; mastery: number; attempts: number; correct: number }[]
  assignments: AssignmentSummary[]
}

export async function getClassAssignments(id: string): Promise<AssignmentSummary[]> {
  return (await api.get(`/teacher/classes/${id}/assignments`)).data
}
export async function getAssignmentMatrix(id: string): Promise<AssignmentMatrix> {
  return (await api.get(`/teacher/assignments/${id}`)).data
}
export async function getTaskAttempts(aid: string, sid: string, tid: string, offset = 0): Promise<TaskAttempts> {
  return (await api.get(`/teacher/assignments/${aid}/students/${sid}/tasks/${tid}`, { params: { offset } })).data
}
export async function getStudentProfile(id: string): Promise<StudentProfile> {
  return (await api.get(`/teacher/students/${id}`)).data
}
export async function getStudentResponses(id: string, skillId?: string, offset = 0): Promise<AttemptPage> {
  return (await api.get(`/teacher/students/${id}/responses`, { params: { skill_id: skillId, offset } })).data
}
