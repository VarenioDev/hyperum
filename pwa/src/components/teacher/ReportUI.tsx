import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/client'
import type { AssignmentSummary } from '../../api/teacher'
import { dateLabel, resultText } from './reportUtils'

export function ReportError({ error, retry }: { error: unknown; retry: () => void }) {
  return <div role="alert" className="glass rounded-2xl p-4 text-sm text-rose-700">
    {getErrorMessage(error)} <button type="button" onClick={retry} className="underline ml-2">Повторить</button>
  </div>
}
export function LegacyNotice() {
  return <p className="rounded-2xl bg-amber-50/80 border border-amber-100 p-4 text-xs text-amber-900 leading-relaxed">
    Есть ответы до обновления учёта. Они сохранены в истории ученика, но не включены в результаты теста:
    раньше ответы не были привязаны к конкретному назначению.
  </p>
}
export function ReportTabs({ items, active, onChange }: { items: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return <nav aria-label="Разделы" className="flex gap-1 glass rounded-2xl p-1 overflow-x-auto">
    {items.map(item => <button type="button" key={item.id} aria-current={active === item.id ? 'page' : undefined}
      onClick={() => onChange(item.id)} className={`flex-1 whitespace-nowrap px-4 py-3 rounded-xl text-sm font-medium transition-colors ${active === item.id ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:bg-white/50'}`}>
      {item.label}</button>)}
  </nav>
}
export function Metric({ label, children }: { label: string; children: ReactNode }) {
  return <div className="glass rounded-2xl p-4"><p className="text-xl font-bold text-slate-800">{children}</p><p className="text-xs text-slate-500 mt-1">{label}</p></div>
}
export function AssignmentCards({ assignments, studentId }: { assignments: AssignmentSummary[]; studentId?: string }) {
  if (!assignments.length) return <p className="glass rounded-2xl p-6 text-sm text-slate-500">Тестов пока нет. Создай первый, чтобы увидеть результаты здесь.</p>
  return <div className="space-y-3">{assignments.map(a => {
    const result = studentId ? a.students.find(s => s.student_id === studentId) : null
    return <Link key={a.id} to={`/teacher/assignment/${a.id}${studentId ? `?student=${studentId}` : ''}`}
      className="block glass rounded-2xl p-4 hover:bg-white/80 focus-visible:ring-2 focus-visible:ring-brand-400 transition-colors">
      <div className="flex justify-between gap-3"><h3 className="text-sm font-semibold text-slate-800 break-words">{a.title}</h3>
        <span className={`shrink-0 text-xs ${a.status === 'draft' ? 'text-slate-400' : 'text-brand-700'}`}>{a.status === 'draft' ? 'Черновик' : 'Отправлен'} →</span></div>
      <p className="text-xs text-slate-500 mt-1">{a.topic} · {dateLabel(a.sent_at || a.created_at)}</p>
      {a.status !== 'draft' && <p className="text-sm text-slate-600 mt-3">{result ? resultText(result) : `Завершили ${a.summary.completed_count} из ${a.summary.students_count} · начали ${a.summary.started_count}`}</p>}
      {a.has_legacy && !result && <p className="text-xs text-amber-800 mt-2">Есть ответы до обновления учёта</p>}
    </Link>
  })}</div>
}
