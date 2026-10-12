import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMyAssignments } from '../api/assignments'
import { getMyMasterySummary} from '../api/mastery'
import { getNextRecommendation } from '../api/recommendations'
import { useAuthStore } from '../stores/authStore'
import Header from '../components/Header'
import AssignmentCard from '../components/AssignmentCard'
import MasteryList from '../components/MasteryList'
import NextStepCard from '../components/NextStepCard'

export default function Dashboard() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const { data: assignments, isLoading: loadingAssignments } = useQuery({
    queryKey: ['assignments', 'my'],
    queryFn: getMyAssignments,
    enabled: user?.role === 'student',
  })

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['mastery', 'me', 'summary'],
    queryFn: getMyMasterySummary,
    enabled: user?.role === 'student',
    retry: false,
  })

  const { data: recommendation, isLoading: loadingRec } = useQuery({
    queryKey: ['recommendations', 'next'],
    queryFn: getNextRecommendation,
    enabled: user?.role === 'student',
    retry: false,
  })

  if (!user) return null

  const firstName = user.full_name.split(' ')[1] || user.full_name.split(' ')[0]
  const weakSkills = summary ? summary.top_weak_skills : []

  return (
    <div className="min-h-screen pb-8 relative">
      <div className="fixed top-0 -left-32 w-80 h-80 rounded-full
                      bg-brand-300/30 blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 -right-32 w-80 h-80 rounded-full
                      bg-purple-300/30 blur-3xl pointer-events-none" />

      <Header />

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6 relative">
        {/* Приветствие */}
        <div>
          <h1 className="text-3xl font-bold text-slate-800">
            Привет, {firstName}!
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {new Date().toLocaleDateString('ru-RU', {
              weekday: 'long', day: 'numeric', month: 'long',
            })}
          </p>
        </div>

        {/* Следующий шаг — только если есть рекомендация */}
        {user.role === 'student' && !loadingRec && recommendation && (
          <NextStepCard recommendation={recommendation} />
        )}

        {/* Метрики */}
        {user.role === 'student' && summary && summary.total_skills > 0 && (
          <section>
            <div className="grid grid-cols-3 gap-3">
              <StatCard
                value={`${Math.round(summary.avg_mastery * 100)}%`}
                label="средний"
                color="text-brand-600"
              />
              <StatCard
                value={summary.mastered}
                label="освоено"
                color="text-mastery-strong"
              />
              <StatCard
                value={summary.weak}
                label="подтянуть"
                color="text-mastery-weak"
              />
            </div>
          </section>
        )}

        {/* Активные задания */}
        {user.role === 'student' && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-slate-700">
                Активные задания
              </h2>
              <button
                onClick={() => navigate('/history')}
                className="text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                История →
              </button>
            </div>

            {loadingAssignments && (
              <div className="text-center text-slate-400 text-sm py-6">
                Загрузка...
              </div>
            )}

            {!loadingAssignments && (() => {
              const active = (assignments || []).filter(
                (a) => a.student_status !== 'completed'
              )
              const done = (assignments || []).filter(
                (a) => a.student_status === 'completed'
              )
              return (
                <>
                  {active.length === 0 && (
                    <div className="glass rounded-2xl p-6 text-center">
                      <p className="text-slate-600 text-sm font-medium">
                        Нет активных заданий
                      </p>
                      <p className="text-slate-400 text-xs mt-1">
                        Учитель скоро назначит что-то новое
                      </p>
                    </div>
                  )}

                  {active.length > 0 && (
                    <div className="space-y-3">
                      {active.map((a) => (
                        <AssignmentCard key={a.id} assignment={a} />
                      ))}
                    </div>
                  )}

                  {done.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-xs uppercase tracking-wide text-slate-400 font-medium mb-3">
                        Пройденные
                      </h3>
                      <div className="space-y-2">
                        {done.map((a) => (
                          <button
                            key={a.id}
                            onClick={() => navigate(`/assignment/${a.id}`)}
                            className="w-full glass rounded-2xl p-4 flex items-center gap-3
                                       opacity-70 hover:opacity-100 transition-opacity text-left"
                          >
                            <span className="text-xl shrink-0">✅</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-600 truncate">
                                {a.title}
                              </p>
                              <p className="text-xs text-slate-400 mt-0.5">
                                {a.topic} · {a.task_count} заданий
                              </p>
                            </div>
                            <span className="text-xs text-slate-400 shrink-0">→</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )
            })()}
          </section>
        )}

        {/* Слабые навыки */}
        {user.role === 'student' && (
          <section>
            <div className="glass-strong rounded-3xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-slate-700">
                  {weakSkills.length > 0 ? 'Стоит подтянуть' : 'Твой прогресс'}
                </h2>
                <button
                  onClick={() => navigate('/graph')}
                  className="text-xs font-medium text-brand-600 hover:text-brand-700"
                >
                  Граф →
                </button>
              </div>

              {loadingSummary && (
                <div className="text-center text-slate-400 text-sm py-4">
                  Загрузка...
                </div>
              )}

              {!loadingSummary && weakSkills.length > 0 && (
                <MasteryList skills={weakSkills} />
              )}

              {!loadingSummary && weakSkills.length === 0 && summary && summary.total_skills > 0 && (
                <div className="text-center py-4">
                  <div className="text-4xl mb-2">🎉</div>
                  <p className="text-sm font-medium text-slate-700">
                    Все навыки в норме
                  </p>
                </div>
              )}

              {!loadingSummary && (!summary || summary.total_skills === 0) && (
                <div className="text-center text-slate-500 py-4 text-sm">
                  Ещё не решал заданий
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function StatCard({
  value,
  label,
  color,
}: {
  value: string | number
  label: string
  color: string
}) {
  return (
    <div className="glass rounded-2xl p-4 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1 font-medium">
        {label}
      </div>
    </div>
  )
}