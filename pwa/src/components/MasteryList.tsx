import type { MasteryItem } from '../api/mastery'
import { masteryBgColor } from '../api/mastery'

interface Props {
  skills: MasteryItem[]
  title?: string
}

export default function MasteryList({ skills, title }: Props) {
  if (skills.length === 0) {
    return (
      <div className="text-center text-slate-500 py-6 text-sm">
        Пока нет данных
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {title && (
        <h3 className="text-sm font-medium text-slate-600 mb-2">{title}</h3>
      )}
      {skills.map((skill) => (
        <div key={skill.skill_id} className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-700 truncate font-medium">
              {skill.skill_name}
            </p>
          </div>
          <div className="w-20 bg-white/60 rounded-full h-1.5 overflow-hidden shrink-0">
            <div
              className={`${masteryBgColor(skill.mastery)} h-full rounded-full transition-all duration-500`}
              style={{ width: `${skill.mastery * 100}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-slate-600 w-9 text-right shrink-0">
            {Math.round(skill.mastery * 100)}%
          </span>
        </div>
      ))}
    </div>
  )
}