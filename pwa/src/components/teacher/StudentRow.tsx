import { useNavigate } from 'react-router-dom'
import type { StudentBrief } from '../../api/groups'

interface Props {
  student: StudentBrief
}

export default function StudentRow({ student }: Props) {
  const navigate = useNavigate()

  const mastery = student.mastery_avg ?? 0
  const masteryPercent = Math.round(mastery * 100)

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
    <button
      onClick={() => navigate(`/teacher/student/${student.id}`)}
      className="w-full glass rounded-2xl p-3 flex items-center gap-3
                 hover:shadow-md transition-shadow text-left"
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
              className={`${bgColor} h-full rounded-full transition-all`}
              style={{ width: `${masteryPercent}%` }}
            />
          </div>
          <span className={`text-sm font-semibold w-10 text-right shrink-0 ${color}`}>
            {masteryPercent}%
          </span>
        </>
      )}
    </button>
  )
}