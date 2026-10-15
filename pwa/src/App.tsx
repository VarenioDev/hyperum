import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { me } from './api/auth'
import { useAuthStore } from './stores/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Join from './pages/Join'
import Dashboard from './pages/Dashboard'
import Assignment from './pages/Assignment'
import Graph from './pages/Graph'
import History from './pages/History'
import TeacherDashboard from './pages/teacher/TeacherDashboard'
import TeacherClass from './pages/teacher/TeacherClass'
import TeacherGenerate from './pages/teacher/TeacherGenerate'
import TeacherAssignment from './pages/teacher/TeacherAssignment'
import TeacherStudent from './pages/teacher/TeacherStudent'
import { useSwipeBack } from './hooks/useSwipeBack'
import Landing from './pages/Landing'
import DemoTest from './pages/DemoTest'

function App() {
  const setUser = useAuthStore((s) => s.setUser)
  const setLoading = useAuthStore((s) => s.setLoading)
  const user = useAuthStore((s) => s.user)

  useSwipeBack()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['me'],
    queryFn: me,
    retry: false,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (isLoading) {
      setLoading(true)
    } else if (isError || !data) {
      setUser(null)
    } else {
      setUser(data.user)
    }
  }, [data, isLoading, isError, setUser, setLoading])

  // Куда редиректить при заходе на "/"
  const homeRedirect = () => {
    if (!user) return '/login'
    return user.role === 'owner' || user.role === 'admin'
      ? '/teacher'
      : '/dashboard'
  }

  return (
    <Routes>
      {/* Публичные */}
      <Route path="/login" element={<Login />} />
      <Route path="/join" element={<Join />} />

      {/* Ученик */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute studentOnly>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/assignment/:id"
        element={
          <ProtectedRoute>
            <Assignment />
          </ProtectedRoute>
        }
      />
      <Route
        path="/graph"
        element={
          <ProtectedRoute>
            <Graph />
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <History />
          </ProtectedRoute>
        }
      />

      {/* Учитель */}
      <Route
        path="/teacher"
        element={
          <ProtectedRoute teacherOnly>
            <TeacherDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/teacher/class/:id"
        element={
          <ProtectedRoute teacherOnly>
            <TeacherClass />
          </ProtectedRoute>
        }
      />

      <Route
        path="/teacher/class/:id/generate"
        element={
          <ProtectedRoute teacherOnly>
            <TeacherGenerate />
          </ProtectedRoute>
        }
      />

      {/* Лендинг — публичный */}
      <Route path="/teacher/assignment/:id" element={<ProtectedRoute teacherOnly><TeacherAssignment /></ProtectedRoute>} />
      <Route path="/teacher/student/:id" element={<ProtectedRoute teacherOnly><TeacherStudent /></ProtectedRoute>} />
<Route path="/" element={<Landing />} />

{/* Демо */}
<Route path="/demo/test" element={<DemoTest />} />

{/* Редиректы */}
<Route path="*" element={<Navigate to={homeRedirect()} replace />} />
    </Routes>
  )
}

export default App
