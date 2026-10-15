// Pure draft behavior with synthetic fixtures; no browser or API required.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/pages/teacher/generationDraft.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } })
const { matchesConfiguration, replacePreviewTask } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const task = id => ({ task_id: id })
const draft = {
  topic: 'Topic', n_tasks: 2, personalize: false,
  students: ['one', 'two'].map(student_id => ({ student_id, tasks: [task('a'), task('b')] })),
}
assert(matchesConfiguration(draft, 'Topic', 2, false, ['two', 'one']))
for (const args of [['Other', 2, false, ['one', 'two']], ['Topic', 3, false, ['one', 'two']],
  ['Topic', 2, true, ['one', 'two']], ['Topic', 2, false, ['one']]]) {
  assert.equal(matchesConfiguration(draft, ...args), false)
}
const common = replacePreviewTask(draft, 'one', 0, 'a', task('c'))
assert.deepEqual(common.students.map(s => s.tasks.map(t => t.task_id)), [['c', 'b'], ['c', 'b']])
assert.deepEqual(draft.students[0].tasks.map(t => t.task_id), ['a', 'b'])
assert.notEqual(common.students[0].tasks[0], common.students[1].tasks[0])
assert.deepEqual(common.usage_stats, { total_tasks_used: 4, unique_tasks_used: 2, max_usage: 2 })
assert.equal(replacePreviewTask(draft, 'one', 0, 'stale', task('c')), draft)
assert.equal(replacePreviewTask(draft, 'one', 0, 'a', task('b')), draft)
const personal = replacePreviewTask({ ...draft, personalize: true }, 'one', 0, 'a', task('c'))
assert.deepEqual(personal.students.map(s => s.tasks.map(t => t.task_id)), [['c', 'b'], ['a', 'b']])
assert.deepEqual(personal.usage_stats, { total_tasks_used: 4, unique_tasks_used: 3, max_usage: 2 })
console.log('Generation draft checks passed')
