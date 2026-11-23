import type { ReactNode } from 'react'
import { PROJECTS, SIGNALS, WEIGHTS, riskScore, band, BAND_LABEL, type Project, type SignalKey } from './data'
import { Contrib } from '../../components/viz'

/**
 * Status-aware question generator + OFFLINE answers computed from the local
 * sample data. When the backend is connected, the same question text goes to the
 * live Genie Agent instead; these computed answers are only the fallback.
 */
export interface Suggestion {
  q: string
  /** Offline answer computed from local data (or a scripted backup). Absent = live-only question. */
  offline?: () => ReactNode
  /** SQL shown with the offline answer (illustrative of what Genie would run). */
  sql?: string
}

export const shortName = (p: Project) => p.name.split(' — ')[0]
const pts = (p: Project, k: SignalKey) => p.signals[k] * WEIGHTS[k]
const label = (k: SignalKey) => SIGNALS.find((s) => s.key === k)!.label
const source = (k: SignalKey) => SIGNALS.find((s) => s.key === k)!.source
const median = (xs: number[]) => { const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2 }
const portfolioMedian = Object.fromEntries(SIGNALS.map((s) => [s.key, Math.round(median(PROJECTS.map((p) => p.signals[s.key])))])) as Record<SignalKey, number>
const trendDelta = (p: Project) => p.trend[p.trend.length - 1] - p.trend[0]
const BAND_FLOOR = { critical: 70, serious: 55, warning: 40, good: 0 } as const

const mvSql = (p: Project, measure: string) => `SELECT signal, MEASURE(${measure})
FROM bhambs.construction_control_tower.project_risk_mv
WHERE project_id = '${p.id}'
GROUP BY ALL ORDER BY 2 DESC`

/* ---------- computed answers ---------- */

function drivers(p: Project): ReactNode {
  const score = riskScore(p)
  const ranked = SIGNALS.map((s) => [s.key, pts(p, s.key)] as const).sort((a, b) => b[1] - a[1])
  const top = ranked.slice(0, 3)
  const share = Math.round((top.reduce((a, [, v]) => a + v, 0) / score) * 100)
  const d = trendDelta(p)
  return (
    <>
      <p>{shortName(p)} scores <strong>{score}</strong> ({BAND_LABEL[band(score)]}), {d >= 0 ? 'up' : 'down'} {Math.abs(d)} pts over 8 weeks.
        The top 3 signals account for <strong>{share}%</strong> of the score:</p>
      <Contrib rows={ranked.map(([k, v]) => [label(k), Math.round(v)])} max={ranked[0][1]} format={(v) => `${v} pts`} />
      <p>Biggest driver: <strong>{label(top[0][0])}</strong> ({source(top[0][0])}) at {p.signals[top[0][0]]}/100 vs. a portfolio median of {portfolioMedian[top[0][0]]}.</p>
    </>
  )
}

/** Points recovered if each signal came down to the portfolio median. */
function fastestPath(p: Project): ReactNode {
  const score = riskScore(p)
  const gains = SIGNALS.map((s) => [s.key, Math.max(0, (p.signals[s.key] - portfolioMedian[s.key]) * WEIGHTS[s.key])] as const)
    .filter(([, g]) => g > 0.5).sort((a, b) => b[1] - a[1])
  const target = band(score) === 'critical' ? 'serious' : band(score) === 'serious' ? 'warning' : 'good'
  const needed = score - (BAND_FLOOR[target] === 0 ? 39 : BAND_FLOOR[target] - 1)
  let acc = 0
  const plan = gains.filter(([, g]) => { if (acc >= needed) return false; acc += g; return true })
  return (
    <>
      <p>To move {shortName(p)} from {BAND_LABEL[band(score)]} to <strong>{BAND_LABEL[target]}</strong> it needs to drop ~{needed} pts.
        Bringing these signals to the portfolio median gets there:</p>
      <Contrib rows={plan.map(([k, g]) => [label(k), Math.round(g)])} max={plan[0]?.[1] ?? 1} format={(v) => `−${v} pts`} />
      <p className="muted small">Projected score ≈ {Math.round(score - acc)}. Work the first item first — it has the biggest payoff per unit of effort.</p>
    </>
  )
}

