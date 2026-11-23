import { useState } from 'react'
import { useBrand } from '../../theme/BrandProvider'
import {
  ArrowRight, FileText, Search, Calculator, ScrollText, Check, GitBranch, ExternalLink, ThumbsUp, X, Sparkles, Paperclip, Link2,
} from 'lucide-react'

/** Stage 2 preview — layout + copy from the EBC storyboard. All data is synthetic. */
type Kind = 'CO' | 'RFI'
interface Item {
  id: string
  kind: Kind
  title: string
  meta: string
  status: string
  system: 'Clearstory' | 'Procore'
  fields: [string, string][]
  description: string
  attachments: string[]
  linked: string[]
  /** Cross-system context the source system alone doesn't show. */
  context: { label: string; value: string; source: string }[]
  questions: string[]
  answer?: 'co-0142' | 'rfi-0387'
}

const ITEMS: Item[] = [
  {
    id: 'CO-0142', kind: 'CO', title: 'Additional foundation work — subsurface rock', meta: 'Concrete sub · 03-3000 · $486K', status: 'Pending', system: 'Clearstory',
    fields: [['Requested', '$486,000'], ['Subcontractor', 'Keystone Concrete LLC'], ['Cost code', '03-3000 Cast-in-place concrete'], ['Submitted', 'Oct 28, 2026'],
      ['Ball in court', 'GC PM — J. Ellis'], ['Days pending', '12'], ['Reason', 'Differing site conditions'], ['COR #', 'COR-2291']],
    description: 'Unforeseen subsurface rock encountered at grid lines C–F during excavation for pile caps PC-14 through PC-22. Sub requests additional rock removal, over-excavation, and lean concrete backfill.',
    attachments: ['COR-2291 pricing backup.pdf', 'Daily log 10-11.pdf', 'Geotech memo GM-07.pdf'],
    linked: ['RFI-0352 Rock at pile caps', 'Change event CE-118'],
    context: [
      { label: 'Schedule', value: 'Foundation path has 4 days of float left', source: 'P6' },
      { label: 'Budget', value: '03-3000 EAC already +$380K over budget', source: 'SAP' },
      { label: 'Daily log', value: 'Rock first noted Oct 11 (17 days before COR)', source: 'Procore' },
    ],
    questions: ['Is this change order covered by the prime contract, and is the pricing in line with similar work in this region?', 'What would approving this do to projected margin?'],
    answer: 'co-0142',
  },
  {
    id: 'CO-0139', kind: 'CO', title: 'Revised embed plates, Level 2', meta: 'Steel sub · 05-1200 · $122K', status: 'Pending', system: 'Clearstory',
    fields: [['Requested', '$122,400'], ['Subcontractor', 'Ironline Steel Erectors'], ['Cost code', '05-1200 Structural steel'], ['Submitted', 'Nov 2, 2026'],
      ['Ball in court', 'GC PE — M. Ruiz'], ['Days pending', '7'], ['Reason', 'Design change (ASI-031)'], ['COR #', 'COR-2304']],
    description: 'Fabrication and installation of revised embed plates at L2 beams B-12 through B-19 per ASI-031, which resolved RFI-0387.',
    attachments: ['COR-2304 breakdown.xlsx', 'ASI-031.pdf'],
    linked: ['RFI-0387 Embed plate conflict', 'ASI-031'],
    context: [
      { label: 'Budget', value: '05-1200 tariff surcharges already +$1.4M', source: 'SAP' },
      { label: 'Schedule', value: 'L2 steel on critical path next week', source: 'P6' },
    ],
    questions: ['Is the labor rate consistent with Ironline’s other jobs with us?', 'Is this already covered by the original steel subcontract scope?'],
  },
  {
    id: 'RFI-0387', kind: 'RFI', title: 'Embed plate conflict at L2 beam', meta: 'Structural · 26 days open', status: 'Open', system: 'Procore',
    fields: [['Discipline', 'Structural'], ['Created', 'Oct 14, 2026'], ['Due', 'Oct 24, 2026 (overdue)'], ['Ball in court', 'Architect — HKS'],
      ['Cost impact', 'Yes (TBD)'], ['Schedule impact', 'Yes'], ['Spec section', '05 12 00'], ['Location', 'Level 2, grid B']],
    description: 'Embed plates shown on S-201 conflict with beam pocket locations on S-305 at L2, grid B. Please confirm plate size and location.',
    attachments: ['S-201 markup.pdf', 'Field photo 10-13.jpg'],
    linked: ['CO-0139 Revised embed plates'],
    context: [
      { label: 'Schedule', value: 'Blocks L2 steel erection starting Nov 16', source: 'P6' },
      { label: 'Precedent', value: '3 similar RFIs on past DC projects', source: 'Procore + Prolog' },
    ],
    questions: ['Has a similar RFI come up before, and how was it resolved?', 'What work is blocked if this stays open another week?'],
    answer: 'rfi-0387',
  },
  {
    id: 'RFI-0391', kind: 'RFI', title: 'Duct bank routing vs. footing F-12', meta: 'Electrical · 23 days open', status: 'Open', system: 'Procore',
    fields: [['Discipline', 'Electrical'], ['Created', 'Oct 17, 2026'], ['Due', 'Oct 27, 2026 (overdue)'], ['Ball in court', 'Engineer — MEP'],
      ['Cost impact', 'Possible'], ['Schedule impact', 'Yes'], ['Spec section', '26 05 43'], ['Location', 'Site, north yard']],
    description: 'Duct bank DB-3 routing on E-101 conflicts with footing F-12 on S-101. Request revised routing or depth.',
    attachments: ['E-101 overlay.pdf'],
    linked: [],
    context: [{ label: 'Schedule', value: 'Trenching > 5 ft planned Wed–Fri', source: 'P6' }],
    questions: ['Has a similar RFI come up before, and how was it resolved?'],
  },
  {
    id: 'CO-0131', kind: 'CO', title: 'Temporary power extension', meta: 'Electrical sub · 01-5000 · $64K', status: 'In negotiation', system: 'Clearstory',
    fields: [['Requested', '$64,200'], ['Subcontractor', 'Brightway Electric'], ['Cost code', '01-5000 Temporary facilities'], ['Submitted', 'Oct 9, 2026'],
      ['Ball in court', 'Subcontractor'], ['Days pending', '31'], ['Reason', 'Schedule extension'], ['COR #', 'COR-2240']],
    description: 'Extend temporary power distribution for an additional 6 weeks due to the switchgear delivery delay.',
    attachments: ['COR-2240.pdf'],
    linked: [],
    context: [{ label: 'Decision', value: 'Negotiate — logged Nov 3 by J. Ellis', source: 'Control Tower' }],
    questions: ['Who caused the switchgear delay — is this back-chargeable?'],
  },
]

