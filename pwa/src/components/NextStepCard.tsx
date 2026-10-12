import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { submitResponse, type ResponseResult } from '../api/responses'
import { getErrorMessage } from '../api/client'
import type { NextTaskRecommendation } from '../api/recommendations'

interface Props {
  recommendation: NextTaskRecommendation
}

export default function NextStepCard({ recommendation }: Props) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<ResponseResult | null>(null)
  const [error, setError] = useState('')
  const [startedAt, setStartedAt] = useState(0)

  const submitMutation = useMutation({
    mutationFn: submitResponse,
    onSuccess: (data) => {
      setResult(data)
      // Обновляем mastery и рекомендации
      queryClient.invalidateQueries({ queryKey: ['mastery'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const openModal = () => {
    setOpen(true)
    setAnswer('')
    setResult(null)
    setError('')
    setStartedAt(Date.now())
  }

  const closeModal = () => {
    setOpen(false)
    setAnswer('')
    setResult(null)
    setError('')
  }

  const handleSubmit = () => {
    if (!answer.trim()) {
      setError('Введите ответ')
      return
    }
    const timeSec = Math.round((Date.now() - startedAt) / 1000)
    submitMutation.mutate({
      task_id: recommendation.task.task_id,
      answer: answer.trim(),
      time_sec: timeSec,
      // Без assignment_id — свободная практика
    })
  }

  return (
    <>
      <section className="glass-strong rounded-3xl p-5">
        <div className="flex items-start gap-3 mb-4">
          <span className="text-2xl">🎯</span>
          <div className="flex-1 min-w-0">
            <p className="text-xs uppercase tracking-wide text-brand-600 font-semibold mb-1">
              Следующий шаг
            </p>
            <h2 className="text-base font-semibold text-slate-800">
              {recommendation.skill_name}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {recommendation.reason}
            </p>
          </div>
        </div>

        <button
          onClick={openModal}
          className="w-full bg-hyper text-white font-semibold py-3
                     rounded-2xl shadow-lg shadow-brand-500/30
                     hover:shadow-xl transition-all"
        >
          Решить сейчас
        </button>
      </section>

      {/* Модалка */}
      {open && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="bg-white rounded-3xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <span className="text-xs font-mono text-slate-400">
                {recommendation.task.code}
              </span>
              <button
                onClick={closeModal}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-base text-slate-800 leading-relaxed whitespace-pre-wrap">
              {recommendation.task.text}
            </p>

            {!result ? (
              <>
                <input
                  type="text"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit() }}
                  autoFocus
                  disabled={submitMutation.isPending}
                  placeholder="Введите ответ..."
                  className="w-full px-4 py-3 bg-white/70 border border-slate-200
                             rounded-2xl text-base
                             focus:outline-none focus:ring-2 focus:ring-brand-400
                             disabled:opacity-60"
                />
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-2xl p-3 text-sm text-red-700">
                    {error}
                  </div>
                )}
                <button
                  onClick={handleSubmit}
                  disabled={submitMutation.isPending}
                  className="w-full bg-hyper text-white font-semibold py-3
                             rounded-2xl disabled:opacity-50"
                >
                  {submitMutation.isPending ? 'Проверяем...' : 'Проверить'}
                </button>
              </>
            ) : (
              <>
                <div className={`rounded-2xl p-4 ${
                  result.correct
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {result.correct ? '✅' : '❌'}
                    </span>
                    <span className={`font-semibold ${
                      result.correct ? 'text-mastery-strong' : 'text-mastery-weak'
                    }`}>
                      {result.correct ? 'Верно!' : 'Неверно'}
                    </span>
                  </div>
                  {!result.correct && result.expected && (
                    <p className="text-sm text-slate-700">
                      <span className="text-slate-500">Правильный ответ:</span>{' '}
                      <strong>{result.expected}</strong>
                    </p>
                  )}
                </div>
                <button
                  onClick={closeModal}
                  className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700
                             font-medium py-3 rounded-2xl transition-colors"
                >
                  Готово
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}