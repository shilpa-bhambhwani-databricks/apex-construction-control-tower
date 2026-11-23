import { useState, type ReactNode } from 'react'
import { AlertOctagon, AlertTriangle, CheckCircle2, Eye } from 'lucide-react'
import type { Band } from '../modules/riskRadar/data'
import { BAND_LABEL } from '../modules/riskRadar/data'

/** Fixed status palette (dataviz skill reference) — never themed, always icon + label. */
export const STATUS: Record<Band, string> = { critical: '#d03b3b', serious: '#ec835a', warning: '#fab219', good: '#0ca30c' }
const ICON: Record<Band, typeof AlertOctagon> = { critical: AlertOctagon, serious: AlertTriangle, warning: Eye, good: CheckCircle2 }

export function StatusBadge({ band }: { band: Band }) {
  const Icon = ICON[band]
  return (
    <span className="status-badge">
      <Icon size={13} color={STATUS[band]} strokeWidth={2.5} aria-hidden />
      {BAND_LABEL[band]}
    </span>
  )
}

/** Single-series sparkline: 2px line, end-point marker, no legend (title names it). */
export function Sparkline({ values, width = 96, height = 28 }: { values: number[]; width?: number; height?: number }) {
  const min = Math.min(...values) - 4
  const max = Math.max(...values) + 4
  const x = (i: number) => (i / (values.length - 1)) * (width - 6) + 3
  const y = (v: number) => height - 3 - ((v - min) / (max - min)) * (height - 6)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const last = values[values.length - 1]
  const delta = Math.round(last - values[0])
  return (
    <span className="spark">
      <svg width={width} height={height} role="img" aria-label={`8-week trend ${Math.round(values[0])} to ${Math.round(last)}`}>
        <path d={d} fill="none" stroke="var(--primary)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={x(values.length - 1)} cy={y(last)} r={3} fill="var(--primary)" stroke="var(--surface)" strokeWidth={2} />
      </svg>
      <span className={`spark-delta ${delta > 0 ? 'up' : 'down'}`}>{delta > 0 ? '▲' : '▼'} {Math.abs(delta)}</span>
    </span>
  )
}

/** Thin horizontal magnitude bar, rounded data-end, anchored at baseline. */
export function ScoreBar({ value, band }: { value: number; band: Band }) {
  return (
    <span className="scorebar">
      <span className="scorebar-track">
        <span className="scorebar-fill" style={{ width: `${value}%`, background: STATUS[band] }} />
      </span>
      <span className="scorebar-value">{value}</span>
    </span>
  )
}

/** Shared hover tooltip. Wrap any mark; tooltip follows the pointer. */
export function useTooltip() {
  const [tip, setTip] = useState<{ x: number; y: number; content: ReactNode } | null>(null)
  const bind = (content: ReactNode) => ({
    onMouseMove: (e: React.MouseEvent) => setTip({ x: e.clientX, y: e.clientY, content }),
    onMouseLeave: () => setTip(null),
  })
  const node = tip ? (
    <div className="tooltip" style={{ left: tip.x + 14, top: tip.y + 14 }} role="tooltip">
      {tip.content}
    </div>
  ) : null
  return { bind, node }
}

/** Single-series horizontal bars with direct value labels (no legend needed). */
export function Contrib({ rows, max, format = (v) => String(v) }: { rows: [string, number][]; max: number; format?: (v: number) => string }) {
  return (
    <div className="contrib">
      {rows.map(([k, v]) => (
        <div key={k} className="contrib-row">
          <span>{k}</span>
          <span className="contrib-track"><span style={{ width: `${max > 0 ? Math.max(2, (v / max) * 100) : 0}%` }} /></span>
          <span className="num">{format(v)}</span>
        </div>
      ))}
    </div>
  )
}
