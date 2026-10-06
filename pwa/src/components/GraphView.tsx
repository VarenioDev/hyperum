/**
 * Визуализация графа знаний через Cytoscape.js.
 *
 * Layout строится только по видимым узлам.
 * При переключении showUnknown — layout перестраивается с анимацией.
 */
import { useEffect, useRef } from 'react'
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape'
import type { StudentGraph, GraphNode } from '../api/graph'

interface Props {
  graph: StudentGraph
  onNodeClick?: (node: GraphNode) => void
  showUnknown?: boolean
  height?: string
}

const LAYOUT_OPTS = {
  name: 'cose',
  animate: false,
  fit: false, // fit вызываем вручную
  padding: 40,
  nodeRepulsion: () => 8000,
  idealEdgeLength: () => 50,
  edgeElasticity: () => 100,
  gravity: 0.4, // сильнее тянет к центру — узлы рядышком
  numIter: 1000,
  randomize: true,
} as const

export default function GraphView({
  graph,
  onNodeClick,
  showUnknown = false,
  height = '500px',
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  const onNodeClickRef = useRef(onNodeClick)
  useEffect(() => {
    onNodeClickRef.current = onNodeClick
  }, [onNodeClick])

  const isFirstFit = useRef(true)

  // ─── Создание графа ────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return

    const elements: ElementDefinition[] = [
      ...graph.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.name,
          status: n.status,
          mastery: n.mastery ?? 0,
          nodeKind: n.status === 'unknown' ? 'unknown' : 'known',
        },
      })),
      ...graph.edges.map((e, i) => {
        const src = graph.nodes.find((n) => n.id === e.source)
        const tgt = graph.nodes.find((n) => n.id === e.target)
        const touchesUnknown =
          src?.status === 'unknown' || tgt?.status === 'unknown'
        return {
          data: {
            id: `e-${i}`,
            source: e.source,
            target: e.target,
            edgeKind: touchesUnknown ? 'to-unknown' : 'between-known',
          },
        }
      }),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,

      style: [
        // ─── Узлы ───
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'font-family': 'Montserrat Alternates, system-ui, sans-serif',
            'font-size': '9px',
            'font-weight': 500,
            'color': '#1e293b',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'border-width': 2,
            'border-color': '#ffffff',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
          },
        },
        {
          selector: 'node[status = "mastered"]',
          style: { 'background-color': '#22c55e', 'width': 26, 'height': 26 },
        },
        {
          selector: 'node[status = "learning"]',
          style: { 'background-color': '#eab308', 'width': 24, 'height': 24 },
        },
        {
          selector: 'node[status = "weak"]',
          style: { 'background-color': '#ef4444', 'width': 24, 'height': 24 },
        },
        {
          selector: 'node[status = "unknown"]',
          style: {
            'background-color': '#374151',
            'width': 8,
            'height': 8,
            'label': '',
            'border-width': 0,
            'opacity': 0.5,
          },
        },
        // ─── Рёбра — теперь заметные ───
        {
          selector: 'edge',
          style: {
            'width': 1.8,
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1,
            'opacity': 0.7,
          },
        },
        {
          selector: 'edge[edgeKind = "to-unknown"]',
          style: {
            'width': 1,
            'line-color': '#cbd5e1',
            'target-arrow-shape': 'none',
            'opacity': 0.3,
          },
        },
        // ─── Активный узел ───
        {
          selector: 'node:active',
          style: {
            'border-width': 4,
            'border-color': '#ec4899',
            'opacity': 1,
          },
        },
      ],

      // Начальный layout — preset, дальше запустим вручную
      layout: { name: 'preset' },

      minZoom: 0.2,
      maxZoom: 4,
    })

    cyRef.current = cy

    cy.on('tap', 'node', (evt) => {
      const id = evt.target.id()
      const node = graph.nodes.find((n) => n.id === id)
      if (node && onNodeClickRef.current) onNodeClickRef.current(node)
    })

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graph])

  // ─── Показ/скрытие unknown + layout + fit ──────────────
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return

    // 1. Скрываем/показываем
    if (showUnknown) {
      cy.elements().style('display', 'element')
    } else {
      cy.elements('node[nodeKind = "unknown"]').style('display', 'none')
      cy.elements('edge[edgeKind = "to-unknown"]').style('display', 'none')
    }

    // 2. Собираем видимые элементы
    const visible = cy.elements().filter(
      (ele) => ele.style('display') !== 'none'
    )

    if (visible.length === 0) return

    // 3. Запускаем layout — только по видимым
    const layout = visible.layout({
      ...(LAYOUT_OPTS as any),
    } as any)

    layout.run()

    // 4. Fit: первый раз — мгновенно, дальше — с анимацией
    if (isFirstFit.current) {
      cy.fit(undefined, 40)
      isFirstFit.current = false
    } else {
      cy.animate(
        { fit: { eles: visible, padding: 40 } },
        { duration: 450, easing: 'ease-in-out' }
      )
    }
  }, [showUnknown, graph])

  return (
    <div className="relative rounded-3xl overflow-hidden">
      <div className="absolute inset-0 glass-strong pointer-events-none" />
      <div
        ref={containerRef}
        style={{ height, width: '100%' }}
        className="relative"
      />
    </div>
  )
}