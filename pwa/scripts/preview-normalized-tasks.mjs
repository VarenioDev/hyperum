// Validate math and render with the actual LatexText component, without an API/DB.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import ts from 'typescript'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import katex from 'katex'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const reportPath = path.resolve(process.argv[2])
const report = JSON.parse(await fs.readFile(reportPath, 'utf8'))
const source = (await fs.readFile(path.join(root, 'src/components/LatexText.tsx'), 'utf8'))
  .replace(/^import ['"]katex\/dist\/katex.min.css['"]\s*$/m, '')
const compiled = ts.transpileModule(source, { compilerOptions: {
  jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022,
}}).outputText
const tempDir = await fs.mkdtemp(path.join(root, 'node_modules/.normalization-preview-'))
let component
try {
  const target = path.join(tempDir, 'LatexText.mjs')
  await fs.writeFile(target, compiled)
  component = (await import(pathToFileURL(target).href)).default
} finally {
  if (!path.resolve(tempDir).startsWith(path.resolve(root, 'node_modules') + path.sep)) {
    throw new Error('Temporary renderer path is outside node_modules')
  }
  await fs.rm(tempDir, { recursive: true, force: true })
}
const escape = value => String(value).replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[c])
const parser = unified().use(remarkParse).use(remarkMath).use(remarkGfm)
function validate(text) {
  const errors = []
  let formulas = 0
  const visit = node => {
    if (node.type === 'math' || node.type === 'inlineMath') {
      formulas++
      try { katex.renderToString(node.value, { throwOnError: true, strict: 'error', trust: false }) }
      catch (error) { errors.push(error.message) }
    } else if (node.type === 'text' && (/\\[A-Za-z]+/.test(node.value) || node.value.includes('$'))) {
      errors.push('Math delimiters/LaTeX remain outside parsed math: ' + node.value.slice(0, 100))
    }
    for (const child of node.children || []) visit(child)
  }
  visit(parser.parse(text))
  return { errors: [...new Set(errors)], formulas }
}
let css = await fs.readFile(path.join(root, 'node_modules/katex/dist/katex.min.css'), 'utf8')
for (const match of [...css.matchAll(/url\(([^)]+)\)/g)]) {
  const file = match[1].replace(/^['"]|['"]$/g, '')
  const font = await fs.readFile(path.join(root, 'node_modules/katex/dist', file))
  const mime = file.endsWith('.woff2') ? 'font/woff2' : file.endsWith('.woff') ? 'font/woff' : 'font/ttf'
  css = css.replace(match[0], `url(data:${mime};base64,${font.toString('base64')})`)
}
const sections = report.tasks.map(task => {
  const result = validate(task.normalized_text)
  task.render_errors = result.errors
  task.formula_count = result.formulas
  const flags = [...(task.warnings || []), ...(task.checks || []), ...result.errors]
  if (task.needs_review) flags.unshift('Model requested manual review')
  if (task.error) flags.unshift(task.error)
  const html = renderToStaticMarkup(React.createElement(component, { text: task.normalized_text }))
  return `<article id="${escape(task.code)}"><h2>${escape(task.code)}</h2>
    <p class="${flags.length && !task.manual_review ? 'warn' : 'ok'}">${task.manual_review ? 'Проверено вручную' : flags.length ? 'Требует проверки' : 'Синтаксические проверки пройдены'} · формул: ${result.formulas}</p>
    ${task.manual_review ? `<p class="ok">${escape(task.manual_review)}</p>` : ''}
    ${flags.length ? `<ul class="warn">${flags.map(flag => `<li>${escape(flag)}</li>`).join('')}</ul>` : ''}
    <div class="columns"><section><h3>Исходник</h3><pre>${escape(task.original_text)}</pre></section>
    <section><h3>Результат</h3>${html}<details><summary>Markdown</summary><pre>${escape(task.normalized_text)}</pre></details></section></div></article>`
}).join('\n')
await fs.writeFile(reportPath, JSON.stringify(report, null, 2))
const html = `<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка нормализации заданий</title><style>${css}
body{font-family:system-ui,sans-serif;background:#f5f6fa;color:#172033;margin:0;padding:24px;line-height:1.6}
main{max-width:1440px;margin:auto}article{background:white;border-radius:16px;padding:24px;margin:24px 0}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}.columns>section{min-width:0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f3f8;padding:16px;border-radius:8px;font-size:13px}
.katex-display{overflow-x:auto;overflow-y:hidden;padding:8px 0}.warn{color:#a23b00}.ok{color:#16703d}
.latex-text p{white-space:pre-wrap}table{border-collapse:collapse}th,td{border:1px solid #ccd2df;padding:8px}
.table-scroll{overflow-x:auto}@media(max-width:800px){body{padding:12px}.columns{grid-template-columns:1fr}}
</style><main><h1>Нормализация заданий</h1><p>Слева исходник, справа рендер текущим LatexText. Проверки синтаксиса не подтверждают математическую эквивалентность. БД не изменялась.</p>
<nav>${report.tasks.map(task => `<a href="#${escape(task.code)}">${escape(task.code)}</a>`).join(' · ')}</nav>${sections}</main></html>`
await fs.writeFile(path.join(path.dirname(reportPath), 'preview.html'), html)
console.log(`Rendered ${report.tasks.length} tasks; ${report.tasks.filter(t => t.render_errors.length).length} with syntax errors`)
