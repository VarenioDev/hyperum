/**
 * API-функции для работы с графом знаний.
 */
import { api } from './client'

export interface GraphNode {
  id: string
  name: string
  module: string | null
  topic: string | null
  mastery: number | null
  attempts: number | null
  status: 'mastered' | 'learning' | 'weak' | 'unknown'
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
}

export interface StudentGraph {
  student_id: string
  student_name: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export async function getStudentGraph(
  studentId: string
): Promise<StudentGraph> {
  const { data } = await api.get<StudentGraph>(
    `/graph/student/${studentId}`
  )
  return data
}