import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { generateTest, getTopics, regenerateTask, saveGeneratedTest, sendAssignment,
  type GeneratedTest, type GeneratedStudentTest } from '../../api/assignments'
import { getGroupDetail } from '../../api/groups'
import { getErrorMessage } from '../../api/client'
import Header from '../../components/Header'
import StudentPicker from '../../components/teacher/StudentPicker'
import GeneratedTaskCard from '../../components/teacher/GeneratedTaskCard'
import { matchesConfiguration, replacePreviewTask } from './generationDraft'

export default function TeacherGenerate() {
  const { id } = useParams<{ id: string }>()
  const [params] = useSearchParams()
  return id ? <Generator key={`${id}:${params.toString()}`} groupId={id} initialStudent={params.get('student')} initialTopic={params.get('topic')} /> : <p>Класс не найден</p>
}

function Generator({ groupId, initialStudent, initialTopic }: { groupId: string; initialStudent: string | null; initialTopic: string | null }) {
  const navigate = useNavigate()
  const [topic, setTopic] = useState(initialTopic || '')
  const [nTasks, setNTasks] = useState<number | ''>(5)
  const [personalize, setPersonalize] = useState(true)
  const [selection, setSelection] = useState<string[] | null>(initialStudent ? [initialStudent] : null)
  const [title, setTitle] = useState('')
  const [generated, setGenerated] = useState<GeneratedTest | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [rejected, setRejected] = useState<Record<string, string[]>>({})
  const [notices, setNotices] = useState<Record<string, string>>({})
  const [replaceErrors, setReplaceErrors] = useState<Record<string, string>>({})

  const groupQuery = useQuery({ queryKey: ['group', groupId], queryFn: () => getGroupDetail(groupId) })
  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: getTopics })
  const group = groupQuery.data
  const eligible = (group?.students || []).filter(s => s.status === 'active')
  const selectedIds = selection === null ? eligible.map(s => s.id) : selection.filter(id => eligible.some(s => s.id === id))
  const preview = generated && matchesConfiguration(generated, topic, nTasks, personalize, selectedIds) ? generated : null

  function resetPreview() {
    setGenerated(null)
    setSavedId(null)
    setError('')
    setRejected({})
    setNotices({})
    setReplaceErrors({})
  }

  const generateMutation = useMutation({
    mutationFn: generateTest,
    onSuccess: data => {
      setGenerated(data)
      setError('')
      if (!title.trim()) setTitle(`${data.topic} — ${data.class_name}`)
    },
    onError: err => setError(getErrorMessage(err)),
  })
  const saveMutation = useMutation({
    mutationFn: saveGeneratedTest,
    onSuccess: data => { setSavedId(data.assignment_id); setError('') },
    onError: err => setError(getErrorMessage(err)),
  })
  const sendMutation = useMutation({
    mutationFn: sendAssignment,
    onSuccess: () => navigate(`/teacher/class/${groupId}`),
    onError: err => setError(getErrorMessage(err)),
  })
  const replaceMutation = useMutation({
    mutationFn: async ({ student, index }: { student: GeneratedStudentTest; index: number }) => {
      if (!preview || savedId) throw new Error('Сначала сгенерируй тест')
      const bucket = preview.personalize ? student.student_id : 'common'
      const result = await regenerateTask({
        group_id: groupId, topic: preview.topic, personalize: preview.personalize,
        student_ids: preview.personalize ? [student.student_id] : preview.students.map(s => s.student_id),
        task_id: student.tasks[index].task_id,
        exclude_task_ids: [...new Set([...student.tasks.map(t => t.task_id), ...(rejected[bucket] || [])])],
      })
      return { result, bucket, previousId: student.tasks[index].task_id }
    },
    onMutate: ({ student, index }) => {
      const key = `${student.student_id}:${index}`
      setReplaceErrors(previous => ({ ...previous, [key]: '' }))
      setNotices(previous => ({ ...previous, [key]: '' }))
    },
    onSuccess: ({ result, bucket, previousId }, { student, index }) => {
      setGenerated(previous => previous ? replacePreviewTask(previous, student.student_id, index, previousId, result.task) : previous)
      setRejected(previous => ({ ...previous, [bucket]: [...new Set([...(previous[bucket] || []), previousId])] }))
      setNotices(previous => ({ ...previous, [`${student.student_id}:${index}`]: result.match === 'neighboring_skill'
        ? 'Подобрали задание из соседнего навыка этой темы' : 'Подобрали другое задание на тот же навык' }))
    },
    onError: (err, { student, index }) => setReplaceErrors(previous => ({ ...previous, [`${student.student_id}:${index}`]: getErrorMessage(err) })),
  })
  const busy = generateMutation.isPending || saveMutation.isPending || sendMutation.isPending || replaceMutation.isPending
  const locked = busy || Boolean(savedId)
  const validCount = typeof nTasks === 'number' && Number.isInteger(nTasks) && nTasks >= 1 && nTasks <= 20

  function handleGenerate() {
    if (busy || savedId || !group || !topic || !validCount || !selectedIds.length) return
    const ids = [...selectedIds]
    resetPreview()
    setSelection(ids)
    generateMutation.mutate({ group_id: groupId, topic, n_tasks: nTasks as number, student_ids: ids, personalize })
  }

  function handleSave() {
    if (!preview || busy || savedId || title.trim().length < 2) return
    setError('')
    saveMutation.mutate({ title: title.trim(), group_id: groupId, topic: preview.topic,
      students: preview.students, personalize: preview.personalize })
  }

  const renderTasks = (student: GeneratedStudentTest) => (
    <div className="space-y-3">
      {student.tasks.map((task, index) => {
        const key = `${student.student_id}:${index}`
        return <GeneratedTaskCard key={`${index}:${task.task_id}`} task={task} position={index + 1}
          onReplace={() => replaceMutation.mutate({ student, index })} disabled={busy}
          replacing={replaceMutation.isPending && replaceMutation.variables?.student.student_id === student.student_id && replaceMutation.variables.index === index}
          saved={Boolean(savedId)} common={!personalize} message={notices[key]} error={replaceErrors[key]} />
      })}
    </div>
  )

  return (
    <div className="min-h-screen pb-24 relative">
      <div className="fixed top-0 -left-32 w-80 h-80 rounded-full bg-brand-300/30 blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 -right-32 w-80 h-80 rounded-full bg-purple-300/30 blur-3xl pointer-events-none" />
      <Header showBack backTo={`/teacher/class/${groupId}`} />
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5 relative">
        <div>
          <p className="text-xs font-medium text-brand-600 mb-2">{group ? `Класс ${group.name}` : 'Подготовка теста'}</p>
          <h1 className="text-2xl font-bold text-slate-800">Сгенерировать тест</h1>
          <p className="text-sm text-slate-500 mt-2">Выбери учеников и тему. Мы подберём задания, а последнее слово — за тобой.</p>
        </div>
        {groupQuery.isPending && <p className="text-sm text-slate-500" role="status">Загружаем класс…</p>}
        {groupQuery.isError && <div role="alert" className="glass rounded-2xl p-4 text-sm text-red-600">
          {getErrorMessage(groupQuery.error)} <button type="button" onClick={() => groupQuery.refetch()} className="underline ml-2">Повторить</button>
        </div>}
        {group && <>
          <StudentPicker students={eligible} selectedIds={selectedIds} disabled={locked}
            onChange={ids => { resetPreview(); setSelection(ids) }} />
          <fieldset disabled={locked} className="glass-strong rounded-3xl p-5 space-y-4">
            <legend className="sr-only">Настройки теста</legend>
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_160px] gap-4">
              <label className="block text-sm font-medium text-slate-700">Тема
                <select value={topic} onChange={e => { resetPreview(); setTopic(e.target.value) }} disabled={locked || topicsQuery.isPending || topicsQuery.isError}
                  className="mt-2 w-full px-4 py-3 bg-white/70 border border-white/80 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-400">
                  <option value="">{topicsQuery.isPending ? 'Загружаем темы…' : 'Выбери тему'}</option>
                  {(topicsQuery.data || []).map(value => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">Заданий на ученика
                <input type="number" min={1} max={20} step={1} value={nTasks}
                  onChange={e => { resetPreview(); setNTasks(e.target.value === '' ? '' : Number(e.target.value)) }}
                  aria-invalid={!validCount}
                  className="mt-2 w-full px-4 py-3 bg-white/70 border border-white/80 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
              </label>
            </div>
            {!validCount && <p className="text-xs text-red-600">Укажи целое число от 1 до 20.</p>}
            <label className="flex gap-3 items-start rounded-2xl bg-white/60 p-4 cursor-pointer">
              <input type="checkbox" checked={!personalize} onChange={e => { resetPreview(); setPersonalize(!e.target.checked) }} className="w-4 h-4 mt-0.5 shrink-0 accent-pink-500" />
              <span><span className="block text-sm font-semibold text-slate-700">Не персонализировать</span>
                <span className="block text-xs text-slate-500 mt-1 leading-relaxed">{personalize
                  ? 'Сейчас каждому ученику подбирается свой набор по его навыкам.'
                  : 'Один набор для всех. Подбор — по среднему уровню выбранных учеников.'}</span></span>
            </label>
            <button type="button" onClick={handleGenerate} disabled={locked || !topic || !selectedIds.length || !validCount}
              className={`${generateMutation.isPending ? 'btn-loading' : 'bg-hyper text-white shadow-lg shadow-brand-500/20'} w-full font-semibold py-3.5 rounded-2xl disabled:opacity-50 disabled:shadow-none transition-all`}>
              <span>{generateMutation.isPending ? '✨ Подбираем задания…' : preview ? '↻ Подобрать заново' : '✨ Сгенерировать'}</span>
            </button>
            {!selectedIds.length && <p className="text-xs text-slate-500">Выбери хотя бы одного ученика.</p>}
          </fieldset>
        </>}
        {topicsQuery.isError && <div role="alert" className="text-sm text-red-600">
          Не удалось загрузить темы. <button type="button" onClick={() => topicsQuery.refetch()} className="underline">Повторить</button>
        </div>}
        {error && <div role="alert" className="bg-red-50/80 border border-red-200 rounded-2xl p-4 text-sm text-red-700">{error}</div>}
        {generated && !preview && <div role="alert" className="glass rounded-2xl p-4 text-sm text-slate-600">
          Состав класса изменился. Подбери тест заново для актуального списка учеников.
          {savedId && <button type="button" disabled={busy} className="block mt-3 text-brand-600 font-semibold"
            onClick={() => { resetPreview(); setTitle('') }}>Начать новый тест</button>}
        </div>}
        {preview && <section className="space-y-4" aria-label="Предпросмотр теста">
          <div className="glass-tinted rounded-3xl p-5">
            <p className="text-xs font-medium text-brand-600 mb-1">Проверь перед отправкой</p>
            <h2 className="font-semibold text-slate-800">{preview.personalize ? 'Персональные наборы готовы' : 'Общий тест готов'}</h2>
            <p className="text-sm text-slate-500 mt-2">Получателей: {preview.students.length} · заданий каждому: {preview.n_tasks}</p>
            {!preview.personalize && <p className="text-xs text-slate-500 mt-2">Замена задания изменит его у всех получателей.</p>}
            {preview.personalize && preview.usage_stats && <p className="text-xs text-slate-400 mt-2">Уникальных заданий: {preview.usage_stats.unique_tasks_used}</p>}
          </div>
          {preview.personalize ? preview.students.map(student => (
            <details key={student.student_id} className="glass rounded-3xl p-4 group">
              <summary className="cursor-pointer flex items-center justify-between gap-3 text-sm font-medium text-slate-700">
                <span className="min-w-0 break-words">{student.full_name}</span><span className="text-xs text-slate-400 shrink-0">{student.tasks.length} заданий</span>
              </summary>
              <div className="mt-4">{renderTasks(student)}</div>
            </details>
          )) : <div className="space-y-3">{renderTasks(preview.students[0])}</div>}
          <div className="glass-strong rounded-3xl p-5 space-y-4">
            <label className="block text-sm font-medium text-slate-700">Название теста
              <input value={title} onChange={e => setTitle(e.target.value)} disabled={locked} maxLength={200}
                className="mt-2 w-full px-4 py-3 bg-white/70 border border-white/80 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
            </label>
            {savedId ? <>
              <p className="text-sm text-emerald-700">✓ Черновик сохранён. Ученики увидят тест после отправки.</p>
              <button type="button" disabled={busy} onClick={() => { if (savedId && preview && !busy) { setError(''); sendMutation.mutate(savedId) } }}
                className="w-full bg-hyper text-white font-semibold py-3.5 rounded-2xl shadow-lg shadow-brand-500/20 disabled:opacity-50">
                {sendMutation.isPending ? 'Отправляем…' : '🚀 Отправить выбранным ученикам'}
              </button>
              <button type="button" disabled={busy} onClick={() => { resetPreview(); setTitle('') }} className="w-full py-2 text-sm text-slate-500">Начать новый тест</button>
            </> : <>
              <p className="text-xs text-slate-500">После сохранения набор будет зафиксирован. До этого можно заменить любое задание.</p>
              <button type="button" onClick={handleSave} disabled={busy || title.trim().length < 2}
                className="w-full bg-hyper text-white font-semibold py-3.5 rounded-2xl shadow-lg shadow-brand-500/20 disabled:opacity-50">
                {saveMutation.isPending ? 'Сохраняем…' : '💾 Сохранить черновик'}
              </button>
            </>}
          </div>
        </section>}
      </main>
    </div>
  )
}
