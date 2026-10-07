import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getGroupDetail,
  updateStudentName,
  removeStudentFromGroup,
  approveStudent,
  type StudentBrief,
} from '../../api/groups'
import { getErrorMessage } from '../../api/client'
import Header from '../../components/Header'
import InviteCodeBlock from '../../components/teacher/InviteCodeBlock'
import PendingStudentCard from '../../components/teacher/PendingStudentCard'

export default function TeacherClass() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [editingStudent, setEditingStudent] = useState<StudentBrief | null>(null)
  const [editName, setEditName] = useState('')
  const [editError, setEditError] = useState('')
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const { data: group, isLoading, error } = useQuery({
    queryKey: ['group', id],
    queryFn: () => getGroupDetail(id!),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: ({ sid, name }: { sid: string; name: string }) =>
      updateStudentName(sid, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      setEditingStudent(null)
      setEditError('')
    },
    onError: (err) => setEditError(getErrorMessage(err)),
  })

  const removeMutation = useMutation({
    mutationFn: (sid: string) => removeStudentFromGroup(id!, sid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      setMenuOpen(null)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (sid: string) => approveStudent(id!, sid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      queryClient.invalidateQueries({ queryKey: ['groups'] })
    },
  })

  const openEdit = (s: StudentBrief) => {
    setEditingStudent(s)
    setEditName(s.full_name)
    setEditError('')
    setMenuOpen(null)
  }

  const handleRemove = (s: StudentBrief) => {
    if (!confirm(`Убрать ${s.full_name} из класса?`)) return
    removeMutation.mutate(s.id)
  }

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
        <div>
          <h1 className="text-3xl font-bold text-slate-800">{group.name}</h1>
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

        {group.invite_code && (
          <InviteCodeBlock
            groupId={group.id}
            code={group.invite_code}
            groupName={group.name}
          />
        )}

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
                <StudentRowWithMenu
                  key={s.id}
                  student={s}
                  menuOpen={menuOpen === s.id}
                  onToggleMenu={() =>
                    setMenuOpen(menuOpen === s.id ? null : s.id)
                  }
                  onOpen={() => {
                    setMenuOpen(null)
                    navigate(`/teacher/student/${s.id}`)
                  }}
                  onEdit={() => openEdit(s)}
                  onRemove={() => handleRemove(s)}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Модалка редактирования */}
      {editingStudent && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-4">
          <div className="glass-strong rounded-3xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-semibold text-slate-800">
              Редактировать ФИО
            </h3>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              autoFocus
              className="w-full px-4 py-3 bg-white/70 border border-white/80
                         rounded-2xl text-base
                         focus:outline-none focus:ring-2 focus:ring-brand-400
                         focus:bg-white transition-all"
              disabled={updateMutation.isPending}
            />
            {editError && (
              <div className="bg-red-50/80 border border-red-200 rounded-2xl
                              p-3 text-sm text-red-700">
                {editError}
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={() =>
                  updateMutation.mutate({
                    sid: editingStudent.id,
                    name: editName,
                  })
                }
                disabled={updateMutation.isPending}
                className="flex-1 bg-hyper text-white font-semibold py-3
                           rounded-2xl shadow-lg shadow-brand-500/30
                           disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Сохраняем...' : 'Сохранить'}
              </button>
              <button
                onClick={() => setEditingStudent(null)}
                className="px-5 bg-slate-100 hover:bg-slate-200 text-slate-600
                           font-medium rounded-2xl transition-colors"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Компонент строки ученика с меню ─────────────────

function StudentRowWithMenu({
  student,
  menuOpen,
  onToggleMenu,
  onOpen,
  onEdit,
  onRemove,
}: {
  student: StudentBrief
  menuOpen: boolean
  onToggleMenu: () => void
  onOpen: () => void
  onEdit: () => void
  onRemove: () => void
}) {
  const mastery = student.mastery_avg ?? 0
  const percent = Math.round(mastery * 100)
  const color =
    mastery >= 0.8
      ? 'text-mastery-strong'
      : mastery >= 0.5
      ? 'text-mastery-medium'
      : 'text-mastery-weak'
  const bgColor =
    mastery >= 0.8
      ? 'bg-mastery-strong'
      : mastery >= 0.5
      ? 'bg-mastery-medium'
      : 'bg-mastery-weak'

  return (
    <div className="relative glass rounded-2xl">
      <div className="flex items-center gap-3 p-3">
        <button
          onClick={onOpen}
          className="flex-1 flex items-center gap-3 text-left min-w-0"
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">
              {student.full_name}
            </p>
            {student.mastery_avg === null && (
              <p className="text-xs text-slate-400 mt-0.5">Ещё не решал</p>
            )}
          </div>
          {student.mastery_avg !== null && (
            <>
              <div className="w-20 bg-white/60 rounded-full h-1.5 overflow-hidden shrink-0">
                <div
                  className={`${bgColor} h-full rounded-full`}
                  style={{ width: `${percent}%` }}
                />
              </div>
              <span className={`text-sm font-semibold w-10 text-right shrink-0 ${color}`}>
                {percent}%
              </span>
            </>
          )}
        </button>
        <button
          onClick={onToggleMenu}
          className="shrink-0 w-8 h-8 flex items-center justify-center
                     text-slate-400 hover:text-slate-600 hover:bg-white/60
                     rounded-xl transition-colors"
        >
          ⋯
        </button>
      </div>

      {menuOpen && (
        <div className="absolute right-2 top-full -mt-1 z-10
                        glass-strong rounded-2xl shadow-xl overflow-hidden">
          <button
            onClick={onEdit}
            className="w-full px-4 py-2.5 text-left text-sm text-slate-700
                       hover:bg-white/60 transition-colors whitespace-nowrap"
          >
            ✏️ Редактировать ФИО
          </button>
          <button
            onClick={onRemove}
            className="w-full px-4 py-2.5 text-left text-sm text-red-600
                       hover:bg-red-50/60 transition-colors whitespace-nowrap"
          >
            🗑 Убрать из класса
          </button>
        </div>
      )}
    </div>
  )
}