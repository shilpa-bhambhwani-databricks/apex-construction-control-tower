import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowRight, Sparkles, Code2, Loader2, RotateCcw } from 'lucide-react'
import type { Project } from './data'
import { projectSuggestions, scopeSuggestions, shortName, type Suggestion } from './insights'
import { askGenie, genieIsLive, type GenieReply } from '../../api/genie'

/**
 * Genie panel. Every question (chip, typed, or double-click) goes to the live
 * Genie Agent when the backend is connected. Offline, chip questions fall back
 * to answers computed from the local sample data; typed questions need live.
 * Rule for the demo: never ask Genie what the screen already shows.
 */
type Source = 'live' | 'offline' | 'needs-live' | 'error'
interface Turn { id: number; q: string; status: 'loading' | 'done'; source?: Source; body?: ReactNode; sql?: string | null }

export interface AutoAsk { question: string; nonce: number }

export function GeniePanel({ project, sector, region, autoAsk, onAssign }: { project?: Project; sector: string; region: string; autoAsk?: AutoAsk; onAssign?: (note: string) => void }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [conversationId, setConversationId] = useState<string>()
  const [live, setLive] = useState<boolean | null>(null)
  const [draft, setDraft] = useState('')
  const seq = useRef(0)
  const threadEnd = useRef<HTMLDivElement>(null)

  useEffect(() => { genieIsLive().then(setLive) }, [])
  // New project or scope → new conversation.
  useEffect(() => { setTurns([]); setConversationId(undefined) }, [project?.id, sector, region])
  // Scroll only the drawer to the newest answer — never the page behind it.
  useEffect(() => {
    const box = threadEnd.current?.closest<HTMLElement>('.drawer-body')
    if (box && turns.length) box.scrollTo({ top: box.scrollHeight, behavior: 'smooth' })
  }, [turns])

  const pSugg = project ? projectSuggestions(project) : []
  const sSugg = scopeSuggestions(sector)
  const scopeLabel = `${sector === 'All' ? 'All sectors' : sector} · ${region === 'All' ? 'All regions' : region}`

  async function ask(q: string, suggestion?: Suggestion) {
    const id = ++seq.current
    setTurns((t) => [...t, { id, q, status: 'loading' }])
    const finish = (patch: Partial<Turn>) => setTurns((t) => t.map((x) => (x.id === id ? { ...x, status: 'done', ...patch } : x)))
    const isLive = await genieIsLive()
    // Live mode: always Genie. Never fall back to computed answers or show the offline label.
    if (isLive) {
      try {
        // Give Genie the on-screen context so typed questions like "why is it slipping?" resolve to the right project.
        const ctx = project ? `[Context: project ${project.id} ${project.name}; filters: ${scopeLabel}] ` : `[Context: filters: ${scopeLabel}] `
        const r = await askGenie(ctx + q, conversationId)
        setConversationId(r.conversation_id)
        finish({ source: 'live', body: <LiveBody r={r} />, sql: r.sql })
      } catch (e) {
        finish({ source: 'error', body: <p>Genie didn’t answer: {(e as Error).message}</p> })
      }
      return
    }
    const s = suggestion ?? [...pSugg, ...sSugg].find((x) => x.q === q)
    if (s?.offline) finish({ source: 'offline', body: s.offline(), sql: s.sql })
    else finish({ source: 'needs-live', body: <p>This one needs the live Genie Agent — open-ended questions are answered once the backend is connected (Stage 1).</p> })
  }

  // Double-click on a project row/label.
  useEffect(() => {
    if (!autoAsk) return
    const id = setTimeout(() => ask(autoAsk.question), 0) // after the project-change reset above
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoAsk?.nonce])

  const submit = () => { const q = draft.trim(); if (q) { setDraft(''); ask(q) } }

  return (
    <section className="card genie">
      <div className="card-head">
        <h2><Sparkles size={16} aria-hidden /> Ask Genie</h2>
        <span className={`chip ${live ? '' : 'chip-ghost'}`} title={live ? 'Connected to the Portfolio Risk Genie Agent' : 'Backend not connected — chip answers are computed from local sample data'}>
          {live === null ? 'Checking…' : live ? '● Live · Portfolio Risk agent' : 'Offline demo mode'}
        </span>
      </div>

      {turns.length === 0 ? (
        <>
          {project && (
            <>
              <p className="sugg-label">About {shortName(project)}</p>
              <div className="suggestions">
                {pSugg.map((s) => <button key={s.q} className="suggestion" onClick={() => ask(s.q, s)}>{s.q}</button>)}
              </div>
            </>
          )}
          <p className="sugg-label">Across {scopeLabel}</p>
          <div className="suggestions">
            {sSugg.map((s) => <button key={s.q} className="suggestion" onClick={() => ask(s.q, s)}>{s.q}</button>)}
          </div>
        </>
      ) : (
        <div className="thread">
          {turns.map((t) => (
            <div key={t.id}>
              <div className="genie-msg user">{t.q}</div>
              {t.status === 'loading' ? (
                <div className="genie-msg bot muted"><Loader2 size={14} className="spin" aria-hidden /> Genie is analyzing…</div>
              ) : (
                <Answer source={t.source!} sql={t.sql} onAssign={project && onAssign && (t.source === 'live' || t.source === 'offline') ? () => onAssign(`From Genie: ${t.q}`) : undefined}>{t.body}</Answer>
              )}
            </div>
          ))}
          <div ref={threadEnd} />
          {(() => {
            const asked = new Set(turns.map((t) => t.q))
            const next = [...pSugg, ...sSugg].filter((s) => !asked.has(s.q)).slice(0, 3)
            return next.length > 0 && turns.every((t) => t.status === 'done') ? (
              <div className="followups">
                <p className="sugg-label">Follow-up</p>
                {next.map((s) => <button key={s.q} className="suggestion small-sugg" onClick={() => ask(s.q, s)}>{s.q}</button>)}
              </div>
            ) : null
          })()}
          <button className="link-btn" onClick={() => { setTurns([]); setConversationId(undefined) }}><RotateCcw size={12} aria-hidden /> New conversation</button>
        </div>
      )}

      <form className="genie-input" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <input value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Ask Genie"
          placeholder={project ? `Ask anything about ${shortName(project)} or the portfolio…` : 'Ask a question…'} />
        <button className="btn btn-primary" aria-label="Send" type="submit"><ArrowRight size={16} /></button>
      </form>
      <p className="muted small">Tip: double-click any project to ask about it. Same metric view as the list — answers match the screen.</p>
    </section>
  )
}

