import { useNavigate } from 'react-router-dom'
import type { MyAssignment } from '../api/assignments'

interface Props {
  assignment: MyAssignment
}

export default function AssignmentCard({ assignment }: Props) {
  const navigate = useNavigate()

  const total = assignment.task_count
  const done = assignment.completed_count
  const progress = total > 0 ? (done / total) * 100 : 0

  const deadline = assignment.deadline
    ? new Date(assignment.deadline).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
      })
    : null

  return (
    <button
      onClick={() => navigate(`/assignment/${assignment.id}`)}
      className="w-full text-left bg-white rounded-2xl shadow-sm p-4
                 hover:shadow-md transition-shadow border border-slate-100"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-slate-800 truncate">
            {assignment.title}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {assignment.topic}
          </p>
        </div>
        {deadline && (
          <span className="text-xs text-slate-500 ml-2 shrink-0">
            до {deadline}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
          <div
            className="bg-brand-500 h-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-xs font-medium text-slate-600 shrink-0">
          {done} / {total}
        </span>
      </div>
    </button>
  )
}