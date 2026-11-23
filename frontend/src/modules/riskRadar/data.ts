/**
 * SYNTHETIC demo data for the look-and-feel pass. Stage 1 replaces this with
 * GET /api/risk-radar/* backed by the UC metric view project_risk_mv.
 * Signal values are 0–100 sub-scores (higher = more risk).
 */
export type SignalKey = 'rfi' | 'co' | 'submittal' | 'schedule' | 'cost' | 'safety'

export const SIGNALS: { key: SignalKey; label: string; short: string; source: string }[] = [
  { key: 'rfi', label: 'Open RFIs (aging)', short: 'RFIs', source: 'Procore' },
  { key: 'co', label: 'Change order exposure', short: 'COs', source: 'Clearstory' },
  { key: 'submittal', label: 'Overdue submittals', short: 'Submittals', source: 'Procore' },
  { key: 'schedule', label: 'Schedule variance (float)', short: 'Schedule', source: 'P6' },
  { key: 'cost', label: 'Cost variance (EAC vs budget)', short: 'Cost', source: 'SAP' },
  { key: 'safety', label: 'Safety (14-day)', short: 'Safety', source: 'Procore' },
]

/** Placeholder weights — "how should they be weighted?" is a TBD to vet with the customer. */
export const WEIGHTS: Record<SignalKey, number> = { rfi: 0.15, co: 0.2, submittal: 0.1, schedule: 0.2, cost: 0.25, safety: 0.1 }

export interface Project {
  id: string
  name: string
  sector: string
  region: string
  contractValueM: number
  pctComplete: number
  signals: Record<SignalKey, number>
  trend: number[] // risk score, last 8 weeks (oldest → newest)
  headline: string
  /** Live API only: pending/disputed CO dollars and the metric-view score. */
  pendingCoUsd?: number
  score?: number
}

const p = (
  id: string, name: string, sector: string, region: string, contractValueM: number, pctComplete: number,
  s: [number, number, number, number, number, number], trend: number[], headline: string,
): Project => ({
  id, name, sector, region, contractValueM, pctComplete,
  signals: { rfi: s[0], co: s[1], submittal: s[2], schedule: s[3], cost: s[4], safety: s[5] },
  trend, headline,
})

export const PROJECTS: Project[] = [
  p('P-1001', 'Project Atlas — Data Center Campus, Bldg 3', 'Data Center', 'Northeast', 1240, 46, [88, 84, 62, 71, 66, 58], [48, 52, 55, 61, 64, 70, 74, 78], '14 RFIs > 21 days · $2.1M pending COs'),
  p('P-1002', 'Project Helios — Hyperscale DC Phase 2', 'Data Center', 'Southwest', 980, 31, [55, 78, 48, 82, 60, 40], [40, 44, 47, 52, 58, 63, 66, 69], 'P6 float consumed on switchgear path'),
  p('P-1003', 'Project Vega — AI Data Hall', 'Data Center', 'Midwest', 760, 58, [62, 70, 74, 54, 72, 35], [55, 57, 60, 61, 63, 64, 66, 67], 'Steel EAC +6.2% vs budget'),
  p('P-1004', 'Project Meridian — Regional Medical Center', 'Healthcare', 'Midwest', 540, 64, [40, 72, 38, 46, 81, 30], [42, 45, 49, 53, 57, 60, 62, 64], 'Projected margin 3.4% vs 6.0% bid'),
  p('P-1005', 'Terminal C Modernization', 'Aviation', 'Southeast', 690, 39, [58, 44, 66, 63, 47, 52], [50, 51, 53, 54, 55, 56, 57, 58], 'Overdue MEP submittals'),
  p('P-1006', 'Project Orion — Colocation Facility', 'Data Center', 'West', 410, 72, [46, 52, 41, 58, 49, 62], [61, 59, 58, 57, 55, 54, 53, 52], '2 near-misses at leading edges'),
  p('P-1007', 'University Science Complex', 'Education', 'Northeast', 320, 51, [52, 36, 58, 42, 38, 28], [44, 45, 45, 46, 46, 46, 45, 45], 'RFI turnaround slipping'),
  p('P-1008', 'Harborview Office Tower', 'Commercial', 'Northeast', 610, 83, [30, 48, 22, 38, 52, 24], [50, 48, 46, 45, 44, 42, 41, 40], 'Closeout CO reconciliation'),
  p('P-1009', 'Project Nova — Edge Data Center', 'Data Center', 'Southeast', 220, 22, [34, 30, 46, 40, 28, 44], [30, 32, 33, 35, 36, 37, 37, 38], 'On track'),
  p('P-1010', 'Children’s Hospital Expansion', 'Healthcare', 'West', 470, 44, [38, 34, 32, 36, 41, 26], [38, 37, 37, 36, 36, 35, 35, 35], 'On track'),
  p('P-1011', 'Riverside K-12 Campus', 'Education', 'Southwest', 140, 67, [22, 18, 30, 26, 20, 34], [28, 27, 27, 26, 25, 25, 24, 24], 'On track'),
  p('P-1012', 'Concourse B Expansion', 'Aviation', 'West', 380, 18, [28, 26, 20, 32, 24, 18], [20, 21, 22, 23, 23, 24, 24, 25], 'On track'),
]

export const riskScore = (pr: Project) =>
  Math.round(SIGNALS.reduce((acc, s) => acc + pr.signals[s.key] * WEIGHTS[s.key], 0))

export type Band = 'critical' | 'serious' | 'warning' | 'good'
export const band = (score: number): Band => (score >= 70 ? 'critical' : score >= 55 ? 'serious' : score >= 40 ? 'warning' : 'good')
export const BAND_LABEL: Record<Band, string> = { critical: 'Critical', serious: 'High', warning: 'Watch', good: 'On track' }
