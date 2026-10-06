import { useNavigate } from 'react-router-dom'
import { logout } from '../api/auth'
import { useAuthStore } from '../stores/authStore'
import type { ReactNode } from 'react'

interface Props {
  title?: string
  showBack?: boolean
  backTo?: string
  right?: ReactNode
}

export default function Header({
  title,
  showBack = false,
  backTo = '/dashboard',
  right,
}: Props) {
  const navigate = useNavigate()
  const setUser = useAuthStore((s) => s.setUser)

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      setUser(null)
      navigate('/login', { replace: true })
    }
  }

  return (
    <header className="sticky top-0 z-20 glass border-b-0">
      <div className="max-w-2xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {showBack ? (
            <button
              onClick={() => navigate(backTo)}
              className="text-sm text-slate-500 hover:text-brand-600 font-medium"
            >
              ← Назад
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xl">🧠</span>
              <span className="font-bold text-hyper">ГиперУм</span>
            </div>
          )}

          {title && (
            <h1 className="text-base font-semibold text-slate-800">
              {title}
            </h1>
          )}

          {right || (
            <button
              onClick={handleLogout}
              className="text-xs text-slate-500 hover:text-red-500
                         font-medium transition-colors"
            >
              Выйти
            </button>
          )}
        </div>
      </div>
    </header>
  )
}