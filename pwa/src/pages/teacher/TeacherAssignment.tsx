import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getAssignmentMatrix, type MatrixStudent, type ResultCell } from '../../api/teacher'
import { sendAssignment } from '../../api/assignments'
import Header from '../../components/Header'
import { LegacyNotice, Metric, ReportError } from '../../components/teacher/ReportUI'
import { RESULT, dateLabel, resultText } from '../../components/teacher/reportUtils'
import { TaskAttemptDialog } from '../../components/teacher/AttemptDetails'

export default function TeacherAssignment() {
  const { id } = useParams<{ id: string }>()
  return id ? <Results key={id} assignmentId={id} /> : null
}
function Results({ assignmentId }: { assignmentId: string }) {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<{ student: MatrixStudent; cell: ResultCell } | null>(null)
  const cache = useQueryClient()
  const query = useQuery({ queryKey: ['teacher-assignment', assignmentId], queryFn: () => getAssignmentMatrix(assignmentId) })
  const send = useMutation({ mutationFn: () => sendAssignment(assignmentId), onSuccess: () => {
    cache.invalidateQueries({ queryKey: ['teacher-assignment', assignmentId] })
    cache.invalidateQueries({ queryKey: ['teacher-class-assignments'] })
    cache.invalidateQueries({ queryKey: ['group'] })
    cache.invalidateQueries({ queryKey: ['teacher-student'] })
  } })
  const data = query.data
  const focusId = params.get('student')
  const students = (data?.students || []).filter(s => (!focusId || s.student_id === focusId)
    && search.trim().toLocaleLowerCase('ru').split(/\s+/).every(word => s.full_name.toLocaleLowerCase('ru').includes(word)))
  const positions = Array.from({ length: Math.max(0, ...(data?.students || []).map(s => s.cells.length)) }, (_, i) => i + 1)
  const studentLink = (student: MatrixStudent) => <Link className="font-medium text-slate-800 hover:text-brand-700 break-words" to={`/teacher/student/${student.student_id}?class=${data!.assignment.group_id}&test=${assignmentId}`}>{student.full_name}</Link>
  const cellButton = (student: MatrixStudent, cell: ResultCell, mobile = false) => {
    const status = RESULT[cell.status]
    return <button type="button" onClick={() => setSelected({ student, cell })}
      aria-label={`${student.full_name}, задание ${cell.position}, ${cell.code}: ${status.label}`}
      title={`${cell.code}: ${status.label}`} className={`border rounded-xl min-h-11 ${mobile ? 'px-3 py-2 text-xs' : 'w-11 text-lg font-semibold'} ${status.style} hover:ring-2 hover:ring-brand-300 focus-visible:ring-2 focus-visible:ring-brand-500`}>
      {mobile ? `${cell.position}. ${status.symbol} ${status.label}` : status.symbol}
    </button>
  }
  return <div className="min-h-screen pb-16 relative">
    <Header showBack backTo={data ? `/teacher/class/${data.assignment.group_id}?tab=tests` : '/teacher'} />
    <main className="max-w-6xl mx-auto px-4 py-6 space-y-5">
      {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем результаты…</p>}
      {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
      {data && <>
        <div className="flex flex-wrap justify-between items-start gap-4"><div className="min-w-0">
          <p className="text-xs font-medium text-brand-700">{data.assignment.class_name} · {data.assignment.topic}</p>
          <h1 className="text-2xl font-bold text-slate-800 mt-2 break-words">{data.assignment.title}</h1>
          <p className="text-xs text-slate-500 mt-2">{data.assignment.status === 'draft' ? 'Черновик · ученики его ещё не видят' : `Отправлен ${dateLabel(data.assignment.sent_at, true)}`}</p>
        </div><button type="button" disabled={query.isFetching} onClick={() => query.refetch()} className="glass rounded-xl px-4 py-2 text-xs text-slate-600 disabled:opacity-50">{query.isFetching ? 'Обновляем…' : 'Обновить результаты'}</button></div>
        {data.assignment.status === 'draft' && <div className="glass-strong rounded-2xl p-4 space-y-3">
          <p className="text-sm text-slate-600">Набор сохранён. Открой ячейки, чтобы проверить задания перед отправкой.</p>
          <button type="button" disabled={send.isPending || !data.summary.students_count} onClick={() => send.mutate()} className="bg-hyper text-white px-5 py-3 rounded-xl text-sm font-semibold disabled:opacity-50">{send.isPending ? 'Отправляем…' : `Отправить ученикам (${data.summary.students_count})`}</button>
          {send.isError && <ReportError error={send.error} retry={() => send.mutate()} />}
        </div>}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Metric label="завершили тест">{data.summary.completed_count} / {data.summary.students_count}</Metric>
          <Metric label="начали выполнять">{data.summary.started_count} / {data.summary.students_count}</Metric>
          <Metric label="заданий выполнено">{data.summary.answered_count} / {data.summary.task_count}</Metric>
          <Metric label="верно из всех заданий">{data.summary.correct_count} / {data.summary.task_count}</Metric>
        </div>
        {data.has_legacy && <LegacyNotice />}
        <section className="glass-strong rounded-3xl p-4 sm:p-5 space-y-4">
          <div><h2 className="font-semibold text-slate-800">Результаты учеников</h2>
            <p className="text-xs text-slate-500 mt-2">Учитывается последняя попытка. Нажми на результат, чтобы увидеть задание и историю ответов.</p>
            <p className="text-xs text-slate-500 mt-1">{data.common_tasks ? 'У всех получателей одинаковые задания в одном порядке.' : 'Наборы различаются: номер обозначает позицию, задания у учеников могут быть разными.'}</p>
          </div>
          <div className="flex flex-wrap gap-3 items-center"><label className="flex-1 min-w-48"><span className="sr-only">Найти ученика по имени</span><input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Найти по имени" className="w-full rounded-xl px-4 py-3 bg-white/80 border border-slate-100 text-sm" /></label>
            {focusId && <button type="button" onClick={() => setParams({})} className="text-sm text-brand-700">Показать весь класс</button>}</div>
          <div className="flex flex-wrap gap-3 text-xs">{Object.entries(RESULT).map(([key, status]) => <span key={key} className="text-slate-600"><b className={`inline-block rounded px-1.5 mr-1 ${status.style}`}>{status.symbol}</b>{status.label}</span>)}</div>
          {!students.length && <p className="text-sm text-slate-500 py-4">По этому запросу учеников нет.</p>}
          <div className="hidden md:block overflow-x-auto rounded-2xl border border-slate-100">
            <table className="w-full text-sm border-collapse"><caption className="sr-only">Последние результаты по позициям заданий</caption>
              <thead><tr className="bg-slate-50"><th scope="col" className="text-left p-3 sticky left-0 bg-slate-50 min-w-56 z-10">Ученик</th><th scope="col" className="p-3 whitespace-nowrap">Верно / всего</th>{positions.map(position => <th key={position} scope="col" className="p-3">№{position}</th>)}</tr></thead>
              <tbody>{students.map(student => <tr key={student.student_id} className="border-t border-slate-100">
                <th scope="row" className="p-3 text-left sticky left-0 bg-white z-10 font-normal">{studentLink(student)}<p className="text-xs text-slate-500 mt-1">{resultText(student)}</p></th>
                <td className="p-3 text-center font-semibold text-slate-700">{student.correct_count}/{student.task_count}</td>
                {positions.map(position => { const cell = student.cells.find(c => c.position === position); return <td key={position} className="p-2 text-center">{cell ? cellButton(student, cell) : '—'}</td> })}
              </tr>)}</tbody></table>
          </div>
          <div className="md:hidden space-y-3">{students.map(student => <details key={student.student_id} className="bg-white/70 rounded-2xl p-4 border border-slate-100">
            <summary className="text-sm text-slate-800 cursor-pointer"><span className="font-medium">{student.full_name}</span><span className="block text-xs text-slate-500 mt-1">{resultText(student)}</span></summary>
            <div className="mt-4 space-y-3"><p className="text-sm">{studentLink(student)} →</p><div className="flex flex-wrap gap-2">{student.cells.map(cell => <span key={cell.task_id}>{cellButton(student, cell, true)}</span>)}</div></div>
          </details>)}</div>
        </section>
      </>}
      {selected && <TaskAttemptDialog key={`${selected.student.student_id}:${selected.cell.task_id}`} assignmentId={assignmentId} studentId={selected.student.student_id} taskId={selected.cell.task_id} studentName={selected.student.full_name} onClose={() => setSelected(null)} />}
    </main>
  </div>
}
