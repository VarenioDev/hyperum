import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getGroupDetail } from '../../api/groups'
import Header from '../../components/Header'
import InviteCodeBlock from '../../components/teacher/InviteCodeBlock'
import PendingStudentCard from '../../components/teacher/PendingStudentCard'
import StudentRow from '../../components/teacher/StudentRow'

export default function TeacherClass() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: group, isLoading, error } = useQuery({
    queryKey: ['group', id],
    queryFn: () => getGroupDetail(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-500">Загрузка...</div>
      </div>
    )
  }

  if (error || !group) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6">
        <div className="text-5xl mb-4">😕</div>
        <p className="text-slate-700">Класс не найден</p>
        <button
          onClick={() => navigate('/teacher')}
          className="text-brand-600 hover:underline text-sm mt-4"
        >
          ← К списку классов
        </button>
      </div>
    )
  }

  const pending = group.students.filter((s) => s.status === 'pending')
  const active = group.students.filter((s) => s.status === 'active')

  return (
    <div className="min-h-screen pb-8 relative">
      <div className="fixed top-0 -left-32 w-80 h-80 rounded-full
                      bg-brand-300/30 blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 -right-32 w-80 h-80 rounded-full
                      bg-purple-300/30 blur-3xl pointer-events-none" />

      <Header showBack backTo="/teacher" />

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6 relative">
        {/* Заголовок */}
        <div>
          <h1 className="text-3xl font-bold text-slate-800">
            {group.name}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {group.subject === 'informatics' ? 'Информатика' : group.subject}
            {' · '}
            {group.students_count} учеников
            {group.pending_count > 0 && (
              <span className="text-red-500 font-medium">
                {' · '}
                {group.pending_count} ждут
              </span>
            )}
          </p>
        </div>

        {/* Кнопка генерации теста */}
        <button
          onClick={() => navigate(`/teacher/class/${group.id}/generate`)}
          className="w-full bg-hyper text-white font-semibold py-4
                     rounded-2xl shadow-lg shadow-brand-500/30
                     hover:shadow-xl transition-all flex items-center
                     justify-center gap-2"
        >
          <span>✨</span>
          Сгенерировать персональные тесты
        </button>

        {/* Инвайт-код */}
        {group.invite_code && (
          <InviteCodeBlock
            groupId={group.id}
            code={group.invite_code}
            groupName={group.name}
          />
        )}

        {/* Ожидают подтверждения */}
        {pending.length > 0 && (
          <section>
            <h2 className="text-base font-semibold text-slate-700 mb-3">
              Ждут подтверждения ({pending.length})
            </h2>
            <div className="space-y-3">
              {pending.map((s) => (
                <PendingStudentCard
                  key={s.id}
                  groupId={group.id}
                  student={s}
                />
              ))}
            </div>
          </section>
        )}

        {/* Активные ученики */}
        <section>
          <h2 className="text-base font-semibold text-slate-700 mb-3">
            Ученики ({active.length})
          </h2>

          {active.length === 0 && (
            <div className="glass rounded-2xl p-6 text-center">
              <div className="text-4xl mb-3">👥</div>
              <p className="text-slate-600 text-sm font-medium">
                Пока нет активных учеников
              </p>
              <p className="text-slate-400 text-xs mt-1">
                Передай код класса — ученики зарегистрируются
              </p>
            </div>
          )}

          {active.length > 0 && (
            <div className="space-y-2">
              {active.map((s) => (
                <StudentRow key={s.id} student={s} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}