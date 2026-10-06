import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getGroupByCode, joinByCode } from '../api/groups'
import { getErrorMessage } from '../api/client'

export default function Join() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [code, setCode] = useState(searchParams.get('code')?.toUpperCase() || '')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState<string | null>(null)

  // Автозагрузка класса, если код в URL
  const { data: group, isLoading: loadingGroup, error: groupError } = useQuery({
    queryKey: ['group-by-code', code],
    queryFn: () => getGroupByCode(code),
    enabled: code.length >= 4,
    retry: false,
  })

  const joinMutation = useMutation({
    mutationFn: joinByCode,
    onSuccess: (data) => {
      setSuccess(data.group_name)
      setError('')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!code || !fullName || !email || !password) {
      setError('Заполните все поля')
      return
    }
    if (password.length < 6) {
      setError('Пароль должен быть не менее 6 символов')
      return
    }
    joinMutation.mutate({ code, full_name: fullName, email, password })
  }

  // ─── Экран успеха ───────────────────────────────────
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-brand-300/40 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-purple-300/40 blur-3xl pointer-events-none" />

        <div className="max-w-sm w-full glass-strong rounded-3xl p-6 text-center relative">
          <div className="text-6xl mb-4">📬</div>
          <h1 className="text-2xl font-bold text-hyper mb-3">
            Заявка отправлена
          </h1>
          <p className="text-slate-600 text-sm mb-4">
            Твоя заявка на вступление в класс <strong>{success}</strong> отправлена.
          </p>
          <p className="text-slate-500 text-xs mb-6">
            Учитель подтвердит её в ближайшее время. После этого
            сможешь войти с указанным email и паролем.
          </p>
          <Link
            to="/login"
            className="block w-full bg-hyper text-white font-semibold py-3.5
                       rounded-2xl shadow-lg shadow-brand-500/30
                       hover:shadow-xl transition-all"
          >
            Перейти ко входу
          </Link>
        </div>
      </div>
    )
  }

  // ─── Форма регистрации ──────────────────────────────
  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-brand-300/40 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-purple-300/40 blur-3xl pointer-events-none" />

      <div className="max-w-sm w-full relative">
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">🎓</div>
          <h1 className="text-3xl font-bold text-hyper">Регистрация</h1>
          <p className="text-slate-500 text-sm mt-2">
            Введи код класса от учителя
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="glass-strong rounded-3xl p-6 space-y-4"
        >
          {/* Код класса */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Код класса
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="A7K9P2"
              maxLength={10}
              autoComplete="off"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base tracking-widest font-mono text-center
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={joinMutation.isPending}
            />
            {code.length >= 4 && (
              <div className="mt-2 text-xs">
                {loadingGroup && (
                  <span className="text-slate-400">Проверяем...</span>
                )}
                {group && (
                  <div className="glass-tinted rounded-xl p-3">
                    <p className="text-slate-700">
                      ✅ Класс: <strong>{group.name}</strong>
                    </p>
                    <p className="text-slate-500 mt-0.5">
                      Учитель: {group.teacher_name}
                    </p>
                  </div>
                )}
                {groupError && (
                  <span className="text-red-500">Код не найден</span>
                )}
              </div>
            )}
          </div>

          {/* ФИО */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              ФИО
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Иванов Иван Иванович"
              autoComplete="name"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={joinMutation.isPending}
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@lyceum.ru"
              autoComplete="email"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={joinMutation.isPending}
            />
          </div>

          {/* Пароль */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Пароль
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="минимум 6 символов"
              autoComplete="new-password"
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={joinMutation.isPending}
            />
          </div>

          {error && (
            <div className="bg-red-50/80 border border-red-200 rounded-2xl p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={joinMutation.isPending || !group}
            className="w-full bg-hyper text-white font-semibold py-3.5
                       rounded-2xl shadow-lg shadow-brand-500/30
                       hover:shadow-xl transition-all
                       disabled:opacity-50 disabled:shadow-none"
          >
            {joinMutation.isPending ? 'Отправляем...' : 'Зарегистрироваться'}
          </button>

          <p className="text-center text-xs text-slate-500 pt-2">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-brand-600 font-medium hover:underline">
              Войти
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}