import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMyResponses, type MyResponse } from '../api/responses'
import Header from '../components/Header'

export default function History() {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: responses, isLoading } = useQuery({
    queryKey: ['responses', 'my'],
    queryFn: () => getMyResponses(100, 0),
  })

  return (
    <div className="min-h-screen">
      <Header showBack title="История ответов" />

      <main className="max-w-2xl mx-auto px-4 py-6">
        {isLoading && (
          <div className="text-center text-slate-400 text-sm py-8">
            Загрузка...
          </div>
        )}

        {!isLoading && (!responses || responses.length === 0) && (
          <div className="glass-strong rounded-3xl p-8 text-center">
            <div className="text-5xl mb-3">📭</div>
            <p className="text-slate-600 text-sm font-medium">
              Вы ещё не решали заданий
            </p>
            <p className="text-slate-400 text-xs mt-1">
              Ответы появятся здесь после первого теста
            </p>
          </div>
        )}

        {!isLoading && responses && responses.length > 0 && (
          <div className="space-y-3">
            {responses.map((r) => (
              <ResponseCard
                key={r.id}
                response={r}
                expanded={expandedId === r.id}
                onToggle={() =>
                  setExpandedId(expandedId === r.id ? null : r.id)
                }
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

// ─── Карточка ответа ─────────────────────────────────

function ResponseCard({
  response,
  expanded,
  onToggle,
}: {
  response: MyResponse
  expanded: boolean
  onToggle: () => void
}) {
  const r = response
  const statusIcon = r.skipped ? '⏭' : r.correct ? '✅' : '❌'
  const statusColor = r.skipped
    ? 'text-slate-400'
    : r.correct
    ? 'text-mastery-strong'
    : 'text-mastery-weak'

  const date = new Date(r.created_at).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <button
      onClick={onToggle}
      className="w-full text-left glass rounded-2xl p-4
                 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-3">
        <span className={`text-xl shrink-0 ${statusColor}`}>{statusIcon}</span>

        <div className="flex-1 min-w-0">
          {r.assignment_title && (
            <p className="text-xs text-brand-600 font-medium truncate mb-1">
              {r.assignment_title}
            </p>
          )}
          <p className="text-sm text-slate-700 font-medium line-clamp-2">
            {r.task_text || r.code || 'Задание'}
          </p>

          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span>{date}</span>
            {r.time_sec !== null && r.time_sec !== undefined && (
              <span>· {r.time_sec} сек</span>
            )}
            {r.skill_name && (
              <span className="truncate">· {r.skill_name}</span>
            )}
          </div>
        </div>

        <span className="text-slate-300 text-sm shrink-0">
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-200 space-y-2 text-sm">
          <div>
            <span className="text-slate-500 text-xs">Ваш ответ:</span>{' '}
            <strong className={r.skipped ? 'text-slate-500' : ''}>
              {r.skipped ? '— (пропущено)' : (r.answer || '—')}
            </strong>
          </div>

          {!r.skipped && !r.correct && r.expected && (
            <div>
              <span className="text-slate-500 text-xs">Правильный ответ:</span>{' '}
              <strong className="text-mastery-strong">{r.expected}</strong>
            </div>
          )}

          {r.code && (
            <div className="text-xs text-slate-400 pt-1">
              Код задания: {r.code}
            </div>
          )}
        </div>
      )}
    </button>
  )
}