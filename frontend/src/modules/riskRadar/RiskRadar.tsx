import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Database, ListChecks, Sparkles, X } from 'lucide-react'
import { useBrand } from '../../theme/BrandProvider'
import { SIGNALS, riskScore, band, type Project } from './data'
import { useProjects } from '../../data/ProjectsProvider'
import { ScoreBar, Sparkline, StatusBadge, useTooltip } from '../../components/viz'
import { GeniePanel, type AutoAsk } from './GeniePanel'
import { FollowUpPanel } from '../../components/FollowUps'
import { projectSuggestions } from './insights'

const pendingCoM = (pr: Project) => pr.pendingCoUsd != null ? pr.pendingCoUsd / 1e6 : Math.round(pr.signals.co * pr.contractValueM * 0.002) / 100

export function RiskRadar({ onOpenResolve }: { onOpenResolve: (projectId: string) => void }) {
  const brand = useBrand()
  const [sector, setSector] = useState<string>('All')
  const [region, setRegion] = useState<string>('All')
  const [selectedId, setSelectedId] = useState<string>('P-1001')
  const { bind, node: tooltip } = useTooltip()
  const { projects: PROJECTS, live, loading } = useProjects()
  const [autoAsk, setAutoAsk] = useState<AutoAsk>()
  const [fuPrefill, setFuPrefill] = useState<string>()
  /** Slide-over drawer (right edge) for Ask Genie + Follow-ups — keeps the page short so the heat map stays in view. */
  const [drawer, setDrawer] = useState<null | 'genie' | 'followups'>(null)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawer(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  /** Double-click: select the project and ask Genie its status-appropriate first question. */
  const askAbout = (p: Project) => {
    setSelectedId(p.id)
    setDrawer('genie')
    setAutoAsk({ question: projectSuggestions(p)[0].q, nonce: Date.now() })
  }

  const rows = useMemo(
    () =>
      PROJECTS.filter((p) => (sector === 'All' || p.sector === sector) && (region === 'All' || p.region === region))
        .map((p) => {
          const score = riskScore(p)
          const shift = score - p.trend[p.trend.length - 1]
          return { ...p, score, trend: p.trend.map((v) => v + shift) }
        })
        .sort((a, b) => b.score - a.score),
    [sector, region, PROJECTS],
  )
  const selected = rows.find((r) => r.id === selectedId) ?? rows[0]
  // Keep the selected row visible inside the scrolling list (e.g. when picked from the heat map) — without moving the page.
  useEffect(() => {
    const box = document.querySelector<HTMLElement>('.table-scroll')
    const row = box?.querySelector<HTMLElement>(`tr[data-pid="${selected?.id}"]`)
    if (!box || !row) return
    const head = box.querySelector('thead')?.getBoundingClientRect().height ?? 0
    if (row.offsetTop - head < box.scrollTop) box.scrollTo({ top: row.offsetTop - head, behavior: 'smooth' })
    else if (row.offsetTop + row.offsetHeight > box.scrollTop + box.clientHeight) box.scrollTo({ top: row.offsetTop + row.offsetHeight - box.clientHeight, behavior: 'smooth' })
  }, [selected?.id])
  if (loading) return <div className="page"><p className="muted">Loading live project data from Unity Catalog…</p></div>
  const needsAttention = rows.filter((r) => r.score >= 55).length
  const coExposure = rows.reduce((a, r) => a + pendingCoM(r), 0)
  const avg = rows.length ? Math.round(rows.reduce((a, r) => a + r.score, 0) / rows.length) : 0
  const backlog = rows.reduce((a, r) => a + r.contractValueM, 0)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Portfolio Risk Radar</p>
        </div>
        <div className="sources" title="Systems of record — read-only. Control Tower adds intelligence on top.">
          <span className={`chip ${live ? '' : 'chip-ghost'}`} title={live ? 'Live from Unity Catalog metric view project_risk_mv' : 'Backend not reachable — bundled sample data'}>{loading ? 'Loading…' : live ? '● Live data' : 'Sample data'}</span>
          <Database size={14} aria-hidden />
          <span>Sources</span>
          {brand.systemsOfRecord.map((s) => (
            <span key={s} className="chip chip-ghost">{s}</span>
          ))}
        </div>
      </header>

      <div className="filters" role="toolbar" aria-label="Filters">
        <div className="segmented" role="radiogroup" aria-label="Market sector">
          {['All', ...brand.sectors].map((s) => (
            <button key={s} role="radio" aria-checked={sector === s} className={sector === s ? 'on' : ''} onClick={() => setSector(s)}>
              {s === 'All' ? 'All sectors' : s}
            </button>
          ))}
        </div>
        <label className="select">
          Region
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {['All', ...brand.regions].map((r) => <option key={r}>{r}</option>)}
          </select>
        </label>
      </div>

      <section className="kpis" aria-label="Portfolio summary">
        <Kpi label="Active projects" value={String(rows.length)} sub={`$${(backlog / 1000).toFixed(1)}B contract value`} />
        <Kpi label="Need attention" value={String(needsAttention)} sub="Risk score ≥ 55" emphasis />
        <Kpi label="Pending CO exposure" value={`$${coExposure.toFixed(1)}M`} sub="Unapproved, Clearstory" />
        <Kpi label="Avg. risk score" value={String(avg)} sub="0–100 · project_risk_mv" />
      </section>

      <div className="grid-main">
        <section className="card">
          <div className="card-head">
            <h2>Ranked projects</h2>
            <span className="muted">{rows.length} projects · composite score from one metric-view definition — same in dashboard, Genie, and MCP</span>
          </div>
          <div className="table-scroll" tabIndex={-1}>
          <table className="table">
            <thead>
              <tr>
                <th>#</th><th>Project</th><th>Risk score</th><th>Status</th><th>8-week trend</th><th>Top driver</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.id} data-pid={r.id} className={r.id === selected?.id ? 'selected' : ''} onClick={() => setSelectedId(r.id)} onDoubleClick={() => askAbout(r)} tabIndex={0} title="Double-click to ask Genie about this project"
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedId(r.id)}>
                  <td className="rank">{i + 1}</td>
                  <td>
                    <div className="proj-name">{r.name}</div>
                    <div className="muted small">{r.sector} · {r.region} · {r.pctComplete}% complete</div>
                  </td>
                  <td><ScoreBar value={r.score} band={band(r.score)} /></td>
                  <td><StatusBadge band={band(r.score)} /></td>
                  <td><Sparkline values={r.trend} /></td>
                  <td className="small">{r.headline}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </section>

        <aside className="side">
          {selected && (
            <section className="card detail">
              <p className="eyebrow">{selected.id} · {selected.sector}</p>
              <h3>{selected.name}</h3>
              <div className="detail-score">
                <span className="big">{selected.score}</span>
                <StatusBadge band={band(selected.score)} />
              </div>
              <ul className="signal-list">
                {SIGNALS.map((s) => (
                  <li key={s.key}>
                    <span>{s.label}<span className="muted small"> · {s.source}</span></span>
                    <span className="mini-bar"><span style={{ width: `${selected.signals[s.key]}%` }} /></span>
                    <span className="num">{selected.signals[s.key]}</span>
                  </li>
                ))}
              </ul>
              <div className="detail-actions">
                <button className="btn btn-primary" onClick={() => setDrawer('genie')}><Sparkles size={15} aria-hidden /> Ask Genie</button>
                <button className="btn btn-ghost" onClick={() => setDrawer('followups')}><ListChecks size={15} aria-hidden /> Follow-ups</button>
              </div>
              <button className="btn btn-accent" onClick={() => onOpenResolve(selected.id)}>
                Resolve open items <ArrowRight size={16} aria-hidden />
              </button>
            </section>
          )}
        </aside>
      </div>

      <div className={`drawer ${drawer ? 'open' : ''}`} role="dialog" aria-label="Project assistant" aria-hidden={!drawer}>
        <div className="drawer-head">
          <div className="segmented" role="tablist">
            <button role="tab" aria-selected={drawer === 'genie'} className={drawer === 'genie' ? 'on' : ''} onClick={() => setDrawer('genie')}>Ask Genie</button>
            <button role="tab" aria-selected={drawer === 'followups'} className={drawer === 'followups' ? 'on' : ''} onClick={() => setDrawer('followups')}>Follow-ups</button>
          </div>
          <span className="muted small drawer-proj">{selected?.name.split(' — ')[0]}</span>
          <button className="icon-btn" onClick={() => setDrawer(null)} aria-label="Close panel"><X size={18} /></button>
        </div>
        <div className="drawer-body">
          {/* Both stay mounted so the Genie conversation survives tab switches. */}
          <div hidden={drawer !== 'genie'}>
            <GeniePanel project={selected} sector={sector} region={region} autoAsk={autoAsk} onAssign={(note) => { setFuPrefill(note); setDrawer('followups') }} />
          </div>
          <div hidden={drawer !== 'followups'}>
            {selected && <FollowUpPanel projectId={selected.id} prefill={fuPrefill} onPrefillUsed={() => setFuPrefill(undefined)}
              ownerHints={['Project executive', 'Superintendent', 'Structural engineer (EOR)', 'Architect', 'Project controls', 'Subcontractor PM']} />}
          </div>
        </div>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Signal heat map</h2>
          <span className="muted">Sub-score 0–100 per signal · green = low risk, red-brown = high risk</span>
        </div>
        <div className="heat" style={{ gridTemplateColumns: `minmax(220px, 1.6fr) repeat(${SIGNALS.length}, 1fr)` }}>
          <div />
          {SIGNALS.map((s) => <div key={s.key} className="heat-col">{s.short}<span className="muted small">{s.source}</span></div>)}
          {rows.map((r) => (
            <HeatRow key={r.id} r={r} bind={bind} selected={r.id === selected?.id} onSelect={() => setSelectedId(r.id)} onAsk={() => askAbout(r)} />
          ))}
        </div>
        <div className="heat-legend" aria-label="Color scale">
          <span className="muted small">Low risk</span>
          {[0, 1, 2, 3, 4, 5, 6].map((i) => <span key={i} className="swatch" style={{ background: `var(--risk-${i})` }} />)}
          <span className="muted small">High risk</span>
        </div>
      </section>
      {tooltip}
    </div>
  )
}

