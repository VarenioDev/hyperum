/**
 * Глобальное состояние аутентификации.
 * Хранит текущего пользователя и статус загрузки.
 */
import { create } from 'zustand'
import type { User } from '../api/auth'

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  reset: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  setUser: (user) =>
    set({
      user,
      isAuthenticated: user !== null,
      isLoading: false,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  reset: () =>
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    }),
}))