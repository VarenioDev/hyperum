import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTaskAttempts, type Attempt, type HistoryAttempt } from '../../api/teacher'
import LatexText from '../LatexText'
import { RESULT, attemptStatus, dateLabel } from './reportUtils'
import { ReportError } from './ReportUI'

export function AttemptRow({ attempt, latest }: { attempt: Attempt; latest?: boolean }) {
  const status = RESULT[attemptStatus(attempt)]
  return <div className="rounded-xl bg-white/70 border border-slate-100 p-3 space-y-2">
    <div className="flex flex-wrap items-center gap-2 text-xs"><span className={`px-2 py-1 rounded-lg border ${status.style}`}>{status.symbol} {status.label}</span>
      {latest && <span className="text-brand-700">Последняя попытка</span>}
      <span className="text-slate-500">{dateLabel(attempt.created_at, true)}</span>
      {attempt.time_sec != null && <span className="text-slate-400">{attempt.time_sec} сек.</span>}
    </div>
    {!attempt.skipped && !attempt.surrendered && <p className="text-sm text-slate-700 whitespace-pre-wrap break-words">Ответ: {attempt.answer || 'Пустой ответ'}</p>}
  </div>
}
export function TaskText({ text, options, expected }: { text: string; options: Record<string, unknown> | null; expected: string | null }) {
  return <div className="space-y-4">
    <LatexText text={text} className="text-sm text-slate-700" />
    {options && <ul className="space-y-1 text-sm">{Object.entries(options).map(([key, value]) => <li key={key} className="flex gap-2"><b>{key}.</b><LatexText text={typeof value === 'string' ? value : JSON.stringify(value)} /></li>)}</ul>}
    <div className="rounded-xl bg-emerald-50 p-3"><p className="text-xs text-emerald-800 mb-1">Правильный ответ</p><p className="text-sm text-emerald-950 whitespace-pre-wrap break-words">{expected ?? 'Не указан'}</p></div>
  </div>
}
export function ReportDialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close() }, [])
  return <dialog ref={ref} onCancel={e => { e.preventDefault(); onClose() }} aria-labelledby="report-dialog-title"
    className="rounded-3xl w-[calc(100%_-_2rem)] max-w-2xl max-h-[90dvh] p-0 backdrop:bg-slate-900/40 shadow-xl">
    <div className="sticky top-0 bg-white/95 flex justify-between items-center gap-3 p-5 border-b border-slate-100 z-10">
      <h2 id="report-dialog-title" className="font-semibold text-slate-800">{title}</h2><button type="button" autoFocus onClick={onClose} className="text-sm text-slate-500 rounded-lg p-2 hover:bg-slate-100">Закрыть</button>
    </div><div className="p-5 space-y-4">{children}</div>
  </dialog>
}
export function TaskAttemptDialog({ assignmentId, studentId, taskId, studentName, onClose }: {
  assignmentId: string; studentId: string; taskId: string; studentName: string; onClose: () => void
}) {
  const [offset, setOffset] = useState(0)
  const query = useQuery({ queryKey: ['teacher-task-attempts', assignmentId, studentId, taskId, offset],
    queryFn: () => getTaskAttempts(assignmentId, studentId, taskId, offset) })
  return <ReportDialog title={studentName} onClose={onClose}>
    {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем задание и попытки…</p>}
    {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
    {query.data && <>
      <p className="text-xs text-slate-500">Задание {query.data.task.position} · {query.data.task.code}{query.data.task.skill_name && ` · ${query.data.task.skill_name}`}</p>
      <TaskText text={query.data.task.text} options={query.data.task.options} expected={query.data.task.expected} />
      <h3 className="text-sm font-semibold text-slate-700">Попытки · сначала новые</h3>
      {!query.data.attempts.length && <p className="text-sm text-slate-500">В этом тесте ответов ещё нет.</p>}
      {query.data.attempts.map((attempt, index) => <AttemptRow key={attempt.id} attempt={attempt} latest={offset === 0 && index === 0} />)}
      <HistoryPagination offset={offset} hasMore={query.data.has_more} onChange={setOffset} />
    </>}
  </ReportDialog>
}
export function HistoryPagination({ offset, hasMore, onChange }: { offset: number; hasMore: boolean; onChange: (offset: number) => void }) {
  if (!offset && !hasMore) return null
  return <div className="flex justify-between gap-3 text-sm"><button type="button" disabled={!offset} onClick={() => onChange(Math.max(0, offset - 20))} className="text-brand-700 disabled:opacity-40 py-2">← Новее</button>
    <button type="button" disabled={!hasMore} onClick={() => onChange(offset + 20)} className="text-brand-700 disabled:opacity-40 py-2">Раньше →</button></div>
}
export function HistoryResponse({ attempt }: { attempt: HistoryAttempt }) {
  return <details className="glass rounded-2xl p-4">
    <summary className="cursor-pointer text-sm text-slate-700"><span className="font-medium">{attempt.code} · {RESULT[attemptStatus(attempt)].label}</span>
      <span className="block text-xs text-slate-500 mt-1">{attempt.context === 'legacy' ? 'До обновления · без точной привязки к тесту' : attempt.assignment_title || 'Самостоятельная практика'} · {dateLabel(attempt.created_at, true)}</span></summary>
    <div className="mt-4 space-y-4"><TaskText text={attempt.task_text} options={attempt.options} expected={attempt.expected} /><AttemptRow attempt={attempt} /></div>
  </details>
}
