import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

interface Props {
  text: string
  className?: string
}

/** Конвертирует \(...\) и \[...\] в $...$ и $$...$$ */
function convertDelimiters(text: string): string {
  let result = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, body) => `\n$$${body}$$\n`)
  result = result.replace(/\\\(([\s\S]*?)\\\)/g, (_, body) => `$${body}$`)
  return result
}

export default function LatexText({ text, className = '' }: Props) {
  const processed = convertDelimiters(text)

  return (
    <div className={`latex-text ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={{
          table: ({ children }) => (
            <div className="table-scroll overflow-x-auto my-3">
              <table className="min-w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-slate-300 px-3 py-2 bg-slate-50 text-left">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-slate-300 px-3 py-2">{children}</td>
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
