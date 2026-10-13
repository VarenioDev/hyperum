/**
 * Рендер текста задания: markdown + LaTeX.
 *
 * Особенности:
 * - \( ... \) → $ ... $, \[ ... \] → $$ ... $$.
 * - Голые LaTeX-команды (\geq, \cdot, \le, \frac, ...) оборачиваются в $...$.
 * - GFM: таблицы, зачёркивание.
 */
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

interface Props {
  text: string
  className?: string
}

/**
 * Известные LaTeX-команды, которые встречаются в заданиях ЕГЭ.
 * Если такая команда есть в тексте без обёртки — оборачиваем в $...$.
 */
const LATEX_COMMANDS = [
  // отношения
  'geq', 'leq', 'neq', 'lt', 'gt', 'equiv',
  // арифметика
  'cdot', 'times', 'div', 'pm', 'mp',
  // дроби / функции
  'frac', 'sqrt', 'sum', 'prod', 'int',
  // множества / логика
  'in', 'notin', 'subset', 'cup', 'cap', 'forall', 'exists',
  'land', 'lor', 'lnot', 'neg', 'to', 'rightarrow', 'leftarrow',
  // прочее
  'infty', 'alpha', 'beta', 'gamma', 'pi', 'sigma', 'theta', 'lambda',
]

/**
 * Конвертирует \( ... \) в $ ... $ и \[ ... \] в $$ ... $$.
 */
function convertDelimiters(text: string): string {
  let result = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, body) => `\n$$${body}$$\n`)
  result = result.replace(/\\\(([\s\S]*?)\\\)/g, (_, body) => `$${body}$`)
  return result
}

/**
 * Находит голые LaTeX-команды (\geq, \cdot, ...) и оборачивает их
 * вместе с "прилегающими" операндами в $...$.
 *
 * Пример:
 *   "n \geq 2020"  →  "$n \\geq 2020$"
 *   "a \cdot b"    →  "$a \\cdot b$"
 *
 * Эвристика: берём слово слева и справа от команды (до пробела или знака),
 * оборачиваем "команда + левый + правый" в $...$.
 */
function wrapBareCommands(text: string): string {
  // Если уже есть $...$ — не трогаем совпадения внутри них.
  // Проходим регуляркой: LaTeX-команда + пробел + операнд.
  // Операнд — цифры/буквы/точки.
  const commandPattern = new RegExp(
    `(\\b[A-Za-z0-9]+)\\s+(\\\\${LATEX_COMMANDS.join('|\\\\')})\\s+([A-Za-z0-9]+)`,
    'g'
  )

  return text.replace(commandPattern, (match, left, cmd, right) => {
    // Не оборачиваем, если рядом уже есть $ (мы внутри формулы)
    const idx = text.indexOf(match)
    const before = text.slice(Math.max(0, idx - 20), idx)
    const dollarCount = (before.match(/\$/g) || []).length
    if (dollarCount % 2 === 1) return match // нечётное число $ — внутри формулы
    return `$${left} ${cmd} ${right}$`
  })
}

export default function LatexText({ text, className = '' }: Props) {
  const processed = (() => {
    let t = text
    t = convertDelimiters(t)
    t = wrapBareCommands(t)
    return t
  })()

  return (
    <div className={`latex-text ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
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
            <td className="border border-slate-300 px-3 py-1.5">{children}</td>
          ),
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