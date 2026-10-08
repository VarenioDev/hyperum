import { api } from './client'

import type { StudentGraph } from './graph'


export interface DemoTask {
  task_id: string
  code: string
  text: string
  position: number
}

export interface DemoStartResponse {
  session_id: string
  topic: string
  total_tasks: number
  reasoning: string
  tasks: DemoTask[]
}

export interface DemoResponseResult {
  correct: boolean
  expected: string | null
  new_mastery: number | null
}


export async function startDemo(description: string): Promise<DemoStartResponse> {
  const { data } = await api.post<DemoStartResponse>('/demo/start', {
    description,
  })
  return data
}

export async function submitDemoResponse(payload: {
  session_id: string
  task_id: string
  answer: string
  time_sec?: number
}): Promise<DemoResponseResult> {
  const { data } = await api.post<DemoResponseResult>('/demo/response', payload)
  return data
}

export async function getDemoGraph(sessionId: string): Promise<StudentGraph> {
  const { data } = await api.get<StudentGraph>(`/demo/graph/${sessionId}`)
  return data
}