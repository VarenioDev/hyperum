import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

/**
 * Edge swipe back (как в iOS).
 * Работает только при касании от левого края экрана (< 30px).
 * Не конфликтует со скроллом по вертикали и с панорамированием Cytoscape.
 */
export function useSwipeBack(options?: {
  edgeWidth?: number
  threshold?: number
}) {
  const navigate = useNavigate()
  const location = useLocation()

  const edgeWidth = options?.edgeWidth ?? 30
  const threshold = options?.threshold ?? 80

  // Роуты, где «назад» не имеет смысла
  const blockedRoutes = [
    '/login',
    '/join',
    '/',
    '/dashboard',
    '/teacher',
  ]

  useEffect(() => {
    let startX = 0
    let startY = 0
    let tracking = false

    const onTouchStart = (e: TouchEvent) => {
      // Не активируем свайп внутри canvas (Cytoscape граф)
      const target = e.target as HTMLElement
      if (target.tagName === 'CANVAS') {
        tracking = false
        return
      }

      const t = e.touches[0]
      if (t.clientX < edgeWidth) {
        startX = t.clientX
        startY = t.clientY
        tracking = true
      } else {
        tracking = false
      }
    }

    const onTouchEnd = (e: TouchEvent) => {
      if (!tracking) return
      tracking = false

      const t = e.changedTouches[0]
      const dx = t.clientX - startX
      const dy = Math.abs(t.clientY - startY)

      // Свайп вправо от края + явно горизонтальный (не скролл)
      if (dx > threshold && dy < threshold * 0.7) {
        // Не срабатывает на «главных» экранах
        if (blockedRoutes.includes(location.pathname)) return

        navigate(-1)
      }
    }

    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchend', onTouchEnd, { passive: true })

    return () => {
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [navigate, location.pathname, edgeWidth, threshold])
}