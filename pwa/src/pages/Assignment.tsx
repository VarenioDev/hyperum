import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAssignmentTasks,
  type AssignmentTask,
} from '../api/assignments'
import { submitResponse, type ResponseResult } from '../api/responses'
import { getErrorMessage } from '../api/client'
import Feedback from '../components/Feedback'

export default function Assignment() {
  const { id: assignmentId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [currentIndex, setCurrentIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<ResponseResult | null>(null)
  const [error, setError] = useState('')

  // Таймер: старт при показе задания
  const startTimeRef = useRef<number>(Date.now())

  const {
    data: tasks,
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ['assignment', assignmentId, 'tasks'],
    queryFn: () => getAssignmentTasks(assignmentId!),
    enabled: !!assignmentId,
  })

  // Сбросить таймер при смене задания
  useEffect(() => {
    startTimeRef.current = Date.now()
    setAnswer('')
    setFeedback(null)
    setError('')
  }, [currentIndex])

  const submitMutation = useMutation({
    mutationFn: submitResponse,
    onSuccess: (result) => {
      setFeedback(result)
      // Инвалидируем mastery и assignments — чтобы дашборд обновился
      queryClient.invalidateQueries({ queryKey: ['mastery', 'me'] })
      queryClient.invalidateQueries({ queryKey: ['assignments', 'my'] })
    },
    onError: (err) => {
      setError(getErrorMessage(err))
    },
  })

  const currentTask: AssignmentTask | undefined = tasks?.[currentIndex]
  const isLast = tasks ? currentIndex === tasks.length - 1 : false

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

  const handleNext = () => {
    if (isLast) {
      navigate('/dashboard', { replace: true })
    } else {
      setCurrentIndex((i) => i + 1)
    }
  }

  // ─── Загрузка ────────────────────────────────────────

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
        <button
          onClick={() => navigate('/dashboard')}
          className="text-brand-600 hover:underline text-sm mt-2"
        >
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
        <button
          onClick={() => navigate('/dashboard')}
          className="text-brand-600 hover:underline text-sm mt-2"
        >
          ← Вернуться на главную
        </button>
      </div>
    )
  }

  // ─── Рендер ──────────────────────────────────────────

  const progress = ((currentIndex + (feedback ? 1 : 0)) / tasks.length) * 100

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
              Задание {currentIndex + 1} из {tasks.length}
            </span>
          </div>
          <div className="bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-brand-500 h-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        {currentTask && (
          <>
            {/* Код задания (для отладки/удобства) */}
            <p className="text-xs text-slate-400 mb-2">
              {currentTask.code}
            </p>

            {/* Текст задания */}
            <div className="glass-strong rounded-3xl p-6 mb-6">
              <p className="text-base text-slate-800 whitespace-pre-wrap leading-relaxed">
                {currentTask.text}
              </p>
            </div>

            {/* Поле ответа */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Ваш ответ
              </label>
              <input
                type="text"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !feedback) handleSubmit()
                }}
                autoFocus
                disabled={!!feedback || submitMutation.isPending}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl
                           focus:outline-none focus:ring-2 focus:ring-brand-500
                           focus:border-transparent text-base
                           disabled:bg-slate-50 disabled:text-slate-500"
                placeholder="Введите ответ..."
              />
              <p className="text-xs text-slate-400 mt-2">
                Пишите ответ без пробелов и единиц измерения
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700 mb-4">
                {error}
              </div>
            )}

            {/* Кнопка проверки */}
            {!feedback && (
              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
                className="w-full bg-hyper text-white font-semibold py-3.5 rounded-2xl shadow-lg shadow-brand-500/30
                             transition-colors"
              >
                {submitMutation.isPending ? 'Проверяем...' : 'Проверить'}
              </button>
            )}
          </>
        )}
      </main>

      {/* Модальное окно с результатом */}
      {feedback && (
        <Feedback
          result={feedback}
          onNext={handleNext}
          isLast={isLast}
        />
      )}
    </div>
  )
}