import { useMutation, useQueryClient } from '@tanstack/react-query'
import { approveStudent, rejectStudent, type StudentBrief } from '../../api/groups'
import { getErrorMessage } from '../../api/client'

interface Props {
  groupId: string
  student: StudentBrief
}

export default function PendingStudentCard({ groupId, student }: Props) {
  const queryClient = useQueryClient()

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['group', groupId] })
    queryClient.invalidateQueries({ queryKey: ['groups'] })
  }

  const approveMutation = useMutation({
    mutationFn: () => approveStudent(groupId, student.id),
    onSuccess: invalidate,
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectStudent(groupId, student.id),
    onSuccess: invalidate,
  })

  const isPending = approveMutation.isPending || rejectMutation.isPending
  const error = approveMutation.error || rejectMutation.error

  return (
    <div className="glass-tinted rounded-2xl p-4 space-y-3
                    ring-1 ring-white/40">
      <div>
        <p className="font-semibold text-slate-800 truncate">
          {student.full_name}
        </p>
        <p className="text-xs text-slate-500 mt-0.5 truncate">
          {student.email}
        </p>
      </div>

      {error && (
        <div className="bg-red-50/80 border border-red-200 rounded-xl
                        p-2 text-xs text-red-700">
          {getErrorMessage(error)}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => approveMutation.mutate()}
          disabled={isPending}
          className="flex-1 bg-hyper text-white font-semibold py-2.5
                     rounded-xl text-sm shadow-md shadow-brand-500/30
                     disabled:opacity-50 transition-all"
        >
          {approveMutation.isPending ? '...' : '✓ Подтвердить'}
        </button>
        <button
          onClick={() => rejectMutation.mutate()}
          disabled={isPending}
          className="px-4 bg-white/70 hover:bg-white text-slate-600
                     font-medium rounded-xl text-sm transition-colors
                     disabled:opacity-50"
        >
          ✕
        </button>
      </div>
    </div>
  )
}