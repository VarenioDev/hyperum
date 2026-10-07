import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAssignmentTasks,
  type AssignmentTask,
} from '../api/assignments'
import { submitResponse, type ResponseResult } from '../api/responses'
import { getErrorMessage } from '../api/client'

type TaskState = {
  answer: string
  result: ResponseResult | null
  submitted: boolean
}

export default function Assignment() {
  const { id: assignmentId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [currentIndex, setCurrentIndex] = useState(0)
  const [taskStates, setTaskStates] = useState<Record<string, TaskState>>({})
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')

  const startTimeRef = useRef<number>(Date.now())

  const { data: tasks, isLoading, error: loadError } = useQuery({
    queryKey: ['assignment', assignmentId, 'tasks'],
    queryFn: () => getAssignmentTasks(assignmentId!),
    enabled: !!assignmentId,
  })

  const currentTask: AssignmentTask | undefined = tasks?.[currentIndex]
  const isLast = tasks ? currentIndex === tasks.length - 1 : false

  // Сбросить таймер при смене задания + восстановить ответ из стейта
  useEffect(() => {
    startTimeRef.current = Date.now()
    if (currentTask) {
      const state = taskStates[currentTask.task_id]
      setAnswer(state?.answer || '')
    }
    setError('')
  }, [currentIndex, currentTask?.task_id])

  const submitMutation = useMutation({
    mutationFn: submitResponse,
    onSuccess: (result, variables) => {
      setTaskStates((prev) => ({
        ...prev,
        [variables.task_id]: {
          answer: variables.answer,
          result,
          submitted: true,
        },
      }))
      queryClient.invalidateQueries({ queryKey: ['mastery', 'me'] })
      queryClient.invalidateQueries({ queryKey: ['assignments', 'my'] })
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const currentState = currentTask ? taskStates[currentTask.task_id] : null

  // Прогресс
  const progressStats = useMemo(() => {
    if (!tasks) return { solved: 0, skipped: 0, total: 0 }
    let solved = 0, skipped = 0
    for (const t of tasks) {
      const st = taskStates[t.task_id]
      if (st?.submitted && !st.result?.skipped) solved++
      else if (st?.submitted && st.result?.skipped) skipped++
    }
    return { solved, skipped, total: tasks.length }
  }, [tasks, taskStates])

  // ─── Действия ────────────────────────────────────────

  const handleSubmit = () => {
    if (!currentTask) return
    if (!answer.trim()) {
      setError('Введите ответ')
      return
    }
    const timeSec = Math.round((Date.now() - startTimeRef.current) / 1000)
    submitMutation.mutate({
      task_id: currentTask.task_id,
      answer: answer.trim(),
      time_sec: timeSec,
    })
  }

  const handleSkip = () => {
    if (!currentTask) return
    const timeSec = Math.round((Date.now() - startTimeRef.current) / 1000)
    submitMutation.mutate({
      task_id: currentTask.task_id,
      answer: '',
      time_sec: timeSec,
      skipped: true,
    })
  }

  const goNext = () => {
    if (!isLast) setCurrentIndex((i) => i + 1)
  }
  const goPrev = () => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1)
  }
  const goTo = (idx: number) => setCurrentIndex(idx)

  const handleFinish = () => {
    navigate('/dashboard', { replace: true })
  }

  const allAnswered =
    tasks && tasks.every((t) => taskStates[t.task_id]?.submitted)

  // ─── Рендер ──────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка заданий...</div>
      </div>
    )
  }

  if (loadError || !tasks) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="text-5xl mb-4">😕</div>
        <p className="text-slate-700 mb-2">Не удалось загрузить задания</p>
        <button onClick={() => navigate('/dashboard')}
          className="text-brand-600 hover:underline text-sm mt-2">
          ← Вернуться на главную
        </button>
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="text-5xl mb-4">📭</div>
        <p className="text-slate-700 mb-2">В этом тесте нет заданий</p>
        <button onClick={() => navigate('/dashboard')}
          className="text-brand-600 hover:underline text-sm mt-2">
          ← Вернуться на главную
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen pb-32">
      {/* Header */}
      <header className="glass sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              ← Выйти
            </button>
            <span className="text-xs text-slate-500">
              {progressStats.solved + progressStats.skipped} из {progressStats.total}
            </span>
          </div>

          {/* Точки-индикаторы заданий */}
          <div className="flex gap-1.5 justify-center">
            {tasks.map((t, idx) => {
              const st = taskStates[t.task_id]
              const isCurrent = idx === currentIndex
              let bg = 'bg-slate-200'
              if (st?.submitted) {
                bg = st.result?.skipped
                  ? 'bg-slate-400'
                  : st.result?.correct
                  ? 'bg-mastery-strong'
                  : 'bg-mastery-weak'
              }
              return (
                <button
                  key={t.task_id}
                  onClick={() => goTo(idx)}
                  className={`h-1.5 rounded-full transition-all ${
                    isCurrent ? 'w-8' : 'w-4'
                  } ${bg} ${isCurrent ? 'ring-2 ring-brand-400 ring-offset-1' : ''}`}
                  aria-label={`Задание ${idx + 1}`}
                />
              )
            })}
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        {currentTask && (
          <>
            <p className="text-xs text-slate-400 mb-2 text-center">
              Задание {currentIndex + 1} из {tasks.length} · {currentTask.code}
            </p>

            {/* Текст задания */}
            <div className="glass-strong rounded-3xl p-6 mb-4">
              <p className="text-base text-slate-800 whitespace-pre-wrap leading-relaxed">
                {currentTask.text}
              </p>
            </div>

            {/* Поле ответа / результат */}
            {!currentState?.submitted ? (
              <>
                <div className="mb-4">
                  <input
                    type="text"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSubmit()
                    }}
                    autoFocus
                    disabled={submitMutation.isPending}
                    className="w-full px-4 py-3 bg-white/70 border border-white/80
                               rounded-2xl text-base
                               focus:outline-none focus:ring-2 focus:ring-brand-400
                               focus:bg-white transition-all
                               disabled:opacity-60"
                    placeholder="Введите ответ..."
                  />
                  <p className="text-xs text-slate-400 mt-2">
                    Без пробелов и единиц измерения
                  </p>
                </div>

                {error && (
                  <div className="bg-red-50/80 border border-red-200 rounded-2xl
                                  p-3 text-sm text-red-700 mb-4">
                    {error}
                  </div>
                )}

                <div className="flex gap-2">
                  {currentIndex > 0 && (
                    <button
                      onClick={goPrev}
                      disabled={submitMutation.isPending}
                      className="px-4 bg-white/70 hover:bg-white text-slate-700
                                 font-medium rounded-2xl transition-colors
                                 disabled:opacity-50"
                    >
                      ←
                    </button>
                  )}
                  <button
                    onClick={handleSubmit}
                    disabled={submitMutation.isPending}
                    className="flex-1 bg-hyper text-white font-semibold py-3.5
                               rounded-2xl shadow-lg shadow-brand-500/30
                               hover:shadow-xl transition-all disabled:opacity-50"
                  >
                    {submitMutation.isPending ? 'Проверяем...' : 'Проверить'}
                  </button>
                  <button
                    onClick={handleSkip}
                    disabled={submitMutation.isPending}
                    className="px-4 bg-white/70 hover:bg-white text-slate-500
                               font-medium rounded-2xl transition-colors
                               disabled:opacity-50 text-sm"
                  >
                    Пропустить
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* Результат inline */}
                <div
                  className={`rounded-2xl p-4 mb-4 ${
                    currentState.result?.skipped
                      ? 'bg-slate-100 border border-slate-200'
                      : currentState.result?.correct
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {currentState.result?.skipped
                        ? '⏭'
                        : currentState.result?.correct
                        ? '✅'
                        : '❌'}
                    </span>
                    <span
                      className={`font-semibold ${
                        currentState.result?.skipped
                          ? 'text-slate-600'
                          : currentState.result?.correct
                          ? 'text-mastery-strong'
                          : 'text-mastery-weak'
                      }`}
                    >
                      {currentState.result?.skipped
                        ? 'Пропущено'
                        : currentState.result?.correct
                        ? 'Верно!'
                        : 'Неверно'}
                    </span>
                  </div>

                  {!currentState.result?.skipped && (
                    <div className="text-sm text-slate-700 space-y-1">
                      <p>
                        <span className="text-slate-500">Ваш ответ:</span>{' '}
                        <strong>{currentState.answer || '—'}</strong>
                      </p>
                      {!currentState.result?.correct && currentState.result?.expected && (
                        <p>
                          <span className="text-slate-500">Правильный ответ:</span>{' '}
                          <strong>{currentState.result.expected}</strong>
                        </p>
                      )}
                      {currentState.result?.new_mastery !== null &&
                       currentState.result?.new_mastery !== undefined && (
                        <p className="text-xs text-slate-500 pt-2 border-t border-slate-200 mt-2">
                          Уровень освоения навыка: {Math.round((currentState.result.new_mastery || 0) * 100)}%
                        </p>
                      )}
                    </div>
                  )}

                  {currentState.result?.skipped && (
                    <p className="text-xs text-slate-500">
                      Ты можешь вернуться к этому заданию позже через индикатор сверху.
                    </p>
                  )}
                </div>

                {/* Кнопки навигации */}
                <div className="flex gap-2">
                  {currentIndex > 0 && (
                    <button
                      onClick={goPrev}
                      className="px-5 bg-white/70 hover:bg-white text-slate-700
                                 font-medium rounded-2xl transition-colors"
                    >
                      ← Назад
                    </button>
                  )}
                  {!isLast && (
                    <button
                      onClick={goNext}
                      className="flex-1 bg-hyper text-white font-semibold py-3.5
                                 rounded-2xl shadow-lg shadow-brand-500/30
                                 hover:shadow-xl transition-all"
                    >
                      Дальше →
                    </button>
                  )}
                  {isLast && allAnswered && (
                    <button
                      onClick={handleFinish}
                      className="flex-1 bg-hyper text-white font-semibold py-3.5
                                 rounded-2xl shadow-lg shadow-brand-500/30
                                 hover:shadow-xl transition-all"
                    >
                      🎉 Завершить тест
                    </button>
                  )}
                  {isLast && !allAnswered && (
                    <div className="flex-1 bg-white/70 rounded-2xl py-3.5 px-4
                                    text-center text-xs text-slate-500">
                      Остались непройденные задания — вернись через индикатор
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}