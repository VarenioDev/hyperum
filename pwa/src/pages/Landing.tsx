import { useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { startDemo } from '../api/demo'
import { getErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export default function Landing() {
  const navigate = useNavigate()
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const user = useAuthStore((s) => s.user)
  const isTeacher = user?.role === 'owner' || user?.role === 'admin'

  const startMutation = useMutation({
    mutationFn: startDemo,
    onSuccess: (data) => {
      // Сохраняем сессию в sessionStorage — чтобы /demo/test знал что делать
      sessionStorage.setItem(
        'demo_session',
        JSON.stringify({
          session_id: data.session_id,
          topic: data.topic,
          tasks: data.tasks,
          reasoning: data.reasoning,
        })
      )
      navigate('/demo/test')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleStart = () => {
    setError('')
    if (description.length < 20) {
      setError('Опиши чуть подробнее — минимум 20 символов')
      return
    }
    startMutation.mutate(description)
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Фоновые блобы */}
      <div className="fixed -top-32 -left-32 w-96 h-96 rounded-full
                      bg-brand-300/40 blur-3xl pointer-events-none" />
      <div className="fixed -bottom-32 -right-32 w-96 h-96 rounded-full
                      bg-purple-300/40 blur-3xl pointer-events-none" />

      {/* Header — минимальный */}
      <header className="relative z-10 max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🧠</span>
          <span className="font-bold text-hyper text-xl">HyperUm</span>
        </div>

            {user ? (
            <Link
                to={isTeacher ? '/teacher' : '/dashboard'}
                className="text-sm font-medium text-brand-600 hover:text-brand-700"
            >
                Моё приложение →
            </Link>
            ) : (
            <Link
                to="/login"
                className="text-sm font-medium text-slate-600 hover:text-brand-600"
            >
                Войти →
            </Link>
            )}
      </header>

      {/* Hero */}
      <section className="relative z-10 max-w-3xl mx-auto px-6 pt-12 pb-16 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 leading-tight">
          Персональные задания —<br />
          <span className="text-hyper">каждому ученику</span>
        </h1>
        <p className="text-slate-600 text-lg mt-6 max-w-xl mx-auto">
          HyperUm строит граф знаний каждого ученика и подбирает задания
          в его зоне ближайшего развития. Одна кнопка — N персональных тестов.
        </p>
      </section>

      {/* Killer-feature: демо */}
      <section className="relative z-10 max-w-2xl mx-auto px-6 pb-16">
        <div className="glass-strong rounded-3xl p-6 sm:p-8">
          <div className="text-center mb-6">
            <div className="text-3xl mb-2">✨</div>
            <h2 className="text-2xl font-bold text-slate-800">
              Попробуй прямо сейчас
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Без регистрации. Опиши, что знаешь и не знаешь — получишь
              персональный тест и свой граф знаний.
            </p>
          </div>

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Например: я хорошо знаю системы счисления, умею переводить из 10 в 2. Плохо разбираюсь в кодировании изображений и звука."
            rows={4}
            className="w-full px-4 py-3 bg-white/70 border border-white/80
                       rounded-2xl text-base placeholder:text-slate-400
                       focus:outline-none focus:ring-2 focus:ring-brand-400
                       focus:bg-white transition-all resize-none"
            disabled={startMutation.isPending}
          />

          {error && (
            <div className="bg-red-50/80 border border-red-200 rounded-2xl
                            p-3 text-sm text-red-700 mt-3">
              {error}
            </div>
          )}

          <button
            onClick={handleStart}
            disabled={startMutation.isPending || description.length < 20}
            className="w-full mt-4 bg-hyper text-white font-semibold py-4
                       rounded-2xl shadow-lg shadow-brand-500/30
                       hover:shadow-xl transition-all
                       disabled:opacity-50 disabled:shadow-none
                       flex items-center justify-center gap-2"
          >
            {startMutation.isPending ? (
              <>
                <span className="sparkle-container text-lg leading-none">
                  <span className="sparkle">✨</span>
                  <span className="sparkle">✨</span>
                  <span className="sparkle">✨</span>
                </span>
                <span>Готовим персональный тест...</span>
              </>
            ) : (
              '✨ Получить тест'
            )}
          </button>

          <p className="text-xs text-slate-400 text-center mt-3">
            Занимает ~15 секунд. Ничего не сохраняем — сессия живёт час.
          </p>
        </div>
      </section>

      {/* Как это работает */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 pb-24">
        <h2 className="text-2xl font-bold text-slate-800 text-center mb-10">
          Как это работает
        </h2>
        <div className="grid gap-6 sm:grid-cols-3">
          <FeatureCard
            icon="🧬"
            title="Граф знаний"
            text="Система строит модель каждого ученика: какие навыки освоены, какие в процессе, какие ещё впереди."
          />
          <FeatureCard
            icon="🎯"
            title="Персональный подбор"
            text="Задания подбираются в зоне ближайшего развития — не слишком легко, не слишком сложно."
          />
          <FeatureCard
            icon="🚫"
            title="Без prerequisite-провалов"
            text="Не даём задание, пока не выполнены все предпосылки. Ученик не застревает."
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 text-center pb-8 text-xs text-slate-400">
        HyperUm · 2026
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  text,
}: {
  icon: string
  title: string
  text: string
}) {
  return (
    <div className="glass rounded-2xl p-6 text-center">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="font-semibold text-slate-800 mb-2">{title}</h3>
      <p className="text-sm text-slate-600 leading-relaxed">{text}</p>
    </div>
  )
}