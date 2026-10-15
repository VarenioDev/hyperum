import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createServer } from 'vite'
import { mkdir, readFile, writeFile } from 'node:fs/promises'

const server = await createServer({ server: { middlewareMode: true, hmr: false }, optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { resultText, latestStudentTest, attemptStatus } = await server.ssrLoadModule('/src/components/teacher/reportUtils.ts')
  const { TaskText, HistoryResponse } = await server.ssrLoadModule('/src/components/teacher/AttemptDetails.tsx')
  const { default: Class } = await server.ssrLoadModule('/src/pages/teacher/TeacherClass.tsx')
  const { default: Matrix } = await server.ssrLoadModule('/src/pages/teacher/TeacherAssignment.tsx')
  const { default: Student } = await server.ssrLoadModule('/src/pages/teacher/TeacherStudent.tsx')
  const { default: Generator } = await server.ssrLoadModule('/src/pages/teacher/TeacherGenerate.tsx')
  const query = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } })
  const stamp = '2026-10-15T12:00:00Z'
  const result = { student_id: 'student', task_count: 5, answered_count: 4, correct_count: 1, state: 'in_progress', saved_state: 'in_progress', has_legacy: false }
  const summary = { students_count: 1, completed_count: 0, started_count: 1, task_count: 5, answered_count: 4, correct_count: 1 }
  const assignment = { id: 'test', group_id: 'class', class_name: '10Б · пример', title: 'Кодирование — проверка', topic: 'Кодирование', status: 'sent', created_at: stamp, sent_at: stamp, students: [result], summary, has_legacy: false }
  const student = { id: 'student', full_name: 'Анна Тестовая', email: null, status: 'active', mastery_avg: 0.5, joined_at: stamp, active_assignments: 1, last_completed_title: null, last_completed_score: null, days_since_activity: 0 }
  const group = { id: 'class', name: '10Б · пример', subject: 'informatics', students_count: 1, pending_count: 0, invite_code: 'DEMO42', students: [student] }
  const cells = ['correct', 'incorrect', 'skipped', 'surrendered', 'unanswered'].map((status, index) => ({ task_id: `task-${index}`, position: index+1, code: `T${index+1}`, status, answered_at: stamp }))
  query.setQueryData(['group', 'class'], group)
  query.setQueryData(['teacher-class-assignments', 'class'], [assignment])
  query.setQueryData(['teacher-assignment', 'test'], { assignment, students: [{ ...result, full_name: student.full_name, cells }], summary, common_tasks: false, has_legacy: false })
  query.setQueryData(['teacher-student', 'student'], { student: { ...student, last_activity: stamp }, groups: [{ id:'class', name:group.name, status:'active' }], summary: { total_skills: 2, mastered: 0, learning: 1, weak: 1 }, weak_skills: [{ skill_id:'skill', name:'Кодирование текста',topic:'Кодирование',mastery:0.4,attempts:4,correct:1 }], assignments: [assignment] })
  query.setQueryData(['teacher-student-graph', 'student'], { student_id:'student', student_name:student.full_name, nodes:[{ id:'skill',name:'Кодирование текста',topic:'Кодирование',module:'Информация',mastery:0.4,attempts:4,status:'weak' }],edges:[] })
  query.setQueryData(['topics'], ['Кодирование'])
  const render = (Component, path, route) => renderToStaticMarkup(createElement(QueryClientProvider, { client: query }, createElement(MemoryRouter, { initialEntries: [path] }, createElement(Routes, null, createElement(Route, { path: route, element: createElement(Component) })))))
  assert.equal(resultText(result), 'Выполнено 4 из 5 · верно 1/5')
  assert(resultText({ ...result, answered_count:0,has_legacy:true,saved_state:'completed' }).includes('до обновления'))
  assert.equal(attemptStatus({ correct:true, skipped:false, surrendered:true }), 'surrendered')
  assert.equal(latestStudentTest([{ ...assignment,status:'draft' }, assignment], 'student'), assignment)
  const classHtml=render(Class, '/teacher/class/class', '/teacher/class/:id')
  assert(classHtml.includes('Создать тест'))
  assert(classHtml.includes('Пригласить учеников'))
  assert(!classHtml.includes('<details open=""'))
  assert(classHtml.includes('Выполнено 4 из 5'))
  assert(classHtml.includes('Ответил сегодня'))
  assert(!classHtml.includes('???'))
  const testsHtml=render(Class, '/teacher/class/class?tab=tests', '/teacher/class/:id')
  assert(testsHtml.includes('Кодирование — проверка'))
  assert(testsHtml.includes('/teacher/assignment/test'))
  const matrixHtml=render(Matrix, '/teacher/assignment/test', '/teacher/assignment/:id')
  assert(matrixHtml.includes('Учитывается последняя попытка'))
  assert(matrixHtml.includes('Наборы различаются'))
  assert(matrixHtml.includes('<table'))
  for (const status of ['Верно','Неверно','Пропущено','Сдался','Не решал']) assert(matrixHtml.includes(status))
  const profileHtml=render(Student, '/teacher/student/student?class=class', '/teacher/student/:id')
  assert(profileHtml.includes('Граф знаний'))
  assert(profileHtml.includes('Кодирование текста'))
  const graphHtml=render(Student, '/teacher/student/student?class=class&tab=graph', '/teacher/student/:id')
  assert(graphHtml.includes('Граф знаний ученика'))
  assert(graphHtml.includes('Показать навыки без данных'))
  assert(graphHtml.includes('Выбрать навык'))
  const generatorHtml=render(Generator, '/teacher/class/class/generate?student=student&topic=Кодирование', '/teacher/class/:id/generate')
  assert(generatorHtml.includes('value="Кодирование" selected=""'))
  assert.equal((generatorHtml.match(/checked=""/g)||[]).length,1)
  const taskHtml=renderToStaticMarkup(createElement(TaskText,{text:'**Текст** $x^2$',options:{A:'$x+1$'},expected:'42'}))
  assert(taskHtml.includes('<strong>Текст</strong>'))
  assert(taskHtml.includes('class="katex"'))
  assert(taskHtml.includes('Правильный ответ'))
  const legacyHtml=renderToStaticMarkup(createElement(HistoryResponse,{attempt:{id:'r',code:'T1',task_text:'text',expected:'42',options:null,context:'legacy',assignment_title:null,answer:'41',correct:false,skipped:false,surrendered:false,time_sec:12,created_at:stamp}}))
  assert(legacyHtml.includes('До обновления · без точной привязки'))
  // Reviewable local artifacts. No real pupil information is used.
  const output = new URL('../../logs/teacher-report-preview/', import.meta.url)
  await mkdir(output,{recursive:true})
  const index = await readFile(new URL('../dist/index.html',import.meta.url),'utf8')
  const css = index.match(/href="(\/assets\/[^"]+\.css)"/)?.[1]
  for (const [name,html] of Object.entries({class:classHtml,tests:testsHtml,matrix:matrixHtml,student:profileHtml,graph:graphHtml})) {
    await writeFile(new URL(`${name}.html`,output),`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">${css ? `<link rel="stylesheet" href="../../pwa/dist${css}">` : ''}<title>Проверка · ${name}</title><body>${html}</body></html>`)
  }
  query.clear()
  console.log('Teacher report checks passed: results, routing, graph controls, generation prefill, Markdown/KaTeX')
} finally { await server.close() }
