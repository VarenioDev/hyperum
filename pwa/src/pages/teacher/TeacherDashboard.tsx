import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listGroups, createGroup } from '../../api/groups'
import { getErrorMessage } from '../../api/client'
import { useAuthStore } from '../../stores/authStore'
import Header from '../../components/Header'
import GroupCard from '../../components/teacher/GroupCard'

export default function TeacherDashboard() {
  const user = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newSubject, setNewSubject] = useState('informatics')
  const [error, setError] = useState('')

  const { data: groups, isLoading } = useQuery({
    queryKey: ['groups'],
    queryFn: listGroups,
  })

  const createMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      setShowCreate(false)
      setNewName('')
      setError('')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleCreate = () => {
    setError('')
    if (newName.length < 2) {
      setError('Название минимум 2 символа')
      return
    }
    createMutation.mutate({
      name: newName,
      subject: newSubject,
      kind: 'class',
    })
  }

  if (!user) return null

  const firstName = user.full_name.split(' ')[1] || user.full_name.split(' ')[0]
  const totalStudents = groups?.reduce((sum, g) => sum + g.students_count, 0) || 0
  const totalPending = groups?.reduce((sum, g) => sum + g.pending_count, 0) || 0

  return (
    <div className="min-h-screen pb-8 relative">
      <div className="fixed top-0 -left-32 w-80 h-80 rounded-full
                      bg-brand-300/30 blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 -right-32 w-80 h-80 rounded-full
                      bg-purple-300/30 blur-3xl pointer-events-none" />

      <Header />

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6 relative">
        {/* Приветствие */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">
              Привет, {firstName}!
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Твои классы и ученики
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-hyper text-white font-semibold px-4 py-2.5
                       rounded-2xl shadow-lg shadow-brand-500/30
                       hover:shadow-xl transition-all text-sm shrink-0"
          >
            + Класс
          </button>
        </div>

        {/* Метрики */}
        {groups && groups.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            <div className="glass rounded-2xl p-4 text-center">
              <div className="text-2xl font-bold text-brand-600">
                {totalStudents}
              </div>
              <div className="text-xs text-slate-500 mt-1 font-medium">
                учеников
              </div>
            </div>
            <div className={`glass rounded-2xl p-4 text-center ${
              totalPending > 0 ? 'ring-2 ring-red-300' : ''
            }`}>
              <div className={`text-2xl font-bold ${
                totalPending > 0 ? 'text-red-500' : 'text-slate-400'
              }`}>
                {totalPending}
              </div>
              <div className="text-xs text-slate-500 mt-1 font-medium">
                ждут подтверждения
              </div>
            </div>
          </div>
        )}

        {/* Форма создания класса */}
        {showCreate && (
          <div className="glass-strong rounded-3xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-800">Новый класс</h3>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Название
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="11А"
                autoFocus
                className="w-full px-4 py-3 bg-white/70 border border-white/80
                           rounded-2xl text-base placeholder:text-slate-400
                           focus:outline-none focus:ring-2 focus:ring-brand-400
                           focus:bg-white transition-all"
                disabled={createMutation.isPending}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Предмет
              </label>
              <select
                value={newSubject}
                onChange={(e) => setNewSubject(e.target.value)}
                className="w-full px-4 py-3 bg-white/70 border border-white/80
                           rounded-2xl text-base
                           focus:outline-none focus:ring-2 focus:ring-brand-400
                           focus:bg-white transition-all"
                disabled={createMutation.isPending}
              >
                <option value="informatics">Информатика</option>
                <option value="math">Математика</option>
                <option value="russian">Русский язык</option>
              </select>
            </div>

            {error && (
              <div className="bg-red-50/80 border border-red-200 rounded-2xl p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="flex-1 bg-hyper text-white font-semibold py-3
                           rounded-2xl shadow-lg shadow-brand-500/30
                           disabled:opacity-50 transition-all"
              >
                {createMutation.isPending ? 'Создаём...' : 'Создать'}
              </button>
              <button
                onClick={() => {
                  setShowCreate(false)
                  setError('')
                }}
                className="px-6 bg-slate-100 hover:bg-slate-200 text-slate-700
                           font-medium rounded-2xl transition-colors"
              >
                Отмена
              </button>
            </div>
          </div>
        )}

        {/* Список классов */}
        <section>
          <h2 className="text-base font-semibold text-slate-700 mb-3">
            Мои классы
          </h2>

          {isLoading && (
            <div className="text-center text-slate-400 text-sm py-8">
              Загрузка...
            </div>
          )}

          {!isLoading && (!groups || groups.length === 0) && !showCreate && (
            <div className="glass rounded-2xl p-6 text-center">
              <div className="text-4xl mb-3">📚</div>
              <p className="text-slate-600 text-sm font-medium">
                У тебя пока нет классов
              </p>
              <p className="text-slate-400 text-xs mt-1">
                Создай первый класс, чтобы начать
              </p>
            </div>
          )}

          {groups && groups.length > 0 && (
            <div className="space-y-3">
              {groups.map((g) => (
                <GroupCard key={g.id} group={g} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}