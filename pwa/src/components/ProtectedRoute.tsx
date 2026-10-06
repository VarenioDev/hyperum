import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Если true — требуем роль owner/admin */
  teacherOnly?: boolean
  /** Если true — требуем роль student */
  studentOnly?: boolean
}

export default function ProtectedRoute({
  children,
  teacherOnly = false,
  studentOnly = false,
}: Props) {
  const { isAuthenticated, isLoading, user } = useAuthStore()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка...</div>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  const isTeacher = user.role === 'owner' || user.role === 'admin'

  if (teacherOnly && !isTeacher) {
    return <Navigate to="/dashboard" replace />
  }

  if (studentOnly && user.role !== 'student') {
    return <Navigate to="/teacher" replace />
  }

  return <>{children}</>
}