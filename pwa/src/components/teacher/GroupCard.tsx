import { useNavigate } from 'react-router-dom'
import type { Group } from '../../api/groups'

interface Props {
  group: Group
}

export default function GroupCard({ group }: Props) {
  const navigate = useNavigate()

  return (
    <button
      onClick={() => navigate(`/teacher/class/${group.id}`)}
      className="w-full text-left glass-strong rounded-2xl p-4
                 transition-all hover:shadow-xl hover:shadow-brand-500/10
                 relative"
    >
      {/* Pending badge */}
      {group.pending_count > 0 && (
        <div className="absolute top-3 right-3 bg-red-500 text-white
                        text-xs font-bold rounded-full px-2 py-0.5 min-w-[20px]
                        text-center animate-pulse">
          {group.pending_count}
        </div>
      )}

      <div className="flex items-start justify-between mb-3 pr-8">
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-slate-800 text-lg truncate">
            {group.name}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 font-medium">
            {group.subject === 'informatics' ? 'Информатика' : group.subject}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">👥</span>
            <span className="font-semibold text-slate-700">
              {group.students_count}
            </span>
            <span className="text-slate-400">учеников</span>
          </div>

          {group.pending_count > 0 && (
            <div className="flex items-center gap-1.5 text-red-600">
              <span>⏳</span>
              <span className="font-semibold">
                {group.pending_count}
              </span>
              <span>ждут</span>
            </div>
          )}
        </div>

        <div className="text-xs text-slate-400 font-mono tracking-wider">
          {group.invite_code}
        </div>
      </div>
    </button>
  )
}