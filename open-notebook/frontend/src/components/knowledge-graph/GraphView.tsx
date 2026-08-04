'use client'

// 知识图谱可视化组件
// 使用纯 SVG 绘制节点和边，不引入 reactflow 等新依赖
// 支持：拖拽节点、缩放、平移、节点按类型着色

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from 'react'
import type { GraphEntity, GraphRelation } from '@/lib/api/knowledge-graph'

// 节点类型对应的颜色（按类型着色）
const TYPE_COLORS: Record<string, string> = {
  person: '#3b82f6', // blue
  organization: '#8b5cf6', // purple
  concept: '#10b981', // emerald
  location: '#f59e0b', // amber
  event: '#ef4444', // red
  other: '#6b7280', // gray
}

// 获取节点颜色，未知类型使用默认色
function getColor(type: string): string {
  return TYPE_COLORS[type.toLowerCase()] || TYPE_COLORS.other
}

// 节点位置接口
interface NodePosition {
  id: string
  x: number
  y: number
  vx: number
  vy: number
}

interface GraphViewProps {
  entities: GraphEntity[]
  relations: GraphRelation[]
  onSelectEntity?: (entity: GraphEntity) => void
  onDeleteEntity?: (entityId: string) => void
  onDeleteRelation?: (relationId: string) => void
}

