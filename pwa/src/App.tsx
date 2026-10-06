import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { me } from './api/auth'
import { useAuthStore } from './stores/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Assignment from './pages/Assignment'
import Graph from './pages/Graph'
import History from './pages/History'

function App() {
  const setUser = useAuthStore((s) => s.setUser)
  const setLoading = useAuthStore((s) => s.setLoading)

  // При старте — проверяем, залогинен ли пользователь
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

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
  path="/dashboard"
  element={
    <ProtectedRoute>
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
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App