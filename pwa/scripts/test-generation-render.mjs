import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const server = await createServer({
  server: { middlewareMode: true, hmr: false },
  optimizeDeps: { noDiscovery: true, include: [] },
})
try {
  const { default: Card } = await server.ssrLoadModule('/src/components/teacher/GeneratedTaskCard.tsx')
  const { default: Picker } = await server.ssrLoadModule('/src/components/teacher/StudentPicker.tsx')
  const props = {
    task: { code: 'SYNTHETIC', text: '**Условие**\n\nНайди $x^2$.', answer: '42',
      primary_skill_name: 'Тестовый навык', difficulty: 0.55, options: { A: '$x+1$' } },
    position: 1, onReplace() {}, disabled: false, replacing: false, saved: false, common: true,
  }
  const html = renderToStaticMarkup(createElement(Card, props))
  assert(html.includes('<strong>Условие</strong>'))
  assert(html.includes('class="katex"'))
  assert(html.includes('Тестовый навык'))
  assert(html.includes('55%'))
  assert(html.includes('42'))
  assert(html.includes('Заменить задание 1 у всех'))
  const saved = renderToStaticMarkup(createElement(Card, { ...props, saved: true }))
  assert(!saved.includes('<button'))
  const picker = renderToStaticMarkup(createElement(Picker, {
    students: [{ id: 'one', full_name: 'Анна Тестовая' }, { id: 'two', full_name: 'Борис Тестовый' }],
    selectedIds: ['one'], onChange() {}, disabled: true,
  }))
  assert(picker.includes('<fieldset disabled=""'))
  assert.equal((picker.match(/ checked=""/g) || []).length, 1)
  assert(picker.includes('1 из 2'))
  console.log('Generation render checks passed (Markdown, KaTeX, answers, controls)')
} finally {
  await server.close()
}
