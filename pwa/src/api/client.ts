/**
 * Axios-клиент для работы с HyperUm API.
 * - withCredentials: true → отправляем httpOnly cookies
 * - baseURL: /api/v1 → проксируется через Vite на localhost:8000
 * - Интерцепторы: единая обработка ошибок
 */
import axios, { AxiosError } from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Интерцептор ответов: единая обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 401 → редирект на логин (обрабатываем в компонентах)
    // Здесь только логируем для отладки
    if (error.response?.status === 401) {
      console.debug('401 Unauthorized:', error.config?.url)
    }
    return Promise.reject(error)
  }
)

/** Достать текст ошибки из ответа FastAPI. */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Неизвестная ошибка'
}