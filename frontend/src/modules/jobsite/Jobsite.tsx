import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  ArrowRight, Smartphone, Camera, X, FileText, CloudSun, Truck, ClipboardCheck, AlertTriangle, CheckCircle2, XCircle, ShieldAlert, Sparkles, Users, Loader2, GitBranch,
} from 'lucide-react'
import { useBrand } from '../../theme/BrandProvider'
import { useProjects } from '../../data/ProjectsProvider'
import { apiHeaders } from '../../api/genie'
import { Md } from '../../components/Markdown'
import { STATUS } from '../../components/viz'
import { jobsiteDay, type JobsiteDay, type Activity } from './data'

/**
 * Jobsite Intelligence — built for the superintendent's question:
 * "Can this crew do this work, in this location, when promised — and if not, who fixes what?"
 * Big-screen layout for the EBC, with a "View on mobile" preview of the same content.
 * Stage 3 preview: data is synthetic and generated per project (see ./data.ts).
 */
interface Photo { url: string; name: string; file?: File }
interface Turn { id: number; q: string; photos: Photo[]; body: ReactNode; source: 'live' | 'offline' | 'loading' | 'error' }
interface Suggestion { q: string; a: () => ReactNode }

const shortName = (n: string) => n.split(' — ')[0]
const WHEN_ORDER = ['Today', 'Tomorrow', 'Thu', 'Next Mon']
const rank = (a: Activity) => ({ critical: 0, serious: 1, warning: 2 }[a.level] * 10 + WHEN_ORDER.indexOf(a.when))