const pillClass = (s: string) => `pill pill-${s.replace(/\s/g, '').toLowerCase()}`

export function ResolveMock({ projectId }: { projectId?: string }) {
  const label = useBrand().moduleLabels?.resolve ?? 'Resolve'
  const [selectedId, setSelectedId] = useState(ITEMS[0].id)
  const [asked, setAsked] = useState<string | null>(null)
  const item = ITEMS.find((i) => i.id === selectedId)!
  const scripted = !!item.answer && asked === item.questions[0]

  const select = (id: string) => { setSelectedId(id); setAsked(null) }

  return (
    <div className="page">
      <header className="page-head">
        <p className="eyebrow">{label} · {projectId ?? 'P-1001'} · Project Atlas</p>
        <span className="chip chip-stage">Stage 2 preview</span>
      </header>

      <div className="grid-resolve">
        <section className="card">
          <div className="card-head"><h2>Backlog</h2><span className="muted small">Clearstory · Procore (read-only)</span></div>
          <ul className="backlog" role="listbox" aria-label="Backlog items">
            {ITEMS.map((b) => (
              <li key={b.id} role="option" aria-selected={b.id === selectedId} tabIndex={0} className={b.id === selectedId ? 'selected' : ''}
                onClick={() => select(b.id)} onKeyDown={(e) => e.key === 'Enter' && select(b.id)}>
                <div><strong>{b.id}</strong> <span className={pillClass(b.status)}>{b.status}</span></div>
                <div>{b.title}</div>
                <div className="muted small">{b.meta}</div>
              </li>
            ))}
          </ul>
        </section>

        <div className="resolve-main">
          {/* ---- Record details: what the system of record says ---- */}
          <section className="card">
            <div className="card-head">
              <h2>{item.id} · {item.title}</h2>
              <span className={pillClass(item.status)}>{item.status} in {item.system}</span>
            </div>
            <dl className="fields">
              {item.fields.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
            </dl>
            <p className="desc">{item.description}</p>
            <div className="rec-row">
              <div>
                <span className="muted small">Attachments</span>
                <ul className="inline-list">{item.attachments.map((a) => <li key={a}><Paperclip size={12} aria-hidden /> {a}</li>)}</ul>
              </div>
              {item.linked.length > 0 && (
                <div>
                  <span className="muted small">Linked</span>
                  <ul className="inline-list">{item.linked.map((l) => <li key={l}><Link2 size={12} aria-hidden /> {l}</li>)}</ul>
                </div>
              )}
            </div>
            <div className="context">
              <span className="muted small">Context from other systems</span>
              {item.context.map((c) => (
                <div key={c.label} className="context-row"><strong>{c.label}</strong> {c.value} <span className="chip chip-ghost">{c.source}</span></div>
              ))}
            </div>
            <button className="link-btn">Open in {item.system} <ExternalLink size={12} aria-hidden /></button>
          </section>

          {/* ---- Assistant ---- */}
          <section className="card">
            <div className="card-head"><h2><Sparkles size={16} aria-hidden /> Ask about {item.id}</h2><span className="chip">Resolve agent</span></div>
            {!asked && (
              <div className="suggestions">
                {item.questions.map((q) => <button key={q} className="suggestion" onClick={() => setAsked(q)}>{q}</button>)}
              </div>
            )}
            {asked && <div className="genie-msg user">{asked}</div>}
            {scripted && item.answer === 'co-0142' && <AnswerCO0142 />}
            {scripted && item.answer === 'rfi-0387' && <AnswerRFI0387 />}
            {asked && !scripted && (
              <p className="muted small">Live answers arrive in Stage 2. Scripted demo answers exist for CO-0142 and RFI-0387.</p>
            )}

            <div className="sor-status" aria-label="Decision vs. official status">
              <span><span className="muted">Control Tower decision:</span> <strong>{item.id === 'CO-0131' ? 'Negotiate (Nov 3)' : 'None yet'}</strong></span>
              <span><span className="muted">Official status:</span> <strong>{item.status}</strong> in {item.system}</span>
            </div>
            <div className="actions">
              {item.kind === 'CO' ? (
                <>
                  <button className="btn btn-accent">Negotiate / request backup <ArrowRight size={16} aria-hidden /></button>
                  <button className="btn btn-ghost"><ThumbsUp size={14} aria-hidden /> Recommend approval</button>
                  <button className="btn btn-ghost"><X size={14} aria-hidden /> Reject with reason</button>
                </>
              ) : (
                <>
                  <button className="btn btn-accent">Assign follow-up <ArrowRight size={16} aria-hidden /></button>
                  <button className="btn btn-ghost">Draft suggested response</button>
                </>
              )}
              <button className="btn btn-ghost">Open in {item.system} <ExternalLink size={14} aria-hidden /></button>
              <button className="btn btn-ghost"><GitBranch size={14} aria-hidden /> View MLflow trace</button>
            </div>
            <p className="muted small">Recommendations are logged in Lakebase with rationale, owner, and due date. The formal {item.kind === 'CO' ? 'approval' : 'response'} happens in {item.system}, the system of record.</p>
          </section>
        </div>
      </div>
    </div>
  )
}

function AnswerCO0142() {
  return (
    <>
      <ol className="steps">
        <li className="done"><Search size={14} aria-hidden /> Searching contracts &amp; specs <span className="muted small">AI Search · 6 docs</span></li>
        <li className="done"><Calculator size={14} aria-hidden /> get_unit_cost_baseline('03-3000', 'Northeast') <span className="muted small">UC function · SAP history</span></li>
        <li className="done"><ScrollText size={14} aria-hidden /> Checking subcontract notice requirements vs. daily log</li>
      </ol>
      <div className="answer">
        <p><Check size={14} aria-hidden className="ok" /> Covered by the differing-site-conditions clause <a className="cite"><FileText size={12} aria-hidden /> Prime §4.3</a></p>
        <p><span className="flag">Review flag</span> Written notice required within 7 days <a className="cite"><FileText size={12} aria-hidden /> Sub §11.2</a> — first notice is 12 days after the daily-log entry.</p>
        <p><span className="flag">Pricing</span> Unit rate is <strong>18% above</strong> the 24-month Northeast median for 03-3000 (n = 37).</p>
        <div className="band">
          <span className="muted small">P25</span><span className="band-track"><span className="band-iqr" /><span className="band-med" /><span className="band-pt" /></span><span className="muted small">P75</span>
        </div>
      </div>
    </>
  )
}

function AnswerRFI0387() {
  return (
    <div className="answer">
      <p>3 similar past RFIs across past data center projects:</p>
      <p><strong>Orion RFI-0212</strong> — embed/beam pocket conflict; resolved by ASI in 6 days, $38K CO, 0 days delay <a className="cite"><FileText size={12} aria-hidden /> RFI-0212</a></p>
      <p><strong>Nova RFI-0098</strong> — plate size mismatch; field fix approved, no cost <a className="cite"><FileText size={12} aria-hidden /> RFI-0098</a></p>
      <p><strong>Legacy DC-17 (Prolog)</strong> — same detail; 19 days open caused 5-day steel delay <a className="cite"><FileText size={12} aria-hidden /> PL-4471</a></p>
    </div>
  )
}
