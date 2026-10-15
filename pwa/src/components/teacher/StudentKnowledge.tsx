import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getStudentGraph, type GraphNode } from '../../api/graph'
import { getStudentResponses } from '../../api/teacher'
import { ReportError } from './ReportUI'
import { HistoryPagination, HistoryResponse } from './AttemptDetails'
import GraphView from '../GraphView'

const statuses = { mastered: 'Освоено', learning: 'В процессе', weak: 'Требует внимания', unknown: 'Нет данных' }
export default function StudentKnowledge({ studentId, onGenerate }: { studentId: string; onGenerate: (topic?: string) => void }) {
  const [topic, setTopic] = useState('')
  const [showUnknown, setShowUnknown] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const query = useQuery({ queryKey: ['teacher-student-graph', studentId], queryFn: () => getStudentGraph(studentId) })
  const topics = [...new Set(query.data?.nodes.map(n => n.topic).filter((v): v is string => Boolean(v)))].sort()
  const graph = useMemo(() => {
    if (!query.data) return null
    const nodes = query.data.nodes.filter(n => !topic || n.topic === topic)
    const ids = new Set(nodes.map(n => n.id))
    return { ...query.data, nodes, edges: query.data.edges.filter(e => ids.has(e.source) && ids.has(e.target)) }
  }, [query.data, topic])
  const selected = graph?.nodes.find(n => n.id === selectedId)
  const visibleNodes = graph?.nodes.filter(n => showUnknown || n.status !== 'unknown') || []
  return <section className="space-y-4">
    <div><h2 className="font-semibold text-slate-800">Граф знаний ученика</h2><p className="text-xs text-slate-500 mt-2">Связи показывают, какие навыки опираются друг на друга. Выбери узел, чтобы посмотреть ответы и подобрать следующий тест.</p></div>
    {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем граф знаний…</p>}
    {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
    {graph && <>
      <div className="flex flex-wrap gap-4 items-center glass rounded-2xl p-4">
        <label className="text-sm text-slate-700 flex-1">Тема<select value={topic} onChange={e => { setTopic(e.target.value); setSelectedId(null) }} className="block mt-2 w-full rounded-xl bg-white px-3 py-2 text-sm"><option value="">Все темы</option>{topics.map(t => <option key={t}>{t}</option>)}</select></label>
        <label className="flex gap-2 items-center text-xs text-slate-600"><input type="checkbox" checked={showUnknown} onChange={e => { setShowUnknown(e.target.checked); setSelectedId(null) }} className="accent-pink-500" />Показать навыки без данных</label>
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-slate-600"><span>🟢 Освоено</span><span>🟡 В процессе</span><span>🔴 Требует внимания</span><span>⚪ Нет данных</span></div>
      {!visibleNodes.length ? <p className="glass rounded-2xl p-5 text-sm text-slate-500">По выбранным навыкам пока нет ответов. Включи навыки без данных, чтобы увидеть структуру темы.</p> : <GraphView graph={graph} showUnknown={showUnknown} onNodeClick={node => setSelectedId(node.id)} height="460px" />}
      <p className="text-xs text-slate-500">Граф можно перемещать и масштабировать. На телефоне и с клавиатуры удобно выбирать навык из списка ниже.</p>
      <label className="block text-sm text-slate-700">Выбрать навык<select value={selectedId || ''} onChange={e => setSelectedId(e.target.value || null)} className="block mt-2 w-full rounded-xl bg-white px-3 py-3 text-sm"><option value="">Выбери навык</option>{visibleNodes.map(n => <option key={n.id} value={n.id}>{n.name} · {statuses[n.status]}</option>)}</select></label>
      {selected && <SkillEvidence key={selected.id} studentId={studentId} node={selected} onGenerate={onGenerate} />}
    </>}
  </section>
}
function SkillEvidence({ studentId, node, onGenerate }: { studentId: string; node: GraphNode; onGenerate: (topic?: string) => void }) {
  const [offset, setOffset] = useState(0)
  const query = useQuery({ queryKey: ['teacher-skill-responses', studentId, node.id, offset], queryFn: () => getStudentResponses(studentId, node.id, offset) })
  return <section className="glass-strong rounded-3xl p-5 space-y-4" aria-label={`Навык: ${node.name}`}>
    <div><p className="text-xs text-brand-700">{statuses[node.status]} · {node.topic}</p><h3 className="text-lg font-semibold text-slate-800 mt-1">{node.name}</h3>
      <p className="text-sm text-slate-600 mt-2">{node.mastery == null ? 'Недостаточно данных для оценки освоения' : `Освоение ${Math.round(node.mastery * 100)}% · попыток: ${node.attempts ?? 0}`}</p>
      <p className="text-xs text-slate-400 mt-1">Освоение учитывает историю ответов; результат теста — последнюю попытку в этом тесте.</p>
    </div>
    {node.topic && <button type="button" onClick={() => onGenerate(node.topic!)} className="text-sm font-semibold text-brand-700 bg-brand-50 rounded-xl px-4 py-3">Подобрать тест по этой теме →</button>}
    <h4 className="text-sm font-medium text-slate-700">Ответы по навыку</h4>
    {query.isPending && <p role="status" className="text-sm text-slate-500">Загружаем ответы…</p>}
    {query.isError && <ReportError error={query.error} retry={() => query.refetch()} />}
    {query.data && <>{!query.data.items.length && <p className="text-sm text-slate-500">Ответов по этому навыку пока нет.</p>}{query.data.items.map(r => <HistoryResponse key={r.id} attempt={r} />)}<HistoryPagination offset={offset} hasMore={query.data.has_more} onChange={setOffset} /></>}
  </section>
}