export function GraphView({
  entities,
  relations,
  onSelectEntity,
  onDeleteEntity,
  onDeleteRelation,
}: GraphViewProps) {
  // 视图变换状态：缩放和平移
  const [scale, setScale] = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })

  // 节点位置状态
  const [positions, setPositions] = useState<Record<string, NodePosition>>({})

  // 拖拽状态
  const dragRef = useRef<{
    nodeId: string | null
    startX: number
    startY: number
    nodeStartX: number
    nodeStartY: number
  } | null>(null)

  // 平移状态
  const panRef = useRef<{
    startX: number
    startY: number
    translateStartX: number
    translateStartY: number
  } | null>(null)

  // 选中的实体 ID
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // 圆形布局初始化节点位置
  useEffect(() => {
    setPositions((prev) => {
      const next: Record<string, NodePosition> = {}
      const count = entities.length
      const radius = Math.max(150, count * 25)
      const centerX = 400
      const centerY = 300
      entities.forEach((entity, idx) => {
        const existing = prev[entity.id]
        if (existing) {
          next[entity.id] = existing
        } else {
          // 圆形布局
          const angle = (idx / Math.max(count, 1)) * 2 * Math.PI
          next[entity.id] = {
            id: entity.id,
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
            vx: 0,
            vy: 0,
          }
        }
      })
      return next
    })
  }, [entities])

  // 简单的力导向布局（每次 relations 或 entities 变化时执行一次）
  useEffect(() => {
    if (entities.length === 0) return
    const iterations = 30
    let current = { ...positions }
    const k = 80 // 理想距离
    const repulsion = 6000 // 排斥力系数

    for (let iter = 0; iter < iterations; iter++) {
      const forces: Record<string, { x: number; y: number }> = {}
      entities.forEach((e) => {
        forces[e.id] = { x: 0, y: 0 }
      })

      // 节点间排斥力
      for (let i = 0; i < entities.length; i++) {
        for (let j = i + 1; j < entities.length; j++) {
          const a = current[entities[i].id]
          const b = current[entities[j].id]
          if (!a || !b) continue
          const dx = a.x - b.x
          const dy = a.y - b.y
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
          const force = repulsion / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          forces[entities[i].id].x += fx
          forces[entities[i].id].y += fy
          forces[entities[j].id].x -= fx
          forces[entities[j].id].y -= fy
        }
      }

      // 边的吸引力
      relations.forEach((rel) => {
        const a = current[rel.source_id]
        const b = current[rel.target_id]
        if (!a || !b) return
        const dx = b.x - a.x
        const dy = b.y - a.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = (dist * dist) / k
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        if (forces[rel.source_id]) {
          forces[rel.source_id].x += fx
          forces[rel.source_id].y += fy
        }
        if (forces[rel.target_id]) {
          forces[rel.target_id].x -= fx
          forces[rel.target_id].y -= fy
        }
      })

      // 应用力
      const updated: Record<string, NodePosition> = {}
      Object.keys(current).forEach((id) => {
        const node = current[id]
        const f = forces[id] || { x: 0, y: 0 }
        updated[id] = {
          ...node,
          x: node.x + Math.max(-10, Math.min(10, f.x * 0.1)),
          y: node.y + Math.max(-10, Math.min(10, f.y * 0.1)),
        }
      })
      current = updated
    }
    setPositions(current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entities.length, relations.length])

  // 节点拖拽处理
  const handleNodePointerDown = useCallback(
    (event: ReactPointerEvent<SVGGElement>, nodeId: string) => {
      event.stopPropagation()
      const node = positions[nodeId]
      if (!node) return
      ;(event.target as Element).setPointerCapture?.(event.pointerId)
      dragRef.current = {
        nodeId,
        startX: event.clientX,
        startY: event.clientY,
        nodeStartX: node.x,
        nodeStartY: node.y,
      }
      setSelectedId(nodeId)
    },
    [positions]
  )

  const handleNodePointerMove = useCallback(
    (event: ReactPointerEvent<SVGGElement>) => {
      if (!dragRef.current?.nodeId) return
      const dx = (event.clientX - dragRef.current.startX) / scale
      const dy = (event.clientY - dragRef.current.startY) / scale
      const nodeId = dragRef.current.nodeId
      setPositions((prev) => {
        const node = prev[nodeId]
        if (!node) return prev
        return {
          ...prev,
          [nodeId]: {
            ...node,
            x: dragRef.current!.nodeStartX + dx,
            y: dragRef.current!.nodeStartY + dy,
          },
        }
      })
    },
    [scale]
  )

  const handleNodePointerUp = useCallback(
    (event: ReactPointerEvent<SVGGElement>) => {
      ;(event.target as Element).releasePointerCapture?.(event.pointerId)
      dragRef.current = null
    },
    []
  )

  // 背景平移处理
  const handleBackgroundPointerDown = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      panRef.current = {
        startX: event.clientX,
        startY: event.clientY,
        translateStartX: translate.x,
        translateStartY: translate.y,
      }
      setSelectedId(null)
    },
    [translate]
  )

  const handleBackgroundPointerMove = useCallback(
    (event: ReactPointerEvent<SVGSVGElement>) => {
      if (!panRef.current) return
      setTranslate({
        x: panRef.current.translateStartX + (event.clientX - panRef.current.startX),
        y: panRef.current.translateStartY + (event.clientY - panRef.current.startY),
      })
    },
    []
  )

  const handleBackgroundPointerUp = useCallback(() => {
    panRef.current = null
  }, [])

  // 缩放处理（滚轮）
  const handleWheel = useCallback((event: ReactWheelEvent<SVGSVGElement>) => {
    event.preventDefault()
    const delta = event.deltaY > 0 ? 0.9 : 1.1
    setScale((prev) => Math.max(0.2, Math.min(3, prev * delta)))
  }, [])

  // 缩放按钮
  const zoomIn = () => setScale((prev) => Math.min(3, prev * 1.2))
  const zoomOut = () => setScale((prev) => Math.max(0.2, prev / 1.2))
  const resetView = () => {
    setScale(1)
    setTranslate({ x: 0, y: 0 })
  }

  // 节点点击处理
  const handleNodeClick = useCallback(
    (entity: GraphEntity) => {
      setSelectedId(entity.id)
      onSelectEntity?.(entity)
    },
    [onSelectEntity]
  )

  return (
    <div className="relative w-full h-full bg-muted/30 rounded-lg border overflow-hidden">
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 800 600"
        onPointerDown={handleBackgroundPointerDown}
        onPointerMove={handleBackgroundPointerMove}
        onPointerUp={handleBackgroundPointerUp}
        onWheel={handleWheel}
        style={{ cursor: panRef.current ? 'grabbing' : 'grab', touchAction: 'none' }}
      >
        <g
          transform={`translate(${translate.x}, ${translate.y}) scale(${scale})`}
        >
          {/* 绘制边（关系） */}
          {relations.map((rel) => {
            const source = positions[rel.source_id]
            const target = positions[rel.target_id]
            if (!source || !target) return null
            const midX = (source.x + target.x) / 2
            const midY = (source.y + target.y) / 2
            return (
              <g key={rel.id} className="cursor-pointer">
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="currentColor"
                  strokeOpacity={0.4}
                  strokeWidth={1.5}
                  className="text-foreground"
                />
                {/* 关系类型标签 */}
                <text
                  x={midX}
                  y={midY - 4}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[10px] pointer-events-none select-none"
                  style={{ fontSize: 10 }}
                >
                  {rel.type}
                </text>
                {/* 删除关系按钮（hover 时显示） */}
                {onDeleteRelation && (
                  <circle
                    cx={midX}
                    cy={midY + 8}
                    r={6}
                    fill="hsl(var(--destructive))"
                    opacity={0.7}
                    className="opacity-0 hover:opacity-100 transition-opacity cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteRelation(rel.id)
                    }}
                  />
                )}
              </g>
            )
          })}

          {/* 绘制节点（实体） */}
          {entities.map((entity) => {
            const pos = positions[entity.id]
            if (!pos) return null
            const color = getColor(entity.type)
            const isSelected = selectedId === entity.id
            const radius = isSelected ? 22 : 18
            return (
              <g
                key={entity.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onPointerDown={(e) => handleNodePointerDown(e, entity.id)}
                onPointerMove={handleNodePointerMove}
                onPointerUp={handleNodePointerUp}
                onClick={() => handleNodeClick(entity)}
                style={{ cursor: 'grab' }}
              >
                {/* 选中时的外圈 */}
                {isSelected && (
                  <circle
                    r={radius + 4}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    strokeOpacity={0.4}
                  />
                )}
                {/* 节点圆形 */}
                <circle
                  r={radius}
                  fill={color}
                  fillOpacity={0.2}
                  stroke={color}
                  strokeWidth={2}
                />
                {/* 节点名称 */}
                <text
                  y={radius + 14}
                  textAnchor="middle"
                  className="fill-foreground pointer-events-none select-none"
                  style={{ fontSize: 11, fontWeight: 500 }}
                >
                  {entity.name.length > 16
                    ? entity.name.slice(0, 16) + '…'
                    : entity.name}
                </text>
                {/* 节点类型小标签 */}
                <text
                  y={4}
                  textAnchor="middle"
                  className="fill-muted-foreground pointer-events-none select-none"
                  style={{ fontSize: 9 }}
                >
                  {entity.type}
                </text>
                {/* 删除节点按钮（选中时显示） */}
                {isSelected && onDeleteEntity && (
                  <g
                    transform={`translate(${radius - 2}, ${-radius + 2})`}
                    className="cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteEntity(entity.id)
                    }}
                  >
                    <circle r={7} fill="hsl(var(--destructive))" />
                    <text
                      y={3}
                      textAnchor="middle"
                      className="fill-white pointer-events-none select-none"
                      style={{ fontSize: 11, fontWeight: 'bold' }}
                    >
                      ×
                    </text>
                  </g>
                )}
              </g>
            )
          })}
        </g>
      </svg>

      {/* 缩放控制按钮 */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1.5 bg-background/80 backdrop-blur rounded-md p-1.5 border shadow-sm">
        <button
          onClick={zoomIn}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted text-sm font-medium"
          title="放大"
        >
          +
        </button>
        <button
          onClick={zoomOut}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted text-sm font-medium"
          title="缩小"
        >
          −
        </button>
        <button
          onClick={resetView}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted text-[10px]"
          title="重置视图"
        >
          ⟲
        </button>
      </div>

      {/* 图例 */}
      <div className="absolute top-4 left-4 bg-background/80 backdrop-blur rounded-md p-2 border shadow-sm">
        <div className="text-xs font-medium mb-1.5">实体类型</div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-[10px] text-muted-foreground capitalize">
                {type}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 空状态提示 */}
      {entities.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-sm text-muted-foreground">
            暂无知识图谱数据，请选择笔记本并提取实体
          </p>
        </div>
      )}
    </div>
  )
}
