import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, ExternalLink, GitBranch, Loader2, Search, Calculator, ScrollText, Sparkles, ThumbsUp, X, Check, FileSearch } from 'lucide-react'
import { useBrand } from '../../theme/BrandProvider'
import { useProjects } from '../../data/ProjectsProvider'
import { apiHeaders } from '../../api/genie'
import { Md } from '../../components/Markdown'
import { FollowUpPanel } from '../../components/FollowUps'
import { ResolveMock } from './ResolveMock'

/**
 * Resolve — live. Backlog + details from Unity Catalog (as the selected identity), Resolve agent answers
 * (AI Search + UC functions, MLflow-traced), decisions logged in Lakebase. Procore/Clearstory stay the systems of record.
 */
interface BacklogItem { id: string; kind: 'CO' | 'RFI'; title: string; status: string; subcontractor?: string; cost_code?: string; amount_requested?: string; days_pending?: string; days_open?: string; discipline?: string; ball_in_court?: string }
interface Detail { id: string; kind: 'CO' | 'RFI'; project: { project_id: string; name: string; region: string }; header: Record<string, string | null>; lines: Record<string, string>[]; context: { label: string; value: string; source: string }[] }
interface Step { tool: string; label: string; summary: string; latency_s: number }
interface AgentReply { answer: string; steps: Step[]; trace_id: string; trace_url: string; model: string }
interface Decision { id: number; item_id: string; decision: string; rationale?: string; decided_by: string; created_at: string; trace_id?: string }

const money = (v?: string | number | null) => (v == null ? '—' : Number(v) >= 1e6 ? `$${(Number(v) / 1e6).toFixed(2)}M` : `$${Math.round(Number(v)).toLocaleString()}`)
const shortName = (n: string) => n.split(' — ')[0]
const get = async <T,>(url: string): Promise<T> => { const r = await fetch(url, { headers: apiHeaders() }); if (!r.ok) throw new Error((await r.text()) || String(r.status)); return r.json() }
const post = async <T,>(url: string, body: unknown): Promise<T> => {
  const r = await fetch(url, { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) })
  if (!r.ok) { let m = await r.text(); try { m = JSON.parse(m).detail ?? m } catch { /* plain */ } throw new Error(m) }
  return r.json()
}

const QUESTIONS = {
  CO: ['Is this change order covered by the prime contract, and is the pricing in line with similar work in this region?',
       'What should we send back to the subcontractor, and what number should we negotiate to?'],
  RFI: ['Has a similar RFI come up before, and how was it resolved?',
        'What work is blocked if this RFI stays open another week, and who needs to act?'],
}
const PLANNED = {
  CO: [{ icon: FileSearch, label: 'Reading change order line items' }, { icon: Search, label: 'Searching contracts & specs' }, { icon: ScrollText, label: 'Checking notice dates (daily logs, letters)' }, { icon: Calculator, label: 'Pulling unit-cost baseline' }],
  RFI: [{ icon: Search, label: 'Finding similar past RFIs' }, { icon: ScrollText, label: 'Summarizing resolutions' }],
}

