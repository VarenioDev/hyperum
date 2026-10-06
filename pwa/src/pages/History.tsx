import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMyResponses } from '../api/responses'

export default function History() {
  const navigate = useNavigate()

  const { data: responses, isLoading } = useQuery({
    queryKey: ['responses', 'my'],
    queryFn: () => getMyResponses(100, 0),
  })

  return (
    <div className="min-h-screen">
      <header className="glass-strong border-b border-slate-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            ← Назад
          </button>
          <h1 className="text-base font-semibold text-slate-800">
            История ответов
          </h1>
          <div className="w-14" />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        {isLoading && (
          <div className="text-center text-slate-400 text-sm py-8">
            Загрузка...
          </div>
        )}

        {!isLoading && (!responses || responses.length === 0) && (
          <div className="glass-strong rounded-2xl shadow-sm p-8 text-center">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-slate-600 text-sm">
              Вы ещё не решали заданий
            </p>
          </div>
        )}

        {!isLoading && responses && responses.length > 0 && (
          <div className="space-y-2">
            {responses.map((r) => (
              <div
                key={r.id}
                className="glass-strong rounded-xl shadow-sm p-3
                           flex items-center gap-3"
              >
                <div className="text-2xl shrink-0">
                  {r.correct ? '✅' : '❌'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">
                    {r.code}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    Ваш ответ: {r.answer}
                  </p>
                </div>
                <div className="text-xs text-slate-400 shrink-0 text-right">
                  {new Date(r.created_at).toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                  })}
                  {r.time_sec && (
                    <div className="text-[10px] mt-0.5">
                      {r.time_sec} сек
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}