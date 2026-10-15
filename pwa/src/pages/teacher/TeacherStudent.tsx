import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getStudentProfile, getStudentResponses } from '../../api/teacher'
import Header from '../../components/Header'
import { AssignmentCards, Metric, ReportError, ReportTabs } from '../../components/teacher/ReportUI'
import { HistoryPagination, HistoryResponse } from '../../components/teacher/AttemptDetails'
import { dateLabel } from '../../components/teacher/reportUtils'
import StudentKnowledge from '../../components/teacher/StudentKnowledge'

export default function TeacherStudent() {
  const { id } = useParams<{ id: string }>()
  return id ? <Student key={id} studentId={id} /> : null
}
function Student({ studentId }: { studentId: string }) {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const tab = ['overview', 'graph', 'history'].includes(params.get('tab') || '') ? params.get('tab')! : 'overview'
  const [chosenGroup, setChosenGroup] = useState(params.get('class') || '')
  const query = useQuery({ queryKey: ['teacher-student', studentId], queryFn: () => getStudentProfile(studentId) })
  const profile = query.data
  const availableGroups = profile?.groups.filter(g => g.status === 'active') || []
  const groupId = availableGroups.find(g => g.id === chosenGroup)?.id || availableGroups[0]?.id
  function generate(topic?: string) {
    if (!groupId) return
    const search = new URLSearchParams({ student: studentId })
    if (topic) search.set('topic', topic)
    navigate(`/teacher/class/${groupId}/generate?${search}`)
  }
  const setTab = (value: string) => setParams(previous => { const next = new URLSearchParams(previous); next.set('tab', value); return next })
  return <div className="min-h-screen pb-16 relative">
    <Header showBack backTo={params.get('test') ? `/teacher/assignment/${params.get('test')}?student=${studentId}` : groupId ? `/teacher/class/${groupId}` : '/teacher'} />
    <main className="max-w-5xl mx-auto px-4 py-6 space-y-5">
      {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем ученика…</p>}
      {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
      {profile && <>
        <div className="flex flex-wrap items-start justify-between gap-4"><div>
          <p className="text-xs text-brand-700">Профиль ученика</p><h1 className="text-2xl font-bold text-slate-800 mt-2 break-words">{profile.student.full_name}</h1>
          <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">{profile.groups.map(g => <Link key={g.id} to={`/teacher/class/${g.id}`} className="hover:text-brand-700 underline">{g.name}</Link>)}</div>
          <p className="text-xs text-slate-500 mt-2">Последний ответ: {profile.student.last_activity ? dateLabel(profile.student.last_activity, true) : 'пока нет ответов'}</p>
          {profile.student.email && <p className="text-xs text-slate-400 mt-1 break-all">{profile.student.email}</p>}
          {profile.student.status !== 'active' && <p className="text-xs text-amber-800 mt-2">{profile.student.status === 'pending' ? 'Ожидает подтверждения' : 'Доступ заблокирован'}</p>}
        </div><div className="space-y-2">
          {availableGroups.length > 1 && <label className="block text-xs text-slate-500">Класс для нового теста<select value={groupId} onChange={e => setChosenGroup(e.target.value)} className="block mt-1 rounded-xl px-3 py-2 bg-white text-sm">{availableGroups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></label>}
          <button type="button" onClick={() => generate()} disabled={!groupId || profile.student.status !== 'active'} className="bg-hyper text-white rounded-2xl px-5 py-3 text-sm font-semibold shadow-lg shadow-brand-500/20 disabled:opacity-40">Подобрать тест</button>
        </div></div>
        <ReportTabs active={tab} onChange={setTab} items={[{ id: 'overview', label: 'Обзор' }, { id: 'graph', label: 'Граф знаний' }, { id: 'history', label: 'Тесты и ответы' }]} />
        {tab === 'overview' && <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3"><Metric label="освоено навыков">{profile.summary.mastered}</Metric><Metric label="в процессе">{profile.summary.learning}</Metric><Metric label="требуют внимания">{profile.summary.weak}</Metric><Metric label="навыков с ответами">{profile.summary.total_skills}</Metric></div>
          {!profile.summary.total_skills && <p className="glass rounded-2xl p-5 text-sm text-slate-500">Пока недостаточно данных для оценки знаний. После первых ответов здесь появится прогресс.</p>}
          <section className="glass-strong rounded-3xl p-5 space-y-3"><div className="flex justify-between gap-3"><h2 className="font-semibold text-slate-800">На что обратить внимание</h2><button type="button" onClick={() => setTab('graph')} className="text-sm text-brand-700">Открыть граф →</button></div>
            {!profile.weak_skills.length && <p className="text-sm text-slate-500">{profile.summary.total_skills ? 'Среди оценённых навыков нет требующих повторения.' : 'Сначала нужны ответы ученика.'}</p>}
            {profile.weak_skills.map(skill => <div key={skill.skill_id} className="flex flex-wrap justify-between gap-2 rounded-xl bg-white/70 p-3"><div><p className="text-sm text-slate-700">{skill.name}</p><p className="text-xs text-slate-500 mt-1">Освоение {Math.round(skill.mastery * 100)}% · попыток {skill.attempts}</p></div>{skill.topic && <button type="button" disabled={profile.student.status !== 'active'} onClick={() => generate(skill.topic!)} className="text-xs text-brand-700 disabled:opacity-40">Тест по теме →</button>}</div>)}
          </section>
          <section className="space-y-3"><h2 className="font-semibold text-slate-800">Последние тесты</h2><AssignmentCards assignments={profile.assignments.filter(a => a.status !== 'draft').slice(0, 3)} studentId={studentId} /></section>
        </>}
        {tab === 'graph' && <StudentKnowledge studentId={studentId} onGenerate={topic => { if (profile.student.status === 'active') generate(topic) }} />}
        {tab === 'history' && <>
          <section className="space-y-3"><h2 className="font-semibold text-slate-800">Назначенные тесты</h2><AssignmentCards assignments={profile.assignments} studentId={studentId} /></section>
          <StudentHistory studentId={studentId} />
        </>}
      </>}
    </main>
  </div>
}
function StudentHistory({ studentId }: { studentId: string }) {
  const [offset, setOffset] = useState(0)
  const query = useQuery({ queryKey: ['teacher-student-responses', studentId, offset], queryFn: () => getStudentResponses(studentId, undefined, offset) })
  return <section className="space-y-3"><h2 className="font-semibold text-slate-800">Ответы · сначала новые</h2>
    {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем ответы…</p>}
    {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
    {query.data && <>{!query.data.items.length && <p className="text-sm text-slate-500">Ответов пока нет.</p>}{query.data.items.map(attempt => <HistoryResponse key={attempt.id} attempt={attempt} />)}<HistoryPagination offset={offset} hasMore={query.data.has_more} onChange={setOffset} /></>}
  </section>
}
