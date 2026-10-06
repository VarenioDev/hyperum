import { useEffect } from 'react'
import type { GraphNode } from '../api/graph'

interface Props {
  node: GraphNode
  onClose: () => void
}

const STATUS_LABEL: Record<string, string> = {
  mastered: 'Освоено',
  learning: 'В процессе',
  weak: 'Требует внимания',
  unknown: 'Не изучалось',
}

const STATUS_STYLE: Record<string, string> = {
  mastered: 'bg-mastery-strong',
  learning: 'bg-mastery-medium',
  weak: 'bg-mastery-weak',
  unknown: 'bg-slate-300',
}

export default function SkillCard({ node, onClose }: Props) {
  // Закрытие по Esc
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Заголовок */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div
              className={`w-3 h-3 rounded-full ${
                STATUS_STYLE[node.status]
              }`}
            />
            <span className="text-xs text-slate-500 uppercase tracking-wide">
              {STATUS_LABEL[node.status]}
            </span>
          </div>
          <h2 className="text-lg font-bold text-slate-800">
            {node.name}
          </h2>
          {node.module && (
            <p className="text-xs text-slate-500 mt-1">
              {node.module}
              {node.topic && ` · ${node.topic}`}
            </p>
          )}
        </div>

        {/* Mastery */}
        {node.mastery !== null && (
          <div className="bg-slate-50 rounded-xl p-4">
            <p className="text-xs text-slate-500 mb-2">
              Уровень освоения
            </p>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-white rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full ${STATUS_STYLE[node.status]}`}
                  style={{ width: `${node.mastery * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium text-slate-700">
                {Math.round(node.mastery * 100)}%
              </span>
            </div>
          </div>
        )}

        {node.mastery === null && (
          <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-500">
            Навык пока не оценивался — решите задания, чтобы появился прогресс
          </div>
        )}

        {/* Кнопка закрыть */}
        <button
          onClick={onClose}
          className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700
                     font-medium py-3 rounded-xl transition-colors"
        >
          Закрыть
        </button>
      </div>
    </div>
  )
}