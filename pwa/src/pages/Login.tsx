import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { login, me } from '../api/auth'
import { getErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/authStore'


export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const navigate = useNavigate()
  const location = useLocation()
  const setUser = useAuthStore((s) => s.setUser)

  const defaultPath = '/dashboard'
  const from = (location.state as any)?.from?.pathname || defaultPath 

  const loginMutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: async () => {
      try {
        const data = await me()
        setUser(data.user)

        // Редирект по роли
        const isTeacher = data.user.role === 'owner' || data.user.role === 'admin'
        const target = from !== '/dashboard' ? from : (isTeacher ? '/teacher' : '/dashboard')
        navigate(target, { replace: true })
      } catch {
        setError('Не удалось загрузить профиль')
      }
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email || !password) {
      setError('Заполните email и пароль')
      return
    }
    loginMutation.mutate()
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">

      {/* Декоративные блобы на фоне */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full
                      bg-brand-300/40 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full
                      bg-purple-300/40 blur-3xl pointer-events-none" />

      <div className="max-w-sm w-full relative">

        {/* Логотип */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-4 drop-shadow-sm">🧠</div>
          <h1 className="text-4xl font-bold text-hyper tracking-tight">
            ГиперУм
          </h1>
          <p className="text-slate-500 mt-2 text-sm font-medium">
            Учись по-своему
          </p>
        </div>

        {/* Форма — стеклянная карточка */}
        <form
          onSubmit={handleSubmit}
          className="glass-strong rounded-3xl p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              placeholder="you@lyceum.ru"
              disabled={loginMutation.isPending}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Пароль
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              placeholder="••••••••"
              disabled={loginMutation.isPending}
            />
          </div>

          {error && (
            <div className="bg-red-50/80 border border-red-200 rounded-2xl p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="w-full bg-hyper text-white font-semibold py-3.5
                       rounded-2xl transition-all shadow-lg shadow-brand-500/30
                       hover:shadow-xl hover:shadow-brand-500/40
                       disabled:opacity-50 disabled:shadow-none"
          >
            {loginMutation.isPending ? 'Вход...' : 'Войти'}
          </button>
                    <p className="text-center text-xs text-slate-500 pt-2">
            Нет аккаунта?{' '}
            <Link
                to="/join"
                className="text-brand-600 font-medium hover:underline"
            >
                Зарегистрироваться по коду
            </Link>
            </p>
        </form>

        <p className="text-center text-xs text-slate-400 mt-6 font-medium">
          ГиперУм · 2026
        </p>
      </div>
    </div>
  )
}