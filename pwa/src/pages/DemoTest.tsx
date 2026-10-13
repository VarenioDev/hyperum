import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  submitDemoResponse,
  getDemoGraph,
  type DemoTask,
  type DemoResponseResult,
} from '../api/demo'
import { getErrorMessage } from '../api/client'
import GraphView from '../components/GraphView'
import SkillCard from '../components/SkillCard'
import type { GraphNode, StudentGraph } from '../api/graph'
import LatexText from '../components/LatexText'

interface DemoSession {
  session_id: string
  topic: string
  tasks: DemoTask[]
  reasoning: string
}

type TaskState = {
  answer: string
  result: DemoResponseResult | null
  submitted: boolean
}

export default function DemoTest() {
  const navigate = useNavigate()

  const [session, setSession] = useState<DemoSession | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [taskStates, setTaskStates] = useState<Record<string, TaskState>>({})
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'solving' | 'graph'>('solving')
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const startTimeRef = useRef<number>(Date.now())

  // Загружаем сессию из sessionStorage при монтировании
  useEffect(() => {
    const raw = sessionStorage.getItem('demo_session')
    if (!raw) {
      navigate('/', { replace: true })
      return
    }
    try {
      const parsed = JSON.parse(raw) as DemoSession
      setSession(parsed)
    } catch {
      navigate('/', { replace: true })
    }
  }, [navigate])

  const currentTask: DemoTask | undefined = session?.tasks[currentIndex]
  const isLast = session ? currentIndex === session.tasks.length - 1 : false

  // Сброс поля при смене задания
  useEffect(() => {
    startTimeRef.current = Date.now()
    if (currentTask) {
      const st = taskStates[currentTask.task_id]
      setAnswer(st?.submitted ? st.answer : '')
    } else {
      setAnswer('')
    }
    setError('')
  }, [currentIndex, currentTask?.task_id, taskStates])

  const submitMutation = useMutation({
    mutationFn: submitDemoResponse,
    onSuccess: (result, variables) => {
      setTaskStates((prev) => ({
        ...prev,
        [variables.task_id]: {
          answer: variables.answer,
          result,
          submitted: true,
        },
      }))
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const currentState = currentTask ? taskStates[currentTask.task_id] : null

  const progressStats = useMemo(() => {
    if (!session) return { done: 0, total: 0 }
    let done = 0
    for (const t of session.tasks) {
      if (taskStates[t.task_id]?.submitted) done++
    }
    return { done, total: session.tasks.length }
  }, [session, taskStates])

  const allAnswered =
    session && session.tasks.every((t) => taskStates[t.task_id]?.submitted)

  // ─── Запрос графа (только в режиме graph) ──────────────
  const { data: graph, isLoading: graphLoading } = useQuery<StudentGraph>({
  queryKey: ['demo-graph', session?.session_id],
  queryFn: () => getDemoGraph(session!.session_id),
  enabled: mode === 'graph' && !!session,
})

  // ─── Действия ─────────────────────────────────────────

  const handleSubmit = () => {
    if (!currentTask || !session) return
    if (!answer.trim()) {
      setError('Введите ответ')
      return
    }
    const timeSec = Math.round((Date.now() - startTimeRef.current) / 1000)
    submitMutation.mutate({
      session_id: session.session_id,
      task_id: currentTask.task_id,
      answer: answer.trim(),
      time_sec: timeSec,
    })
  }

  const goNext = () => {
    if (!isLast) setCurrentIndex((i) => i + 1)
  }
  const goPrev = () => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1)
  }

  const handleShowGraph = () => {
    setMode('graph')
  }

  const handleRestart = () => {
    sessionStorage.removeItem('demo_session')
    navigate('/', { replace: true })
  }

  // ─── Рендер ───────────────────────────────────────────

  // Пока грузится sessionStorage
  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка...</div>
      </div>
    )
  }

  // Режим графа
  if (mode === 'graph') {
    return (
      <div className="min-h-screen relative overflow-hidden">
        <div className="fixed -top-32 -left-32 w-96 h-96 rounded-full
                        bg-brand-300/40 blur-3xl pointer-events-none" />
        <div className="fixed -bottom-32 -right-32 w-96 h-96 rounded-full
                        bg-purple-300/40 blur-3xl pointer-events-none" />

        <header className="relative z-10 max-w-2xl mx-auto px-6 py-6
                           flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🧠</span>
            <span className="font-bold text-hyper text-xl">HyperUm</span>
          </div>
          <button
            onClick={handleRestart}
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            Заново
          </button>
        </header>

        <main className="relative z-10 max-w-2xl mx-auto px-6 pb-16">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-900">
              Твой граф знаний
            </h1>
            <p className="text-slate-600 mt-2 text-sm">
              По теме «{session.topic}» · {graph?.nodes.filter(n => n.mastery !== null).length || 0} навыков оценено
            </p>
          </div>

          {graphLoading && (
            <div className="glass rounded-2xl p-8 text-center">
              <div className="text-slate-500">Строим граф...</div>
            </div>
          )}

          {graph && (
            <>
              {/* Легенда */}
              <div className="glass rounded-2xl p-4 mb-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <LegendItem
                    color="bg-mastery-strong"
                    label="Освоено"
                    count={graph.nodes.filter((n) => n.status === 'mastered').length}
                  />
                  <LegendItem
                    color="bg-mastery-medium"
                    label="В процессе"
                    count={graph.nodes.filter((n) => n.status === 'learning').length}
                  />
                  <LegendItem
                    color="bg-mastery-weak"
                    label="Слабо"
                    count={graph.nodes.filter((n) => n.status === 'weak').length}
                  />
                  <LegendItem
                    color="bg-slate-300"
                    label="Не изучалось"
                    count={graph.nodes.filter((n) => n.status === 'unknown').length}
                  />
                </div>
              </div>

              {/* Граф */}
              <GraphView
                graph={graph}
                onNodeClick={(node) => setSelectedNode(node)}
                height="calc(100vh - 420px)"
              />

              {/* CTA */}
              <div className="glass-strong rounded-3xl p-6 mt-6 text-center">
                <div className="text-3xl mb-3">🎓</div>
                <h2 className="text-xl font-bold text-slate-800 mb-2">
                  Хочешь такой же для своего класса?
                </h2>
                <p className="text-sm text-slate-600 mb-5">
                  Учителя подключают HyperUm бесплатно. Ученики
                  получают персональные задания, а учитель — видит
                  кто что знает.
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <Link
                    to="/login"
                    className="bg-hyper text-white font-semibold py-3 px-6
                               rounded-2xl shadow-lg shadow-brand-500/30
                               hover:shadow-xl transition-all"
                  >
                    Войти как учитель
                  </Link>
                  <button
                    onClick={handleRestart}
                    className="bg-white/70 hover:bg-white text-slate-700
                               font-medium py-3 px-6 rounded-2xl
                               transition-colors"
                  >
                    Пройти заново
                  </button>
                </div>
              </div>
            </>
          )}
        </main>

        {/* Карточка навыка */}
        {selectedNode && (
          <SkillCard
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
    )
  }

  // Режим решения
  return (
    <div className="min-h-screen pb-32 relative">
      <div className="fixed -top-32 -left-32 w-96 h-96 rounded-full
                      bg-brand-300/40 blur-3xl pointer-events-none" />

      {/* Header */}
      <header className="relative z-10 max-w-2xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <Link
            to="/"
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            ← Выйти
          </Link>
          <span className="text-xs text-slate-500">
            {progressStats.done} из {progressStats.total}
          </span>
        </div>

        {/* Точки-индикаторы */}
        <div className="flex gap-1.5 justify-center">
          {session.tasks.map((t, idx) => {
            const st = taskStates[t.task_id]
            const isCurrent = idx === currentIndex
            let bg = 'bg-slate-200'
            if (st?.submitted) {
              bg = st.result?.correct
                ? 'bg-mastery-strong'
                : 'bg-mastery-weak'
            }
            return (
              <div
                key={t.task_id}
                className={`h-1.5 rounded-full transition-all ${
                  isCurrent ? 'w-8' : 'w-4'
                } ${bg} ${
                  isCurrent ? 'ring-2 ring-brand-400 ring-offset-1' : ''
                }`}
              />
            )
          })}
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 max-w-2xl mx-auto px-6 py-4">
        {currentTask && (
          <>
            <p className="text-xs text-slate-400 mb-2 text-center">
              Задание {currentIndex + 1} из {session.tasks.length}
            </p>

                        <div className="glass-strong rounded-3xl p-6 mb-4">
              <LatexText
                text={currentTask.text}
                className="text-base text-slate-800"
              />
            </div>

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
                </div>

                {error && (
                  <div className="bg-red-50/80 border border-red-200 rounded-2xl
                                  p-3 text-sm text-red-700 mb-4">
                    {error}
                  </div>
                )}
              </>
            ) : (
              <div
                className={`rounded-2xl p-4 mb-4 ${
                  currentState.result?.correct
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">
                    {currentState.result?.correct ? '✅' : '❌'}
                  </span>
                  <span
                    className={`font-semibold ${
                      currentState.result?.correct
                        ? 'text-mastery-strong'
                        : 'text-mastery-weak'
                    }`}
                  >
                    {currentState.result?.correct ? 'Верно!' : 'Неверно'}
                  </span>
                </div>

                <div className="text-sm text-slate-700 space-y-1">
                  <p>
                    <span className="text-slate-500">Ваш ответ:</span>{' '}
                    <strong>{currentState.answer || '—'}</strong>
                  </p>
                  {!currentState.result?.correct &&
                    currentState.result?.expected && (
                      <p>
                        <span className="text-slate-500">
                          Правильный ответ:
                        </span>{' '}
                        <strong>{currentState.result.expected}</strong>
                      </p>
                    )}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Фиксированная нижняя панель */}
      <div className="fixed bottom-0 left-0 right-0 z-40 glass safe-bottom">
        <div className="max-w-2xl mx-auto px-6 py-3">
          {!currentState?.submitted ? (
            <div className="flex gap-2">
              {currentIndex > 0 && (
                <button
                  onClick={goPrev}
                  disabled={submitMutation.isPending}
                  className="px-4 py-3 bg-white/70 hover:bg-white text-slate-700
                             font-medium rounded-2xl transition-colors
                             disabled:opacity-50"
                >
                  ←
                </button>
              )}
              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
                className="flex-1 bg-hyper text-white font-semibold py-3
                           rounded-2xl shadow-lg shadow-brand-500/30
                           hover:shadow-xl transition-all disabled:opacity-50"
              >
                {submitMutation.isPending ? 'Проверяем...' : 'Проверить'}
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              {currentIndex > 0 && (
                <button
                  onClick={goPrev}
                  className="px-5 py-3 bg-white/70 hover:bg-white text-slate-700
                             font-medium rounded-2xl transition-colors"
                >
                  ← Назад
                </button>
              )}
              {!isLast && (
                <button
                  onClick={goNext}
                  className="flex-1 bg-hyper text-white font-semibold py-3
                             rounded-2xl shadow-lg shadow-brand-500/30
                             hover:shadow-xl transition-all"
                >
                  Дальше →
                </button>
              )}
              {isLast && allAnswered && (
                <button
                  onClick={handleShowGraph}
                  className="flex-1 bg-hyper text-white font-semibold py-3
                             rounded-2xl shadow-lg shadow-brand-500/30
                             hover:shadow-xl transition-all"
                >
                  🎉 Показать мой граф
                </button>
              )}
              {isLast && !allAnswered && (
                <div className="flex-1 bg-white/70 rounded-2xl py-3 px-4
                                text-center text-xs text-slate-500">
                  Остались непройденные — вернись через индикатор
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Вспомогательный компонент ──────────────────────────

function LegendItem({
  color,
  label,
  count,
}: {
  color: string
  label: string
  count: number
}) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${color} shrink-0`} />
      <span className="text-slate-600 flex-1">{label}</span>
      <span className="text-slate-400">{count}</span>
    </div>
  )
}