/** Sub-score cut points for the 7-step diverging scale (step 3 = neutral, ~45–54). */
const RISK_THRESHOLDS = [25, 35, 45, 55, 65, 75]

function HeatRow({ r, bind, selected, onSelect, onAsk }: { r: Project & { score: number }; bind: ReturnType<typeof useTooltip>['bind']; selected: boolean; onSelect: () => void; onAsk: () => void }) {
  return (
    <>
      <button className={`heat-label ${selected ? 'on' : ''}`} onClick={onSelect} onDoubleClick={onAsk} title="Double-click to ask Genie">{r.name.split(' — ')[0]}</button>
      {SIGNALS.map((s) => {
        const v = r.signals[s.key]
        const step = RISK_THRESHOLDS.filter((t) => v >= t).length
        return (
          <div key={s.key} className="heat-cell" style={{ background: `var(--risk-${step})`, color: step <= 0 || step >= 5 ? '#fff' : 'var(--ink)' }}
            {...bind(<><strong>{r.name}</strong><br />{s.label}: {v}<br /><span className="muted">Source: {s.source}</span></>)}>
            {v >= 70 ? v : ''}
          </div>
        )
      })}
    </>
  )
}

function Kpi({ label, value, sub, emphasis }: { label: string; value: string; sub: string; emphasis?: boolean }) {
  return (
    <div className={`kpi ${emphasis ? 'kpi-emph' : ''}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      <span className="muted small">{sub}</span>
    </div>
  )
}
