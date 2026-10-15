import type { Attempt, AssignmentSummary, ResultStatus, StudentResult } from '../../api/teacher'

export const RESULT: Record<ResultStatus, { label: string; symbol: string; style: string }> = {
  correct: { label: 'Верно', symbol: '✓', style: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  incorrect: { label: 'Неверно', symbol: '×', style: 'bg-rose-50 text-rose-800 border-rose-200' },
  skipped: { label: 'Пропущено', symbol: '↷', style: 'bg-amber-50 text-amber-800 border-amber-200' },
  surrendered: { label: 'Сдался', symbol: '⚑', style: 'bg-orange-50 text-orange-800 border-orange-200' },
  unanswered: { label: 'Не решал', symbol: '—', style: 'bg-slate-50 text-slate-500 border-slate-200' },
}
export function attemptStatus(attempt: Attempt): ResultStatus {
  return attempt.surrendered ? 'surrendered' : attempt.skipped ? 'skipped' : attempt.correct ? 'correct' : 'incorrect'
}
export function resultText(result: StudentResult): string {
  if (result.has_legacy && result.saved_state === 'completed' && !result.answered_count) return 'Завершён до обновления · старые ответы в истории'
  if (!result.answered_count) return 'Ещё не приступил'
  return `${result.state === 'completed' ? 'Завершён' : `Выполнено ${result.answered_count} из ${result.task_count}`} · верно ${result.correct_count}/${result.task_count}`
}
export function dateLabel(value: string | null, withTime = false): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } as const : {}) })
}
export function latestStudentTest(assignments: AssignmentSummary[], studentId: string) {
  return assignments.find(a => a.status !== 'draft' && a.students.some(s => s.student_id === studentId))
}