function keepingOnTrack(p: Project): ReactNode {
  const strengths = SIGNALS.map((s) => [s.key, portfolioMedian[s.key] - p.signals[s.key]] as const).sort((a, b) => b[1] - a[1]).slice(0, 3)
  const d = trendDelta(p)
  return (
    <>
      <p>{shortName(p)} is <strong>On track</strong> at {riskScore(p)} and {d <= 0 ? `improved ${Math.abs(d)} pts` : `drifted up ${d} pts`} over 8 weeks.
        Where it beats the portfolio median most:</p>
      <Contrib rows={strengths.map(([k, g]) => [label(k), Math.round(g)])} max={strengths[0][1]} format={(v) => `${v} better`} />
      <p>Strongest area: <strong>{label(strengths[0][0])}</strong> ({p.signals[strengths[0][0]]} vs. median {portfolioMedian[strengths[0][0]]}).</p>
    </>
  )
}

function biggestThreat(p: Project): ReactNode {
  const [k] = SIGNALS.map((s) => [s.key, pts(p, s.key)] as const).sort((a, b) => b[1] - a[1])[0]
  const score = riskScore(p)
  const nextFloor = band(score) === 'good' ? 40 : band(score) === 'warning' ? 55 : 70
  const headroom = nextFloor - score
  const signalRise = Math.ceil(headroom / WEIGHTS[k])
  return (
    <>
      <p>The signal most likely to move {shortName(p)} up a band is <strong>{label(k)}</strong> ({source(k)}), currently {p.signals[k]}/100 —
        its highest weighted signal.</p>
      <p>{shortName(p)} has <strong>{headroom} pts</strong> of headroom before {BAND_LABEL[band(nextFloor)]}. That signal alone would need to rise
        ~{signalRise} points to cross it{signalRise > 100 - p.signals[k] ? ' — not possible on its own, so it would take several signals worsening together' : ''}.</p>
      <p className="muted small">Live Genie adds the leading indicators behind it (e.g. upcoming low-float P6 activities, aging items about to cross 21 days).</p>
    </>
  )
}

function lessonsFor(p: Project): ReactNode {
  const peers = PROJECTS.filter((x) => x.id !== p.id && x.sector === p.sector)
  const atRisk = [...(peers.length ? peers : PROJECTS)].sort((a, b) => riskScore(b) - riskScore(a))[0]
  const gaps = SIGNALS.map((s) => [s.key, atRisk.signals[s.key] - p.signals[s.key]] as const).sort((a, b) => b[1] - a[1]).slice(0, 3)
  return (
    <>
      <p>Compared with <strong>{shortName(atRisk)}</strong> ({riskScore(atRisk)}, the highest-risk {peers.length ? p.sector.toLowerCase() : ''} project),
        {' '}{shortName(p)} is ahead most on:</p>
      <Contrib rows={gaps.map(([k, g]) => [label(k), g])} max={gaps[0][1]} format={(v) => `${v} better`} />
      <p>Worth asking {shortName(p)}’s team how they manage <strong>{label(gaps[0][0])}</strong> — that practice is the biggest transferable gap.</p>
    </>
  )
}

/* ---------- scripted backups (Atlas + portfolio), kept for the live-demo safety net ---------- */

const ATLAS_BACKUP: Suggestion[] = [
  {
    q: 'Why did Atlas’s risk score rise over the last 8 weeks?',
    sql: `SELECT week, signal, MEASURE(weighted_contribution) AS pts
FROM bhambs.construction_control_tower.project_risk_mv
WHERE project_id = 'P-1001' AND week >= date_sub(current_date(), 56)
GROUP BY ALL ORDER BY week`,
    offline: () => (
      <>
        <p>Atlas rose from <strong>50 → 73</strong> (+23) since Sept 14. Change in points by signal:</p>
        <Contrib rows={[['RFI aging', 7.5], ['Cost variance', 6.8], ['Schedule float', 5.4], ['Safety', 2.8], ['Submittals', 2.0], ['CO exposure', -1.1]]} max={7.5} format={(v) => `${v > 0 ? '+' : ''}${v}`} />
        <p>Main drivers: open RFIs older than 21 days went from <strong>6 to 14</strong>, EAC overrun rose from <strong>4.2% to 6.9%</strong> (SAP),
          and critical-path float fell from <strong>9.3 to 4.8 days</strong> (P6). CO exposure stayed roughly flat at ~$2.1M as CO-0142 and CO-0139 replaced older items.</p>
      </>
    ),
  },
  {
    q: 'Which open RFIs on Atlas block critical-path work in the next 2 weeks?',
    sql: `SELECT r.rfi_id, r.subject, s.activity_name, s.planned_start, s.total_float_days
FROM bhambs.construction_control_tower.rfis r
JOIN bhambs.construction_control_tower.schedule_activities s ON r.activity_id = s.activity_id
WHERE r.project_id = 'P-1001' AND r.status = 'Open'
  AND s.critical_flag AND s.planned_start <= date_add(current_date(), 14)`,
    offline: () => (
      <table className="mini-table">
        <thead><tr><th>RFI</th><th>Blocks</th><th>Starts</th><th>Float</th></tr></thead>
        <tbody>
          <tr><td>RFI-0387 Embed plate conflict</td><td>L2 steel erection</td><td>Nov 16</td><td>0 d</td></tr>
          <tr><td>RFI-0391 Duct bank vs. F-12</td><td>Trenching, north yard</td><td>Nov 11</td><td>2 d</td></tr>
          <tr><td>RFI-0352 Rock at pile caps</td><td>Pile caps PC-14–22</td><td>Nov 13</td><td>4 d</td></tr>
        </tbody>
      </table>
    ),
  },
]

