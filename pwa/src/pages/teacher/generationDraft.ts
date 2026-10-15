import type { GeneratedTask, GeneratedTest } from '../../api/assignments'

export function matchesConfiguration(draft: GeneratedTest, topic: string, nTasks: number | '', personalize: boolean, selectedIds: string[]): boolean {
  return draft.topic === topic && draft.n_tasks === nTasks && draft.personalize === personalize
    && draft.students.length === selectedIds.length && draft.students.every(s => selectedIds.includes(s.student_id))
}

export function replacePreviewTask(draft: GeneratedTest, studentId: string, index: number, oldTaskId: string, replacement: GeneratedTask): GeneratedTest {
  const targets = draft.personalize ? draft.students.filter(s => s.student_id === studentId) : draft.students
  if (!targets.length || targets.some(s => s.tasks[index]?.task_id !== oldTaskId
    || s.tasks.some(t => t.task_id === replacement.task_id))) return draft
  const students = draft.students.map(student => !targets.includes(student) ? student : {
    ...student, tasks: student.tasks.map((task, i) => i === index ? { ...replacement } : task),
  })
  const counts = new Map<string, number>()
  for (const student of students) for (const task of student.tasks) counts.set(task.task_id, (counts.get(task.task_id) || 0) + 1)
  return { ...draft, students, usage_stats: {
    total_tasks_used: [...counts.values()].reduce((a, b) => a + b, 0),
    unique_tasks_used: counts.size, max_usage: Math.max(0, ...counts.values()),
  } }
}
