import type { ResponseResult } from '../api/responses'

interface Props {
  result: ResponseResult
  onNext: () => void
  isLast: boolean
}

export default function Feedback({ result, onNext, isLast }: Props) {
  const { correct, expected, new_mastery } = result

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50
                    flex items-end sm:items-center justify-center p-4">
      <div className="glass-strong rounded-3xl w-full max-w-md p-6 space-y-4
                      animate-in slide-in-from-bottom duration-300">

        {/* Заголовок */}
        <div className="text-center">
          <div className="text-6xl mb-3">{correct ? '🎉' : '😔'}</div>
          <h2 className={`text-2xl font-bold ${
            correct ? 'text-hyper' : 'text-slate-700'
          }`}>
            {correct ? 'Верно!' : 'Неверно'}
          </h2>
        </div>

        {/* Правильный ответ */}
        {!correct && expected && (
          <div className="glass-tinted rounded-2xl p-4">
            <p className="text-xs text-slate-600 mb-1 font-medium">
              Правильный ответ
            </p>
            <p className="text-base font-semibold text-slate-800 break-words">
              {expected}
            </p>
          </div>
        )}

        {/* Mastery */}
        {new_mastery !== null && (
          <div className="glass rounded-2xl p-4">
            <p className="text-xs text-slate-600 mb-2 font-medium">
              Уровень освоения навыка
            </p>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-white/60 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    new_mastery >= 0.8
                      ? 'bg-mastery-strong'
                      : new_mastery >= 0.5
                      ? 'bg-mastery-medium'
                      : 'bg-mastery-weak'
                  }`}
                  style={{ width: `${new_mastery * 100}%` }}
                />
              </div>
              <span className="text-sm font-bold text-slate-700">
                {Math.round(new_mastery * 100)}%
              </span>
            </div>
          </div>
        )}

        <button
          onClick={onNext}
          className="w-full bg-hyper text-white font-semibold py-3.5
                     rounded-2xl transition-all shadow-lg shadow-brand-500/30
                     hover:shadow-xl hover:shadow-brand-500/40"
        >
          {isLast ? 'Завершить' : 'Следующее →'}
        </button>
      </div>
    </div>
  )
}