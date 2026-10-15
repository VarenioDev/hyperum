import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { regenerateCode } from '../../api/groups'

interface Props {
  groupId: string
  code: string
  groupName: string
}

export default function InviteCodeBlock({ groupId, code, groupName }: Props) {
  const [copied, setCopied] = useState<'code' | 'link' | null>(null)
  const queryClient = useQueryClient()

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateCode(groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', groupId] })
    },
  })

  const currentCode = regenerateMutation.data?.invite_code || code

  const copy = async (text: string, kind: 'code' | 'link') => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(kind)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      // fallback — старый способ
      const el = document.createElement('textarea')
      el.value = text
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(kind)
      setTimeout(() => setCopied(null), 2000)
    }
  }

  const inviteLink = `${typeof window === 'undefined' ? '' : window.location.origin}/join?code=${currentCode}`

  const handleRegenerate = () => {
    if (confirm('Сгенерировать новый код? Старый перестанет работать.')) {
      regenerateMutation.mutate()
    }
  }

  return (
    <div className="glass-strong rounded-3xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">
          Код для учеников
        </h3>
        <button
          onClick={handleRegenerate}
          disabled={regenerateMutation.isPending}
          className="text-xs text-slate-500 hover:text-brand-600
                     font-medium transition-colors disabled:opacity-50"
        >
          {regenerateMutation.isPending ? 'Генерация...' : '↻ Обновить'}
        </button>
      </div>

      <div className="text-center my-4">
        <div className="font-mono text-3xl font-bold tracking-widest text-hyper">
          {currentCode}
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Передай этот код ученикам класса <strong>{groupName}</strong>
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-4">
        <button
          onClick={() => copy(currentCode, 'code')}
          className="bg-white/70 hover:bg-white text-slate-700 font-medium
                     py-2.5 rounded-xl text-xs transition-colors"
        >
          {copied === 'code' ? '✓ Скопировано' : 'Копировать код'}
        </button>
        <button
          onClick={() => copy(inviteLink, 'link')}
          className="bg-hyper text-white font-medium py-2.5 rounded-xl
                     text-xs shadow-md shadow-brand-500/30
                     hover:shadow-lg transition-all"
        >
          {copied === 'link' ? '✓ Скопировано' : 'Ссылка для входа'}
        </button>
      </div>

      <p className="text-[10px] text-slate-400 mt-3 text-center break-all">
        {inviteLink}
      </p>
    </div>
  )
}