export function Resolve({ projectId: initial }: { projectId?: string }) {
  const label = useBrand().moduleLabels?.resolve ?? 'Resolve'
  const { projects, live, loading } = useProjects()
  const [projectId, setProjectId] = useState(initial ?? 'P-1001')
  const project = projects.find((p) => p.id === projectId) ?? projects[0]
  const [items, setItems] = useState<BacklogItem[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [selectedId, setSelectedId] = useState<string>()

  useEffect(() => {
    if (!project) return
    setItems(null); setSelectedId(undefined)
    get<{ items: BacklogItem[] }>(`/api/resolve/backlog?project_id=${project.id}`)
      .then((r) => { setItems(r.items); setSelectedId(r.items.find((i) => i.id === 'CO-0142')?.id ?? r.items[0]?.id) })
      .catch(() => setFailed(true))
  }, [project?.id])

  if (loading) return <div className="page"><p className="muted">Loading live project data from Unity Catalog…</p></div>
  if (!live || failed) return <ResolveMock projectId={projectId} />
  if (!project) return <div className="page"><p className="muted">Loading…</p></div>

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow">{label} · {shortName(project.name)}</p>
        <div className="head-actions">
          <label className="select">Project
            <select value={project.id} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{shortName(p.name)} · {p.sector}</option>)}
            </select>
          </label>
          <span className="chip">● Live · Resolve agent</span>
        </div>
      </header>
      <div className="grid-resolve">
        <section className="card">
          <div className="card-head"><h2>Backlog</h2><span className="muted small">Clearstory · Procore (read-only)</span></div>
          {items == null ? <p className="muted small"><Loader2 size={14} className="spin" aria-hidden /> Loading pending COs and aging RFIs…</p> : items.length === 0 ? <p className="muted small">No pending COs or aging RFIs.</p> : (
            <ul className="backlog" role="listbox" aria-label="Backlog items">
              {items.map((b) => (
                <li key={b.id} role="option" aria-selected={b.id === selectedId} tabIndex={0} className={b.id === selectedId ? 'selected' : ''}
                  onClick={() => setSelectedId(b.id)} onKeyDown={(e) => e.key === 'Enter' && setSelectedId(b.id)}>
                  <div><strong>{b.id}</strong> <span className={`pill pill-${b.status.replace(/\s/g, '').toLowerCase()}`}>{b.status}</span></div>
                  <div>{b.title}</div>
                  <div className="muted small">{b.kind === 'CO' ? `${b.subcontractor} · ${b.cost_code} · ${money(b.amount_requested)} · ${b.days_pending} d pending` : `${b.discipline} · ${b.days_open} days open · ${b.ball_in_court ?? ''}`}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
        {selectedId ? <ItemPanel key={`${project.id}-${selectedId}`} projectId={project.id} itemId={selectedId} /> : <section className="card"><p className="muted">Select an item.</p></section>}
      </div>
    </div>
  )
}

function ItemPanel({ projectId, itemId }: { projectId: string; itemId: string }) {
  const [d, setD] = useState<Detail | null>(null)
  const [err, setErr] = useState<string>()
  const [asked, setAsked] = useState<string>()
  const [reply, setReply] = useState<AgentReply | null>(null)
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0)
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [fuPrefill, setFuPrefill] = useState<string>()
  const system = itemId.startsWith('CO') ? 'Clearstory' : 'Procore'

  const loadDecisions = () => get<Decision[]>(`/api/resolve/decisions?project_id=${projectId}`).then((r) => setDecisions(r.filter((x) => x.item_id === itemId))).catch(() => {})
  useEffect(() => { get<Detail>(`/api/resolve/item?project_id=${projectId}&item_id=${itemId}`).then(setD).catch((e) => setErr(String(e.message))); loadDecisions() }, [projectId, itemId]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!busy) return; const t = setInterval(() => setTick((x) => x + 1), 1000); return () => clearInterval(t) }, [busy])

  const ask = async (q: string) => {
    setAsked(q); setReply(null); setErr(undefined); setBusy(true); setTick(0)
    try { setReply(await post<AgentReply>('/api/resolve/ask', { project_id: projectId, item_id: itemId, question: q })) }
    catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  const recommendation = useMemo(() => reply?.answer.split('**Recommendation**')[1]?.replace(/\[[^\]]+\]/g, '').trim().slice(0, 900), [reply])
  const decide = async (decision: string) => {
    const rationale = window.prompt(`Rationale for "${decision}" (logged in Control Tower):`, recommendation ?? '')
    if (rationale == null) return
    try { await post('/api/resolve/decisions', { project_id: projectId, item_id: itemId, decision, rationale, trace_id: reply?.trace_id }); loadDecisions() }
    catch (e) { setErr((e as Error).message) }
  }

  if (err && !d) return <section className="card"><p className="fu-msg bad"><X size={14} aria-hidden /> {err}</p></section>
  if (!d) return <section className="card"><p className="muted small"><Loader2 size={14} className="spin" aria-hidden /> Loading record…</p></section>
  const h = d.header
  const fields: [string, string][] = d.kind === 'CO'
    ? [['Requested', money(h.amount_requested)], ['Subcontractor', h.subcontractor ?? '—'], ['Cost code', h.cost_code ?? '—'], ['Submitted', h.submitted_date ?? '—'], ['Status', h.status ?? '—'], ['Region', d.project.region]]
    : [['Discipline', h.discipline ?? '—'], ['Created', h.created_date ?? '—'], ['Due', h.due_date ?? '—'], ['Ball in court', h.ball_in_court ?? '—'], ['Cost impact', h.cost_impact_flag === 'true' ? 'Yes' : 'No'], ['Schedule impact', h.schedule_impact_flag === 'true' ? 'Yes' : 'No']]
  const planned = PLANNED[d.kind]
  const latest = decisions[0]

  return (
    <div className="resolve-main">
      <section className="card">
        <div className="card-head"><h2>{d.id} · {d.kind === 'CO' ? h.description : h.subject}</h2><span className={`pill pill-${(h.status ?? '').replace(/\s/g, '').toLowerCase()}`}>{h.status} in {system}</span></div>
        <dl className="fields">{fields.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        {d.lines.length > 0 && (
          <table className="mini-table">
            <thead><tr><th>#</th><th>Line item</th><th>Qty</th><th>Unit rate</th><th>Amount</th></tr></thead>
            <tbody>{d.lines.sort((a, b) => Number(a.line) - Number(b.line)).map((l) => <tr key={l.line}><td>{l.line}</td><td>{l.item_desc}</td><td>{Number(l.quantity).toLocaleString()} {l.unit}</td><td>${Number(l.unit_rate).toLocaleString()}</td><td>{money(l.line_amount)}</td></tr>)}</tbody>
          </table>
        )}
        {d.context.length > 0 && (
          <div className="context">
            <span className="muted small">Context from other systems</span>
            {d.context.map((c) => <div key={c.label} className="context-row"><strong>{c.label}</strong> {c.value} <span className="chip chip-ghost">{c.source}</span></div>)}
          </div>
        )}
      </section>

      <section className="card">
        <div className="card-head"><h2><Sparkles size={16} aria-hidden /> Ask about {d.id}</h2><span className="chip">Resolve agent · {reply?.model?.replace('databricks-', '') ?? 'Claude via Databricks'}</span></div>
        {!asked && <div className="suggestions">{QUESTIONS[d.kind].map((q) => <button key={q} className="suggestion" onClick={() => ask(q)}>{q}</button>)}</div>}
        {asked && <div className="genie-msg user">{asked}</div>}
        {busy && (
          <ol className="steps">
            {planned.map((s, i) => {
              const state = tick >= (i + 1) * 5 ? 'done' : tick >= i * 5 ? 'now' : ''
              return <li key={s.label} className={state}>{state === 'now' ? <Loader2 size={14} className="spin" aria-hidden /> : <s.icon size={14} aria-hidden />} {s.label}</li>
            })}
            <li className="muted small">Agent working · {tick}s</li>
          </ol>
        )}
        {reply && (
          <>
            <ol className="steps">
              {reply.steps.map((s, i) => <li key={i} className="done"><Check size={14} aria-hidden /> {s.label} <span className="muted small">{s.summary} · {s.latency_s}s</span></li>)}
            </ol>
            <div className="answer"><Md text={reply.answer} /></div>
          </>
        )}
        {err && asked && <p className="fu-msg bad"><X size={14} aria-hidden /> {err}</p>}
        {asked && !busy && <button className="link-btn" onClick={() => { setAsked(undefined); setReply(null) }}>← Ask another question</button>}

        <div className="sor-status" aria-label="Decision vs. official status">
          <span><span className="muted">Control Tower decision:</span> <strong>{latest ? `${latest.decision} · ${latest.decided_by} · ${new Date(latest.created_at).toLocaleDateString()}` : 'None yet'}</strong></span>
          <span><span className="muted">Official status:</span> <strong>{h.status}</strong> in {system}</span>
        </div>
        <div className="actions">
          {d.kind === 'CO' ? (
            <>
              <button className="btn btn-accent" onClick={() => decide('Negotiate')}>Negotiate / request backup <ArrowRight size={16} aria-hidden /></button>
              <button className="btn btn-ghost" onClick={() => decide('Recommend approval')}><ThumbsUp size={14} aria-hidden /> Recommend approval</button>
              <button className="btn btn-ghost" onClick={() => decide('Reject')}><X size={14} aria-hidden /> Reject with reason</button>
            </>
          ) : (
            <>
              <button className="btn btn-accent" onClick={() => setFuPrefill(`${d.id}: ${h.subject}`)}>Assign follow-up <ArrowRight size={16} aria-hidden /></button>
              <button className="btn btn-ghost" onClick={() => decide('Draft response')}>Log suggested response</button>
            </>
          )}
          <button className="btn btn-ghost" title={`Opens ${system} — the system of record (demo link)`}>Open in {system} <ExternalLink size={14} aria-hidden /></button>
          {reply?.trace_url && <a className="btn btn-ghost" href={reply.trace_url} target="_blank" rel="noreferrer"><GitBranch size={14} aria-hidden /> View MLflow trace</a>}
        </div>
        {d.kind === 'RFI' && <FollowUpPanel projectId={projectId} prefill={fuPrefill} onPrefillUsed={() => setFuPrefill(undefined)} ownerHints={[h.ball_in_court ?? 'Architect', 'Structural engineer (EOR)', 'Project engineer', 'Superintendent']} />}
        <p className="muted small">Recommendations are logged in Lakebase with rationale, owner, and the agent's trace ID. The formal {d.kind === 'CO' ? 'approval' : 'response'} happens in {system}, the system of record.</p>
      </section>
    </div>
  )
}
