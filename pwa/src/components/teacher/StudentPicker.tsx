import { useState } from 'react'

interface Props {
  students: { id: string; full_name: string }[]
  selectedIds: string[]
  onChange: (ids: string[]) => void
  disabled?: boolean
}

export default function StudentPicker({ students, selectedIds, onChange, disabled }: Props) {
  const [search, setSearch] = useState('')
  const words = search.trim().toLocaleLowerCase('ru').split(/\s+/).filter(Boolean)
  const visible = students.filter(s => words.every(word => s.full_name.toLocaleLowerCase('ru').includes(word)))
  const selected = new Set(selectedIds)
  const allVisible = visible.length > 0 && visible.every(s => selected.has(s.id))

  return (
    <fieldset disabled={disabled} className="glass-strong rounded-3xl p-5 space-y-4">
      <legend className="sr-only">Получатели теста</legend>
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold text-slate-800">Кому отправим тест</h2>
        <span aria-live="polite" className="text-xs font-medium text-brand-600 bg-brand-50 px-3 py-1.5 rounded-full">
          {selectedIds.length} из {students.length}
        </span>
      </div>
      <label className="block">
        <span className="sr-only">Найти ученика по имени</span>
        <input type="search" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Найти по имени или фамилии"
          className="w-full px-4 py-3 rounded-2xl bg-white/70 border border-white/80 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
      </label>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
        <button type="button" disabled={!visible.length || allVisible} className="text-brand-600 font-medium disabled:opacity-40"
          onClick={() => onChange([...new Set([...selectedIds, ...visible.map(s => s.id)])])}>
          {search.trim() ? 'Выбрать найденных' : 'Выбрать всех'}
        </button>
        <button type="button" disabled={!selectedIds.length} onClick={() => onChange([])}
          className="text-slate-500 font-medium disabled:opacity-40">Снять выбор</button>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-1 pr-1">
        {visible.map(student => (
          <label key={student.id} className={`flex items-center gap-3 rounded-2xl px-3 py-3 cursor-pointer transition-colors ${selected.has(student.id) ? 'bg-brand-50/80' : 'hover:bg-white/60'}`}>
            <input type="checkbox" checked={selected.has(student.id)} className="h-4 w-4 shrink-0 accent-pink-500"
              onChange={e => onChange(e.target.checked ? [...selectedIds, student.id] : selectedIds.filter(id => id !== student.id))} />
            <span className="text-sm text-slate-700 break-words min-w-0">{student.full_name}</span>
          </label>
        ))}
        {!visible.length && <p className="text-sm text-slate-500 py-3">{students.length ? 'По этому имени никого не нашли' : 'Пока нет подтверждённых учеников'}</p>}
      </div>
      <p className="text-xs text-slate-400">В списке только ученики с подтверждённым доступом. Поиск не меняет выбор.</p>
    </fieldset>
  )
}
