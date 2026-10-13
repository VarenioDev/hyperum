/**
 * Рендер текста задания: markdown + LaTeX.
 *
 * Особенности:
 * - Конвертирует \( ... \) → $ ... $ и \[ ... \] → $$ ... $$,
 *   потому что remark-math по умолчанию понимает только $ синтаксис.
 * - Убирает дубли LaTeX (F65) — например, "\( G(n) \) G(n)" → "\( G(n) \)".
 * - Поддержка GFM: таблицы, зачёркивание.
 * - Безопасный рендер: без raw HTML.
 */
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

interface Props {
  text: string
  className?: string
  /** Убирать дубли LaTeX. По умолчанию true. */
  dedupeLatex?: boolean
}

/**
 * Конвертирует классический LaTeX-синтаксис \(...\) и \[...\]
 * в синтаксис, который понимает remark-math ($...$ и $$...$$).
 */
function convertDelimiters(text: string): string {
  // \[ ... \] → $$ ... $$  (block)
  let result = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, body) => `\n$$${body}$$\n`)

  // \( ... \) → $ ... $  (inline)
  result = result.replace(/\\\(([\s\S]*?)\\\)/g, (_, body) => `$${body}$`)

  return result
}

/**
 * Убирает дубли LaTeX. Пример:
 *   "\( G(n) \) G(n)" → "\( G(n) \)"
 *   "\[ x \] x"       → "\[ x \]"
 *
 * Логика: если после формулы LaTeX идёт тот же текст без обёртки — удаляем его.
 */
function dedupeLatex(text: string): string {
  let result = text

  // \( inline \) + plain_text, где plain_text совпадает с содержимым
  result = result.replace(
    /\\\(([\s\S]*?)\\\)\s*([^\s\\\n][^\n]*?)(?=\s|$|[.,;!?])/g,
    (match, body, after) => {
      const bodyTrim = body.trim()
      const afterTrim = after.trim()
      if (bodyTrim === afterTrim) {
        return `\\(${body}\\)`
      }
      return match
    }
  )

  // \[ block \] + plain_text
  result = result.replace(
    /\\\[([\s\S]*?)\\\]\s*([^\s\\\n][^\n]*?)(?=\s|$|[.,;!?])/g,
    (match, body, after) => {
      const bodyTrim = body.trim()
      const afterTrim = after.trim()
      if (bodyTrim === afterTrim) {
        return `\\[${body}\\]`
      }
      return match
    }
  )

  return result
}

export default function LatexText({
  text,
  className = '',
  dedupeLatex: shouldDedupe = true,
}: Props) {
  const processed = (() => {
    let t = text
    if (shouldDedupe) t = dedupeLatex(t)
    t = convertDelimiters(t)
    return t
  })()

  return (
    <div className={`latex-text ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Таблицы — оборачиваем в скроллируемый контейнер
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 -mx-2 px-2">
              <table className="min-w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-slate-300 px-3 py-1.5 bg-slate-50 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-slate-300 px-3 py-1.5">
              {children}
            </td>
          ),
          // Абзацы — без лишних отступов
          p: ({ children }) => (
            <p className="whitespace-pre-wrap leading-relaxed">{children}</p>
          ),
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  )
}