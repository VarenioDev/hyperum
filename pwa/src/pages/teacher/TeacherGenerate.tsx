import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  getTopics,
  generateTest,
  saveGeneratedTest,
  sendAssignment,
  type GeneratedTest,
} from '../../api/assignments'
import { getGroupDetail } from '../../api/groups'
import { getErrorMessage } from '../../api/client'
import Header from '../../components/Header'

export default function TeacherGenerate() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [topic, setTopic] = useState<string>('')
  const [nTasks, setNTasks] = useState<number>(5)
  const [title, setTitle] = useState<string>('')
  const [generated, setGenerated] = useState<GeneratedTest | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const { data: group, isLoading: loadingGroup } = useQuery({
    queryKey: ['group', id],
    queryFn: () => getGroupDetail(id!),
    enabled: !!id,
  })

  const { data: topics } = useQuery({
    queryKey: ['topics'],
    queryFn: getTopics,
  })

  const generateMutation = useMutation({
    mutationFn: generateTest,
    onSuccess: (data) => {
      setGenerated(data)
      setError('')
      if (!title) {
        setTitle(`${data.topic} — ${data.class_name}`)
      }
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const saveMutation = useMutation({
    mutationFn: saveGeneratedTest,
    onSuccess: (data) => {
      setSavedId(data.assignment_id)
      setError('')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const sendMutation = useMutation({
    mutationFn: sendAssignment,
    onSuccess: () => {
      navigate(`/teacher/class/${id}`)
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleGenerate = () => {
    setError('')
    if (!group) return
    if (!topic) {
      setError('Выбери тему')
      return
    }
    generateMutation.mutate({
      class_name: group.name,
      topic,
      n_tasks: nTasks,
    })
  }

  const handleSave = () => {
    if (!generated) return
    saveMutation.mutate({
      title: title || `${generated.topic} — ${generated.class_name}`,
      class_name: generated.class_name,
      topic: generated.topic,
      students: generated.students,
    })
  }

  const handleSend = () => {
    if (!savedId) return
    sendMutation.mutate(savedId)
  }

  const isBusy =
    generateMutation.isPending ||
    saveMutation.isPending ||
    sendMutation.isPending

  if (loadingGroup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen pb-32 relative">
      <div className="fixed top-0 -left-32 w-80 h-80 rounded-full
                      bg-brand-300/30 blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 -right-32 w-80 h-80 rounded-full
                      bg-purple-300/30 blur-3xl pointer-events-none" />

      <Header showBack backTo={`/teacher/class/${id}`} />

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5 relative">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            Сгенерировать тест
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Класс {group?.name} · каждому ученику — свой набор
          </p>
        </div>

        {/* Форма генерации */}
        <div className="glass-strong rounded-3xl p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Тема
            </label>
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={isBusy}
            >
              <option value="">— Выбери тему —</option>
              {(topics || []).map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Заданий на ученика
            </label>
            <input
              type="number"
              value={nTasks}
              min={1}
              max={15}
              onChange={(e) => setNTasks(Number(e.target.value))}
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={isBusy}
            />
          </div>

          {error && (
            <div className="bg-red-50/80 border border-red-200 rounded-2xl
                            p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={isBusy || !topic}
            className="w-full bg-hyper text-white font-semibold py-3.5
                       rounded-2xl shadow-lg shadow-brand-500/30
                       hover:shadow-xl transition-all
                       disabled:opacity-50 disabled:shadow-none"
          >
            {generateMutation.isPending ? 'Генерируем...' : '✨ Сгенерировать'}
          </button>
        </div>

        {/* Превью сгенерированного теста */}
        {generated && (
          <>
            <div className="glass rounded-2xl p-4 space-y-2">
              <h3 className="font-semibold text-slate-800 text-sm">
                Готово: {generated.students.length} персональных тестов
              </h3>
              {generated.usage_stats && (
                <p className="text-xs text-slate-500">
                  Уникальных заданий:{' '}
                  {generated.usage_stats.unique_tasks_used} из{' '}
                  {generated.usage_stats.total_tasks_used} использований
                  {' · '}
                  макс. повтор: {generated.usage_stats.max_usage}
                </p>
              )}
            </div>

            <div className="space-y-2">
              {generated.students.map((s) => (
                <details
                  key={s.student_id}
                  className="glass rounded-2xl p-3 group"
                >
                  <summary className="cursor-pointer flex items-center
                                      justify-between list-none">
                    <span className="font-medium text-slate-800 text-sm truncate">
                      {s.full_name}
                    </span>
                    <span className="text-xs text-slate-500 shrink-0 ml-2">
                      {s.tasks.length} заданий
                    </span>
                  </summary>
                  <div className="mt-3 space-y-1.5 pl-1">
                    {s.tasks.map((t, i) => (
                      <div
                        key={t.task_id}
                        className="text-xs text-slate-600 flex gap-2"
                      >
                        <span className="font-mono text-slate-400 shrink-0">
                          {i + 1}.
                        </span>
                        <span className="font-mono text-brand-600 shrink-0">
                          {t.code}
                        </span>
                        <span className="text-slate-500 truncate">
                          {t.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </div>

            {/* Форма сохранения */}
            {!savedId && (
              <div className="glass-strong rounded-3xl p-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Название теста
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-4 py-3 bg-white/70 border border-white/80
                               rounded-2xl text-base
                               focus:outline-none focus:ring-2 focus:ring-brand-400
                               focus:bg-white transition-all"
                    disabled={isBusy}
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={isBusy}
                    className="flex-1 bg-white/80 hover:bg-white text-slate-700
                               font-semibold py-3 rounded-2xl transition-colors
                               disabled:opacity-50"
                  >
                    {saveMutation.isPending ? 'Сохраняем...' : '💾 Сохранить'}
                  </button>
                  <button
                    onClick={handleGenerate}
                    disabled={isBusy}
                    className="px-5 bg-slate-100 hover:bg-slate-200
                               text-slate-600 font-medium rounded-2xl
                               transition-colors disabled:opacity-50 text-sm"
                  >
                    ↻ Заново
                  </button>
                </div>
              </div>
            )}

            {/* Отправка */}
            {savedId && (
              <div className="glass-tinted rounded-3xl p-5 space-y-4
                              ring-1 ring-white/40">
                <div>
                  <p className="text-sm font-semibold text-slate-800">
                    ✓ Черновик сохранён
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Отправь тест ученикам, чтобы они увидели его в приложении
                  </p>
                </div>
                <button
                  onClick={handleSend}
                  disabled={sendMutation.isPending}
                  className="w-full bg-hyper text-white font-semibold py-3.5
                             rounded-2xl shadow-lg shadow-brand-500/30
                             hover:shadow-xl transition-all disabled:opacity-50"
                >
                  {sendMutation.isPending
                    ? 'Отправляем...'
                    : '🚀 Отправить ученикам'}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}