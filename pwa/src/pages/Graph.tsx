import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getStudentGraph, type GraphNode } from '../api/graph'
import { useAuthStore } from '../stores/authStore'
import GraphView from '../components/GraphView'
import SkillCard from '../components/SkillCard'

export default function Graph() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [showUnknown, setShowUnknown] = useState(false)

  // Стабильный колбэк — не пересоздаётся
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node)
  }, [])

  const {
    data: graph,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['graph', user?.id],
    queryFn: () => getStudentGraph(user!.id),
    enabled: !!user,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка графа...</div>
      </div>
    )
  }

  if (error || !graph) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="text-5xl mb-4">😕</div>
        <p className="text-slate-700">Не удалось загрузить граф</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="text-brand-600 hover:underline text-sm mt-4"
        >
          ← На главную
        </button>
      </div>
    )
  }

  // Статистика по графу
  const stats = {
    mastered: graph.nodes.filter((n) => n.status === 'mastered').length,
    learning: graph.nodes.filter((n) => n.status === 'learning').length,
    weak: graph.nodes.filter((n) => n.status === 'weak').length,
    unknown: graph.nodes.filter((n) => n.status === 'unknown').length,
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="glass-strong border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              ← Назад
            </button>
            <h1 className="text-base font-semibold text-slate-800">
              Граф знаний
            </h1>
            <div className="w-14" />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* Легенда */}
        <div className="glass-strong rounded-2xl shadow-sm p-4">
          <p className="text-xs text-slate-500 mb-3">Легенда</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <LegendItem color="bg-mastery-strong" label="Освоено" count={stats.mastered} />
            <LegendItem color="bg-mastery-medium" label="В процессе" count={stats.learning} />
            <LegendItem color="bg-mastery-weak" label="Слабо" count={stats.weak} />
            <LegendItem color="bg-slate-300" label="Не изучалось" count={stats.unknown} />
          </div>
        </div>


        {/* Граф */}
                {/* Переключатель неизученных */}
        <label className="flex items-center justify-between gap-3 glass-strong rounded-2xl p-4 cursor-pointer">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-700">
              Показать неизученные темы
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {stats.unknown} навыков ещё впереди
            </p>
          </div>
          <div className="relative shrink-0">
            <input
              type="checkbox"
              checked={showUnknown}
              onChange={(e) => setShowUnknown(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-300 rounded-full
                            peer-checked:bg-hyper transition-colors" />
            <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white
                            rounded-full shadow transition-transform
                            peer-checked:translate-x-5" />
          </div>
        </label>

        {/* Подсказка */}
        <p className="text-xs text-slate-500 text-center">
          Тапните на узел, чтобы увидеть детали. Граф можно масштабировать.
        </p>

        {/* Граф */}
        <GraphView
          graph={graph}
          onNodeClick={handleNodeClick}
          showUnknown={showUnknown}
          height="calc(100vh - 340px)"
        />
      </main>

      {/* Карточка навыка */}
      {selectedNode && (
        <SkillCard
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  )
}

// ─── Вспомогательный компонент ────────────────────────

function LegendItem({
  color,
  label,
  count,
}: {
  color: string
  label: string
  count: number
}) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${color} shrink-0`} />
      <span className="text-slate-600 flex-1">{label}</span>
      <span className="text-slate-400">{count}</span>
    </div>
  )
}