export function Jobsite({ initialProjectId }: { initialProjectId?: string }) {
  const brand = useBrand()
  const label = brand.moduleLabels?.jobsite ?? 'Jobsite Intelligence'
  const co = brand.shortName ?? brand.customerName
  const { projects: PROJECTS, live } = useProjects()
  const [projectId, setProjectId] = useState(initialProjectId ?? 'P-1001')
  const project = PROJECTS.find((p) => p.id === projectId) ?? PROJECTS[0]
  const [mobile, setMobile] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const [liveDay, setLiveDay] = useState<Omit<JobsiteDay, 'project'> | null>(null)
  const [liveFailed, setLiveFailed] = useState(false)
  useEffect(() => {
    if (!live || !project) return
    setLiveDay(null)
    fetch(`/api/jobsite/day?project_id=${project.id}`, { headers: apiHeaders() })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then(setLiveDay).catch(() => setLiveFailed(true))
  }, [live, project?.id])
  const useLive = live && !liveFailed
  const maybeDay = useMemo(() => (!project ? null : useLive ? (liveDay ? { ...liveDay, project } as JobsiteDay : null) : jobsiteDay(project)), [project, useLive, liveDay])
  useEffect(() => setTurns([]), [projectId])
  if (!maybeDay) return <div className="page"><p className="muted">Loading live project data from Unity Catalog…</p></div>
  const day = maybeDay

  const blocked = day.activities.filter((a) => a.checks.some((c) => !c.ok))
  const short = day.crews.filter((c) => c.yesterday < c.planned)
  const highRisk = day.activities.filter((a) => a.level !== 'warning')
  const topRisk = [...day.activities].sort((a, b) => rank(a) - rank(b))[0]
  const suggestions: Suggestion[] = [
    { q: `What do ${co} EHS standards and OSHA require for ${shortName(topRisk.name).toLowerCase()}?`, a: () => standardsAnswer(day, topRisk, co) },
    { q: `Draft a 5-minute toolbox talk for ${topRisk.when === 'Today' ? 'today' : topRisk.when}’s ${shortName(topRisk.name).toLowerCase()}`, a: () => toolboxTalk(day, topRisk) },
    { q: 'What’s not ready to start in the next 2 weeks — and who owns it?', a: () => notReady(blocked) },
    { q: 'Which trades were short-staffed yesterday vs. plan?', a: () => staffing(short) },
    { q: 'Draft today’s daily log', a: () => dailyLog(day) },
  ]
  const ask = (q: string, body: ReactNode, photos: Photo[] = []) => {
    const id = Date.now()
    if (!useLive) { setTurns((t) => [...t, { id, q, photos, body, source: 'offline' }]); return }
    setTurns((t) => [...t, { id, q, photos, body: <p className="muted"><Loader2 size={14} className="spin" aria-hidden /> Jobsite agent is checking the lookahead, crews, near-misses and standards…</p>, source: 'loading' }])
    const finish = (b: ReactNode, source: Turn['source']) => setTurns((t) => t.map((x) => (x.id === id ? { ...x, body: b, source } : x)))
    ;(async () => {
      try {
        const photo = photos[0]?.file ? await toJpegDataUrl(photos[0].file) : undefined
        const r = await fetch('/api/jobsite/ask', { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ project_id: day.project.id, question: q, photo_data_url: photo }) })
        if (!r.ok) { let m = await r.text(); try { m = JSON.parse(m).detail ?? m } catch { /* plain */ } throw new Error(m) }
        const j = await r.json()
        finish(<>
          <details className="steps-wrap">
            <summary><CheckCircle2 size={13} aria-hidden /> {j.steps.length} steps · {j.steps.reduce((a: number, st: { latency_s: number }) => a + st.latency_s, 0).toFixed(1)}s tools — lookahead, crews, near-misses, EHS/OSHA (click to expand)</summary>
            <ol className="steps">{j.steps.map((st: { label: string; summary: string; latency_s: number }, i: number) => <li key={i} className="done"><CheckCircle2 size={14} aria-hidden /> {st.label} <span className="muted small">{st.summary} · {st.latency_s}s</span></li>)}</ol>
          </details>
          <Md text={j.answer} />
          <div className="actions">{j.trace_url && <a className="btn btn-ghost" href={j.trace_url} target="_blank" rel="noreferrer"><GitBranch size={14} aria-hidden /> View MLflow trace</a>}
            {j.photo_path && <span className="muted small">Photo saved to {j.photo_path.replace('/Volumes/bhambs/construction_control_tower/', '')}</span>}</div>
        </>, 'live')
      } catch (e) { finish(<p>Jobsite agent didn’t answer: {(e as Error).message}</p>, 'error') }
    })()
  }

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow">{label} · {shortName(day.project.name)}</p>
        <div className="head-actions">
          <label className="select">
            Project
            <select value={project.id} onChange={(e) => setProjectId(e.target.value)}>
              {PROJECTS.map((p) => <option key={p.id} value={p.id}>{shortName(p.name)} · {p.sector}</option>)}
            </select>
          </label>
          <button className="btn btn-ghost" onClick={() => setMobile(true)}><Smartphone size={14} aria-hidden /> View on mobile</button>
          <span className="chip chip-stage">Stage 3 preview</span>
        </div>
      </header>

      <section className="kpis" aria-label="Superintendent summary">
        <div className="kpi"><span className="kpi-label">Superintendent</span><span className="kpi-value kpi-sm">{day.superintendent}</span><span className="muted small"><CloudSun size={12} aria-hidden /> {day.weather}</span></div>
        <div className={`kpi ${highRisk.length ? 'kpi-emph' : ''}`}><span className="kpi-label">High-risk work this week</span><span className="kpi-value">{highRisk.length}</span><span className="muted small">Permits + standards attached</span></div>
        <div className={`kpi ${blocked.length ? 'kpi-emph' : ''}`}><span className="kpi-label">Not ready to start</span><span className="kpi-value">{blocked.length} <span className="kpi-of">of {day.activities.length}</span></span><span className="muted small">2-week lookahead</span></div>
        <div className="kpi"><span className="kpi-label">Near-misses · 14 days</span><span className="kpi-value">{day.nearMisses.count}</span><span className="muted small">{day.nearMisses.theme}</span></div>
      </section>

      <nav className="section-nav" aria-label="Sections">
        {([['js-ready', `Ready?${blocked.length ? ` (${blocked.length})` : ''}`], ['js-ask', 'Ask'], ['js-safety', 'Safety'], ['js-crews', 'Crews'], ['js-events', 'Deliveries & inspections']] as const).map(([id, t]) => (
          <button key={id} className="chip chip-ghost" onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>{t}</button>
        ))}
        <span className="muted small">Phase: {day.phase} · {day.project.pctComplete}% complete</span>
      </nav>

      <div className="grid-main">
        <section className="card" id="js-ready">
          <div className="card-head">
            <h2>Ready? — can the work start (2-week lookahead)</h2>
            <span className="muted">Checked automatically against P6, Procore RFIs & submittals, and deliveries</span>
          </div>
          <ReadyTable day={day} />
        </section>
        <aside className="side">
          <section className="card genie" id="js-ask">
            <div className="card-head"><h2><Sparkles size={16} aria-hidden /> Ask</h2></div>
            <p className="muted small ask-sub">{co} EHS standards and OSHA 1926 — answered for this project, this week.</p>
            <Ask day={day} turns={turns} suggestions={suggestions} onAsk={ask} />
          </section>
        </aside>
      </div>

      <div className="grid-3">
        <section className="card" id="js-safety">
          <div className="card-head"><h2><AlertTriangle size={16} aria-hidden /> Safety — this week</h2></div>
          <SafetyList day={day} />
        </section>
        <section className="card" id="js-crews">
          <div className="card-head"><h2><Users size={16} aria-hidden /> Crews — yesterday vs. plan</h2></div>
          <Crews day={day} />
        </section>
        <section className="card" id="js-events">
          <div className="card-head"><h2><Truck size={16} aria-hidden /> Deliveries & inspections today</h2></div>
          <Events day={day} />
        </section>
      </div>

      {mobile && (
        <div className="mobile-overlay" role="dialog" aria-label="Mobile preview" onClick={() => setMobile(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <button className="overlay-close" onClick={() => setMobile(false)} aria-label="Close mobile preview"><X size={18} /></button>
            <Phone day={day} turns={turns} suggestions={suggestions} onAsk={ask} blockedCount={blocked.length} />
            <p className="overlay-note">Same app, same data — responsive on any phone or tablet. No separate mobile build.</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------------- big-screen sections ---------------- */

function ReadyTable({ day }: { day: JobsiteDay }) {
  const labels = ['Info', 'Approvals', 'Materials', 'Float'] as const
  return (
    <table className="table ready-table">
      <thead><tr><th>Activity</th><th>When</th>{labels.map((l) => <th key={l} className="c">{l}</th>)}<th>What’s blocking it · owner · needed by</th></tr></thead>
      <tbody>
        {day.activities.map((a) => {
          const fails = a.checks.filter((c) => !c.ok)
          return (
            <tr key={a.id} className={fails.length ? 'row-bad' : ''}>
              <td>
                <div className="ready-head">
                  {fails.length ? <XCircle size={16} color={STATUS.critical} aria-label="Not ready" /> : <CheckCircle2 size={16} color={STATUS.good} aria-label="Ready" />}
                  <strong>{a.name}</strong>
                </div>
                <div className="muted small">{a.trade} · {a.area}</div>
              </td>
              <td><span className="when">{a.when}</span></td>
              {labels.map((l) => {
                const c = a.checks.find((x) => x.label === l)!
                return <td key={l} className="c" title={c.detail}><span className={`check ${c.ok ? 'ok' : 'bad'}`}>{c.ok ? '✓' : '✗'}</span></td>
              })}
              <td className="small">
                {fails.length === 0 ? <span className="muted">Clear to start</span> : fails.map((c) => (
                  <div key={c.label}>{c.detail}{c.owner ? <> · <strong>{c.owner}</strong></> : ''}{c.neededBy ? ` · by ${c.neededBy}` : ''}</div>
                ))}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function SafetyList({ day }: { day: JobsiteDay }) {
  return (
    <ul className="brief">
      {day.activities.filter((a) => a.when !== 'Next Mon').map((a) => (
        <li key={a.id} className={`brief-${a.level}`}>
          <AlertTriangle size={18} aria-hidden color={STATUS[a.level]} />
          <div>
            <strong>{a.name}</strong> <span className="when">{a.when}</span>
            <div className="muted small">{a.hazard}</div>
            {a.permit && <div className="small permit">Permit: {a.permit}</div>}
            <a className="cite"><FileText size={12} aria-hidden /> {a.standard}</a>
          </div>
        </li>
      ))}
      {day.nearMisses.count > 0 && (
        <li className="brief-serious">
          <ShieldAlert size={18} aria-hidden color={STATUS.serious} />
          <div><strong>{day.nearMisses.count} near-miss{day.nearMisses.count > 1 ? 'es' : ''} in 14 days</strong><div className="muted small">{day.nearMisses.theme} · safety observations</div></div>
        </li>
      )}
    </ul>
  )
}

function Crews({ day }: { day: JobsiteDay }) {
  const max = Math.max(...day.crews.map((c) => c.planned))
  return (
    <>
      <ul className="crews">
        {day.crews.map((c) => {
          const gap = c.planned - c.yesterday
          return (
            <li key={c.trade}>
              <div className="crew-head"><strong>{c.trade}</strong> <span className="muted small">{c.company}</span></div>
              <div className="crew-bar" aria-label={`${c.yesterday} of ${c.planned} planned`}>
                <span className="crew-planned" style={{ width: `${(c.planned / max) * 100}%` }} />
                <span className="crew-actual" style={{ width: `${(c.yesterday / max) * 100}%`, background: gap > 0 ? STATUS.serious : 'var(--primary)' }} />
              </div>
              <div className="small">{c.yesterday} of {c.planned} planned{gap > 0 ? <strong className="short"> · short {gap}</strong> : ' · on plan'}</div>
            </li>
          )
        })}
      </ul>
      <p className="muted small">Procore daily log manpower vs. P6 resource plan.</p>
    </>
  )
}

function Events({ day }: { day: JobsiteDay }) {
  return (
    <ul className="events">
      {day.events.map((e) => (
        <li key={e.what}>{e.kind === 'delivery' ? <Truck size={14} aria-hidden /> : <ClipboardCheck size={14} aria-hidden />} <span><strong>{e.time}</strong> {e.what}</span></li>
      ))}
    </ul>
  )
}

/* ---------------- shared Ask panel (big screen + phone) ---------------- */

function Ask({ day, turns, suggestions, onAsk }: { day: JobsiteDay; turns: Turn[]; suggestions: Suggestion[]; onAsk: (q: string, body: ReactNode, photos?: Photo[]) => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [photos, setPhotos] = useState<Photo[]>([])
  const [note, setNote] = useState('')
  const asked = new Set(turns.map((t) => t.q))
  const onFiles = (files: FileList | null) => {
    if (!files) return
    const next = [...files].filter((f) => f.type.startsWith('image/')).slice(0, 4).map((f) => ({ url: URL.createObjectURL(f), name: f.name, file: f }))
    setPhotos((p) => [...p, ...next].slice(0, 4))
  }
  const send = () => {
    const q = note.trim()
    if (!photos.length && !q) return
    const match = suggestions.find((s) => s.q === q)
    const body = photos.length
      ? <p>Photo received. Hazard check runs on a vision model with {shortName(day.project.name)}’s activities and recent observations as context — connected in Stage 3. The photo is stored in a Unity Catalog volume with the project record.</p>
      : match ? match.a() : <p>Open-ended questions are answered by the live Jobsite agent once it’s connected (Stage 3).</p>
    onAsk(q || 'Is there anything unsafe in this photo?', body, photos)
    setPhotos([]); setNote('')
  }
  return (
    <div>
      <div className="thread">
        {turns.map((t, i) => (
          <div key={i} className="photo-turn">
            <div className="genie-msg user">
              {t.photos.length > 0 && <div className="thumbs">{t.photos.map((p) => <img key={p.url} src={p.url} alt={p.name} />)}</div>}
              {t.q}
            </div>
            <div className="genie-msg bot">{t.source === 'offline' && <span className="src-tag">Offline demo · computed from sample data</span>}{t.body}</div>
          </div>
        ))}
      </div>
      <p className="sugg-label">{turns.length ? 'Follow-up' : `Ask about ${shortName(day.project.name)}`}</p>
      <div className="suggestions">
        {suggestions.filter((s) => !asked.has(s.q)).map((s) => <button key={s.q} className="suggestion small-sugg" onClick={() => onAsk(s.q, s.a())}>{s.q}</button>)}
      </div>
      {photos.length > 0 && (
        <div className="thumbs pending" aria-label="Photos to send">
          {photos.map((p) => (
            <span key={p.url} className="thumb">
              <img src={p.url} alt={p.name} />
              <button aria-label={`Remove ${p.name}`} onClick={() => setPhotos((ps) => ps.filter((x) => x.url !== p.url))}><X size={12} /></button>
            </span>
          ))}
        </div>
      )}
      <form className="genie-input phone-input" onSubmit={(e) => { e.preventDefault(); send() }}>
        <button type="button" className="btn btn-ghost icon-btn" aria-label="Add photo" title="Take or upload a photo" onClick={() => fileRef.current?.click()}><Camera size={16} /></button>
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ask, or add a jobsite photo…" aria-label="Ask about the jobsite" />
        <button className="btn btn-primary" type="submit" aria-label="Send"><ArrowRight size={16} /></button>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg" capture="environment" multiple hidden onChange={(e) => { onFiles(e.target.files); e.target.value = '' }} />
      </form>
    </div>
  )
}

/* ---------------- mobile preview ---------------- */

type PhoneView = 'today' | 'ready' | 'crews' | 'ask'
function Phone({ day, turns, suggestions, onAsk, blockedCount }: { day: JobsiteDay; turns: Turn[]; suggestions: Suggestion[]; onAsk: (q: string, body: ReactNode, photos?: Photo[]) => void; blockedCount: number }) {
  const [view, setView] = useState<PhoneView>('ready')
  return (
    <div className="phone phone-device" aria-label="Superintendent phone view">
      <div className="phone-bar"><Smartphone size={14} aria-hidden /> {day.superintendent} · {shortName(day.project.name)}</div>
      <div className="phone-tabs" role="tablist">
        {(['ready', 'today', 'crews', 'ask'] as PhoneView[]).map((v) => (
          <button key={v} role="tab" aria-selected={view === v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>
            {{ ready: `Ready?${blockedCount ? ` (${blockedCount})` : ''}`, today: 'Safety', crews: 'Crews', ask: 'Ask' }[v]}
          </button>
        ))}
      </div>
      <div className="phone-view">
        {view === 'ready' && <ReadyCompact day={day} />}
        {view === 'today' && <><div className="today-strip"><span><CloudSun size={14} aria-hidden /> {day.weather}</span></div><SafetyList day={day} /><Events day={day} /></>}
        {view === 'crews' && <Crews day={day} />}
        {view === 'ask' && <Ask day={day} turns={turns} suggestions={suggestions} onAsk={onAsk} />}
      </div>
    </div>
  )
}

function ReadyCompact({ day }: { day: JobsiteDay }) {
  return (
    <ul className="ready">
      {day.activities.map((a) => {
        const fails = a.checks.filter((c) => !c.ok)
        return (
          <li key={a.id} className={fails.length ? 'not-ready' : ''}>
            <div className="ready-head">
              {fails.length ? <XCircle size={16} color={STATUS.critical} aria-label="Not ready" /> : <CheckCircle2 size={16} color={STATUS.good} aria-label="Ready" />}
              <strong>{a.name}</strong> <span className="when">{a.when}</span>
            </div>
            <div className="checks">{a.checks.map((c) => <span key={c.label} className={`check ${c.ok ? 'ok' : 'bad'}`}>{c.ok ? '✓' : '✗'} {c.label}</span>)}</div>
            {fails.map((c) => <div key={c.label} className="small fail-line">{c.detail}{c.owner ? ` · ${c.owner}` : ''}{c.neededBy ? ` · by ${c.neededBy}` : ''}</div>)}
          </li>
        )
      })}
    </ul>
  )
}

/* ---------------- computed answers (offline) ---------------- */

/** Standards question (what a standards-only safety assistant answers) + the project context on top. */
function standardsAnswer(day: JobsiteDay, a: Activity, co: string): ReactNode {
  const related = day.activities.filter((x) => x.id !== a.id && x.standard.split(' · ')[0] === a.standard.split(' · ')[0])
  return (
    <>
      <p><strong>Standard:</strong> <a className="cite"><FileText size={12} aria-hidden /> {a.standard}</a> — the live agent quotes the exact requirements from {co}’s EHS manual and OSHA, with section citations.</p>
      <p><strong>On {shortName(day.project.name)} this week:</strong></p>
      <ul className="bullets">
        <li>{a.name} — <strong>{a.when}</strong>, {a.area}, {a.trade.toLowerCase()} crew{a.permit ? `; needs ${a.permit.toLowerCase()}` : ''}.</li>
        {related.map((r) => <li key={r.id}>Also applies to {r.name.toLowerCase()} ({r.when}).</li>)}
        {day.nearMisses.count > 0 && <li>Job-wide: {day.nearMisses.count} near-miss{day.nearMisses.count > 1 ? 'es' : ''} in 14 days ({day.nearMisses.theme}).</li>}
        <li>Conditions today: {day.weather}.</li>
      </ul>
      <p className="muted small">Requirement text comes from the governed standards library ({co} EHS + OSHA 1926 in a Unity Catalog volume) once connected.</p>
    </>
  )
}

function toolboxTalk(day: JobsiteDay, a: Activity): ReactNode {
  return (
    <>
      <p><strong>Toolbox talk — {a.name}</strong> ({a.when}, {a.area})</p>
      <ol className="talk">
        <li><strong>The hazard:</strong> {a.hazard.toLowerCase()} — {a.trade.toLowerCase()} crew in {a.area}.</li>
        {a.permit && <li><strong>Before we start:</strong> {a.permit} reviewed and signed; competent person named.</li>}
        <li><strong>Why it matters here:</strong> {day.nearMisses.count > 0 ? `${day.nearMisses.count} near-miss${day.nearMisses.count > 1 ? 'es' : ''} on this job in 14 days (${day.nearMisses.theme}).` : 'no recent near-misses — keep it that way.'}</li>
        <li><strong>Conditions today:</strong> {day.weather}{/wind|gust/.test(day.weather) ? ' — confirm wind limits for lifts and wall bracing.' : '.'}</li>
        <li><strong>New workers:</strong> pair first-year crew with a lead; walk the work area before starting.</li>
        <li><strong>Stop-work:</strong> anyone can stop the job if conditions change.</li>
      </ol>
      <a className="cite"><FileText size={12} aria-hidden /> {a.standard}</a>
      <p className="muted small">Draft for the superintendent to review before the huddle.</p>
    </>
  )
}

function notReady(blocked: Activity[]): ReactNode {
  if (!blocked.length) return <p>Everything in the 2-week lookahead is clear to start: info, approvals, materials and float all check out.</p>
  return (
    <table className="mini-table">
      <thead><tr><th>Activity</th><th>Blocker</th><th>Owner</th><th>By</th></tr></thead>
      <tbody>
        {blocked.flatMap((a) => a.checks.filter((c) => !c.ok).map((c) => (
          <tr key={a.id + c.label}><td>{shortName(a.name)} <span className="muted">({a.when})</span></td><td>{c.detail}</td><td>{c.owner ?? '—'}</td><td>{c.neededBy ?? '—'}</td></tr>
        )))}
      </tbody>
    </table>
  )
}

function staffing(short: JobsiteDay['crews']): ReactNode {
  if (!short.length) return <p>All trades were on plan yesterday.</p>
  return (
    <>
      <ul className="bullets">{short.map((c) => <li key={c.trade}><strong>{c.trade}</strong> ({c.company}): {c.yesterday} of {c.planned} — short {c.planned - c.yesterday}</li>)}</ul>
      <p className="muted small">Raise at tomorrow’s foreman meeting; check against this week’s lookahead commitments.</p>
    </>
  )
}

function dailyLog(day: JobsiteDay): ReactNode {
  const total = day.crews.reduce((a, c) => a + c.yesterday, 0)
  return (
    <>
      <p><strong>Daily log draft — {shortName(day.project.name)}</strong></p>
      <ul className="bullets">
        <li><strong>Weather:</strong> {day.weather}</li>
        <li><strong>Manpower:</strong> {total} workers — {day.crews.map((c) => `${c.trade} ${c.yesterday}`).join(', ')}</li>
        <li><strong>Work:</strong> {day.activities.filter((a) => a.when === 'Today').map((a) => a.name).join('; ') || 'per lookahead'}</li>
        <li><strong>Deliveries / inspections:</strong> {day.events.map((e) => `${e.time} ${e.what}`).join('; ')}</li>
        <li><strong>Safety:</strong> {day.nearMisses.count} near-miss(es) in 14 days ({day.nearMisses.theme}); no incidents today — <em>confirm</em></li>
      </ul>
      <p className="muted small">Draft built from today’s records — super reviews and submits in Procore. Nothing is auto-filed.</p>
    </>
  )
}

/** Downscale a photo to ≤1600 px JPEG (keeps uploads small for the vision model and the volume). */
function toJpegDataUrl(file: File, max = 1600): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height))
      const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k)
      c.getContext('2d')!.drawImage(img, 0, 0, c.width, c.height)
      resolve(c.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = reject
    img.src = URL.createObjectURL(file)
  })
}
