import type { GeneratedTask } from '../../api/assignments'
import LatexText from '../LatexText'

interface Props {
  task: GeneratedTask
  position: number
  onReplace: () => void
  disabled: boolean
  replacing: boolean
  saved: boolean
  common: boolean
  message?: string
  error?: string
}

export default function GeneratedTaskCard({ task, position, onReplace, disabled, replacing, saved, common, message, error }: Props) {
  return (
    <article className="rounded-2xl bg-white/65 border border-white/80 p-4 space-y-3 min-w-0">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-7 h-7 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center font-semibold">{position}</span>
          <span className="font-mono text-slate-400">{task.code}</span>
        </div>
        {!saved && <button type="button" onClick={onReplace} disabled={disabled}
          aria-label={`Заменить задание ${position}${common ? ' у всех' : ''}`}
          className="px-3 py-2 rounded-xl text-xs font-semibold text-brand-600 bg-brand-50 hover:bg-brand-100 disabled:opacity-40">
          {replacing ? 'Подбираем…' : common ? '↻ Заменить у всех' : '↻ Заменить'}
        </button>}
      </div>
      <LatexText text={task.text} className="text-sm text-slate-700" />
      {task.options && <ul className="space-y-1 text-sm text-slate-600">
        {Object.entries(task.options).map(([key, value]) => <li key={key} className="flex items-start gap-2">
          <span className="font-semibold shrink-0">{key}.</span>
          <LatexText text={typeof value === 'string' ? value : JSON.stringify(value)} />
        </li>)}
      </ul>}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full px-3 py-1.5 bg-purple-50 text-purple-700">{task.primary_skill_name || task.skill_id || 'Навык не указан'}</span>
        {task.difficulty != null && <span className="rounded-full px-3 py-1.5 bg-slate-50 text-slate-500" title="Оценка сложности задания">Сложность {Math.round(task.difficulty * 100)}%</span>}
      </div>
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer hover:text-slate-700">Правильный ответ</summary>
        <p className="mt-2 rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800 whitespace-pre-wrap break-words">{task.answer ?? 'Ответ не указан'}</p>
      </details>
      {message && <p role="status" className="text-xs text-purple-600">{message}</p>}
      {error && <p role="alert" className="text-xs text-red-600">{error}</p>}
    </article>
  )
}