function Answer({ source, sql, children, onAssign }: { source: Source; sql?: string | null; children: ReactNode; onAssign?: () => void }) {
  const [showSql, setShowSql] = useState(false)
  return (
    <div className={`genie-msg bot ${source === 'error' || source === 'needs-live' ? 'muted' : ''}`}>
      {source === 'offline' && <span className="src-tag">Offline demo · computed from sample data</span>}
      {children}
      {sql && <button className="link-btn" onClick={() => setShowSql((v) => !v)}><Code2 size={14} aria-hidden /> {showSql ? 'Hide SQL' : 'Show SQL'}</button>}
      {showSql && sql && <pre className="sql">{sql}</pre>}
      {onAssign && <button className="link-btn" onClick={onAssign}>→ Assign follow-up from this answer</button>}
    </div>
  )
}

/** Minimal, safe markdown for Genie text: **bold** and "- " bullet lines. No HTML injection (React escapes text). */
function Md({ text }: { text: string }) {
  const inline = (line: string) => line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <span key={i}>{part}</span>)
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => { if (bullets.length) { blocks.push(<ul key={blocks.length} className="bullets">{bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}</ul>); bullets = [] } }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (/^[-*] /.test(line)) { bullets.push(line.slice(2)); continue }
    flush()
    if (line) blocks.push(<p key={blocks.length}>{inline(line)}</p>)
  }
  flush()
  return <>{blocks}</>
}

/** Round long decimals from SQL results for display (e.g. 14.240000000000002 → 14.24). */
const fmtCell = (v: string | null) => {
  if (v == null) return '—'
  if (/^-?\d+\.\d{3,}$/.test(v)) return String(Math.round(Number(v) * 100) / 100)
  return v
}

function LiveBody({ r }: { r: GenieReply }) {
  return (
    <>
      {r.text && <Md text={r.text} />}
      {r.table && r.table.rows.length > 0 && (
        <table className="mini-table">
          <thead><tr>{r.table.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>{r.table.rows.slice(0, 12).map((row, i) => <tr key={i}>{row.map((v, j) => <td key={j}>{fmtCell(v)}</td>)}</tr>)}</tbody>
        </table>
      )}
      {!r.text && !r.table && <p>Genie returned no content.</p>}
    </>
  )
}