export function scopeSuggestions(sector: string): Suggestion[] {
  return [
    {
      q: `Which subcontractors account for the most pending CO dollars${sector === 'All' ? '' : ` on ${sector.toLowerCase()} jobs`}?`,
      sql: `SELECT subcontractor, SUM(amount_requested) AS pending_usd, COUNT(*) AS cos
FROM bhambs.construction_control_tower.change_orders c
JOIN bhambs.construction_control_tower.projects p USING (project_id)
WHERE c.status IN ('Pending','Disputed')${sector !== 'All' ? `\n  AND p.market_sector = '${sector}'` : ''}
GROUP BY subcontractor ORDER BY pending_usd DESC LIMIT 5`,
      offline: () => (
        <>
          <Contrib rows={[['Keystone Concrete', 1.12], ['Ironline Steel', 0.94], ['Brightway Electric', 0.61], ['Northgate Mechanical', 0.48], ['All others', 0.5]]} max={1.12} format={(v) => `$${v}M`} />
          <p>Keystone’s exposure is concentrated on <strong>Atlas and Vega</strong> — both foundation/subsurface claims.</p>
          <p className="muted small">Scripted backup — subcontractor detail isn’t in the local sample data.</p>
        </>
      ),
    },
    {
      q: 'Which projects have rising cost variance but little change order exposure?',
      sql: `SELECT name, MEASURE(cost_variance_trend_8w) AS cost_trend, MEASURE(pending_co_usd) AS pending_co
FROM bhambs.construction_control_tower.project_risk_mv
GROUP BY ALL HAVING cost_trend > 0 AND pending_co < 250000`,
      offline: () => (
        <p><strong>Meridian</strong> and <strong>Harborview</strong>: cost variance up 8 weeks running with under $250K pending COs — a classic sign of work
          performed but not captured as change orders (scope leakage). <span className="muted small">Scripted backup.</span></p>
      ),
    },
  ]
}

/** Band-aware questions for a project. The first one is what double-click asks. */
export function projectSuggestions(p: Project): Suggestion[] {
  const n = shortName(p)
  const b = band(riskScore(p))
  let qs: Suggestion[]
  if (b === 'good') {
    qs = [
      { q: `What’s keeping ${n} on track?`, offline: () => keepingOnTrack(p), sql: mvSql(p, 'signal_vs_portfolio_median') },
      { q: `What’s the biggest risk that could knock ${n} off track?`, offline: () => biggestThreat(p), sql: mvSql(p, 'weighted_contribution') },
      { q: `What can at-risk ${p.sector.toLowerCase()} projects learn from ${n}?`, offline: () => lessonsFor(p), sql: mvSql(p, 'signal_gap_vs_peer') },
    ]
  } else if (b === 'warning') {
    qs = [
      { q: `What’s driving ${n}’s risk score?`, offline: () => drivers(p), sql: mvSql(p, 'weighted_contribution') },
      { q: `What could push ${n} into High risk next?`, offline: () => biggestThreat(p), sql: mvSql(p, 'weighted_contribution') },
      { q: `What’s the fastest way to get ${n} back on track?`, offline: () => fastestPath(p), sql: mvSql(p, 'gap_to_portfolio_median') },
    ]
  } else {
    qs = [
      { q: `What’s driving ${n}’s risk score?`, offline: () => drivers(p), sql: mvSql(p, 'weighted_contribution') },
      { q: `What would bring ${n} back to Watch fastest?`, offline: () => fastestPath(p), sql: mvSql(p, 'gap_to_portfolio_median') },
      { q: `Which open items on ${n} block critical-path work in the next 2 weeks?` },
    ]
  }
  return p.id === 'P-1001' ? [qs[0], ...ATLAS_BACKUP, qs[1]] : qs
}
