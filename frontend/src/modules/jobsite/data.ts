/**
 * SYNTHETIC superintendent data, generated per project from its sector + risk signals.
 * Stage 3 replaces this with: P6 lookahead (schedule_activities), Procore daily logs /
 * manpower / inspections / deliveries, safety_observations, rfis, submittals.
 *
 * Built around the superintendent's core question:
 * "Can this crew do this work, in this location, when promised — and if not, who fixes what?"
 */
import { type Project } from '../riskRadar/data'

export type Level = 'critical' | 'serious' | 'warning'
export interface Activity {
  id: string
  name: string
  trade: string
  area: string
  when: string
  hazard: string
  standard: string
  permit?: string
  level: Level
  checks: { label: 'Info' | 'Approvals' | 'Materials' | 'Inspection' | 'Float'; ok: boolean; detail: string; owner?: string; neededBy?: string }[]
}
export interface Crew { trade: string; company: string; planned: number; yesterday: number }
export interface Event { time: string; what: string; kind: 'delivery' | 'inspection' }
export interface JobsiteDay {
  phase: 'early' | 'mid' | 'late'
  project: Project
  superintendent: string
  weather: string
  nearMisses: { count: number; theme: string }
  activities: Activity[]
  crews: Crew[]
  events: Event[]
}

type Phase = 'early' | 'mid' | 'late'
type Template = Omit<Activity, 'id' | 'when' | 'checks' | 'level'> & { base: Level }
type T = Template
/** {B} = building, {L} = level — filled per project so same-sector jobs don't look identical. */
const TEMPLATES: Record<string, Record<Phase, T[]>> = {
  'Data Center': {
    early: [
      { name: 'Mass excavation & shoring', trade: 'Sitework', area: 'Bldg {B} footprint', hazard: 'Cave-in / equipment struck-by', standard: 'OSHA 1926 Subpart P', permit: 'Competent person daily inspection', base: 'serious' },
      { name: 'Drilled pier installation', trade: 'Foundations', area: 'Bldg {B}, grid A–F', hazard: 'Drill rig struck-by / open holes', standard: 'OSHA 1926 Subpart P', base: 'serious' },
      { name: 'Foundation mat pour', trade: 'Concrete', area: 'Bldg {B}, pour 2', hazard: 'Pump truck boom / formwork', standard: 'OSHA 1926 Subpart Q', base: 'warning' },
    ],
    mid: [
      { name: 'Metal decking at leading edges', trade: 'Steel erection', area: 'Bldg {B}, L{L}', hazard: 'Falls from leading edge', standard: 'OSHA 1926 Subpart R', base: 'serious' },
      { name: 'Trenching > 5 ft — electrical duct bank', trade: 'Sitework', area: 'North yard', hazard: 'Cave-in', standard: 'OSHA 1926 Subpart P', permit: 'Competent person daily inspection', base: 'serious' },
      { name: '220-ton crawler crane pick — roof steel', trade: 'Steel erection', area: 'Bldg {B}, L{L}', hazard: 'Critical lift over active work zone', standard: 'OSHA 1926 Subpart CC', permit: 'Critical lift plan', base: 'critical' },
      { name: 'Overhead MEP rough-in from aerial lifts', trade: 'Mechanical', area: 'Data hall {B}', hazard: 'Aerial lift tip-over / falls', standard: 'OSHA 1926 Subpart L (1926.453)', base: 'serious' },
    ],
    late: [
      { name: 'Switchgear set & energization', trade: 'Electrical', area: 'Electrical room E-{B}', hazard: 'Arc flash / energized work', standard: 'OSHA 1926 Subpart K · NFPA 70E', permit: 'Energized work permit', base: 'critical' },
      { name: 'Generator load-bank testing', trade: 'Electrical', area: 'Generator yard', hazard: 'Energized equipment / noise', standard: 'OSHA 1926 Subpart K', permit: 'Lockout/tagout plan', base: 'serious' },
      { name: 'Integrated systems test (Level 5 Cx)', trade: 'Commissioning', area: 'Data hall {B}', hazard: 'Unexpected energization', standard: 'OSHA 1926 Subpart K (1926.417)', permit: 'Lockout/tagout plan', base: 'critical' },
      { name: 'Hot-aisle containment install', trade: 'Interiors', area: 'Data hall {B}', hazard: 'Ladder falls', standard: 'OSHA 1926 Subpart X', base: 'warning' },
    ],
  },
  Healthcare: {
    early: [
      { name: 'Excavation next to occupied hospital', trade: 'Sitework', area: 'East lot', hazard: 'Cave-in / public protection', standard: 'OSHA 1926 Subpart P · ICRA perimeter', permit: 'Competent person daily inspection', base: 'serious' },
      { name: 'Utility tie-in to live campus services', trade: 'Plumbing', area: 'Central plant', hazard: 'Service interruption to occupied hospital', standard: 'Owner shutdown procedure', permit: 'Owner shutdown approval', base: 'critical' },
      { name: 'Foundation pour', trade: 'Concrete', area: 'Tower {B}', hazard: 'Pump truck boom', standard: 'OSHA 1926 Subpart Q', base: 'warning' },
    ],
    mid: [
      { name: 'Corridor ceiling MEP rough-in (occupied wing)', trade: 'Mechanical', area: 'East wing, L{L}', hazard: 'Dust migration into patient areas', standard: 'ICRA Class IV · OSHA 1926 Subpart X', permit: 'Infection control permit', base: 'critical' },
      { name: 'Firestopping & cutting (hot work)', trade: 'Firestopping', area: 'Shaft S-{B}', hazard: 'Fire in occupied building', standard: 'OSHA 1926 Subpart J', permit: 'Hot work permit', base: 'serious' },
      { name: 'Exterior curtain wall install', trade: 'Glazing', area: 'South elevation', hazard: 'Falls / dropped objects', standard: 'OSHA 1926 Subpart M', base: 'serious' },
      { name: 'Steel erection over main entrance', trade: 'Steel erection', area: 'Entrance canopy', hazard: 'Overhead loads near public', standard: 'OSHA 1926 Subpart CC', permit: 'Lift plan + pedestrian reroute', base: 'critical' },
    ],
    late: [
      { name: 'Medical gas tie-in', trade: 'Plumbing', area: 'OR suite', hazard: 'Service interruption to occupied ORs', standard: 'NFPA 99 · owner shutdown procedure', permit: 'Owner shutdown approval', base: 'critical' },
      { name: 'Emergency power transfer testing', trade: 'Electrical', area: 'Essential electrical system', hazard: 'Loss of life-safety power', standard: 'NFPA 110 · OSHA 1926 Subpart K', permit: 'Owner test window approval', base: 'critical' },
      { name: 'ICRA barrier removal & terminal clean', trade: 'General', area: 'East wing, L{L}', hazard: 'Dust release into patient areas', standard: 'ICRA Class IV', permit: 'Infection control sign-off', base: 'serious' },
    ],
  },
  Aviation: {
    early: [
      { name: 'Utility relocation under apron', trade: 'Sitework', area: 'Apron {B}', hazard: 'Cave-in / airside incursion', standard: 'OSHA 1926 Subpart P · FAA AC 150/5370-2', permit: 'Airside work permit', base: 'critical' },
      { name: 'Foundation pour for concourse', trade: 'Concrete', area: 'Concourse grid {B}', hazard: 'Pump truck boom near airspace', standard: 'OSHA 1926 Subpart Q · FAA Form 7460-1', base: 'serious' },
      { name: 'FOD control at staging area', trade: 'General', area: 'Airside laydown', hazard: 'Foreign object debris', standard: 'FAA AC 150/5380-5', base: 'warning' },
    ],
    mid: [
      { name: 'Mobile crane lift near approach surface', trade: 'Steel erection', area: 'Concourse roof', hazard: 'Airspace obstruction', standard: 'FAA Form 7460-1 · OSHA 1926 Subpart CC', permit: 'FAA obstruction determination', base: 'critical' },
      { name: 'Overnight terminal demo (occupied)', trade: 'Demolition', area: 'Gates C{L}0–C{L}4', hazard: 'Public separation / dust', standard: 'OSHA 1926 Subpart T', permit: 'Airport operations approval', base: 'serious' },
      { name: 'Concourse roofing', trade: 'Roofing', area: 'Concourse roof', hazard: 'Falls / wind-blown debris onto airside', standard: 'OSHA 1926 Subpart M', base: 'serious' },
    ],
    late: [
      { name: 'Airside paving near active taxiway', trade: 'Paving', area: 'Taxiway C', hazard: 'Aircraft movement area incursion', standard: 'FAA AC 150/5370-2 · CSPP', permit: 'Airside work permit', base: 'critical' },
      { name: 'Baggage system commissioning', trade: 'Conveyor', area: 'Bag hall', hazard: 'Caught-in moving equipment', standard: 'Lockout/tagout (OSHA 1910.147)', permit: 'Lockout/tagout plan', base: 'serious' },
      { name: 'Jet bridge installation', trade: 'Equipment', area: 'Gate C{B}', hazard: 'Heavy lift near aircraft stand', standard: 'OSHA 1926 Subpart CC', permit: 'Lift plan + airside escort', base: 'serious' },
    ],
  },
  Education: {
    early: [
      { name: 'Site excavation next to occupied campus', trade: 'Sitework', area: 'North lawn', hazard: 'Cave-in / student pedestrian routes', standard: 'OSHA 1926 Subpart P', permit: 'Competent person daily inspection', base: 'serious' },
      { name: 'Underground utilities', trade: 'Plumbing', area: 'Campus loop road', hazard: 'Trench / traffic', standard: 'OSHA 1926 Subpart P', base: 'serious' },
      { name: 'Foundation pour', trade: 'Concrete', area: 'Building {B}', hazard: 'Pump truck boom', standard: 'OSHA 1926 Subpart Q', base: 'warning' },
    ],
    mid: [
      { name: 'Masonry wall construction', trade: 'Masonry', area: 'Gym, north wall', hazard: 'Unbraced wall collapse', standard: 'OSHA 1926 Subpart Q', base: 'serious' },
      { name: 'Roofing tear-off (campus in session)', trade: 'Roofing', area: 'Building {B} roof', hazard: 'Falls / debris near pedestrians', standard: 'OSHA 1926 Subpart M', base: 'serious' },
      { name: 'After-hours steel delivery & set', trade: 'Steel erection', area: 'Science wing', hazard: 'Student pedestrian separation', standard: 'Site logistics plan · OSHA 1926 Subpart CC', permit: 'Campus access approval', base: 'serious' },
    ],
    late: [
      { name: 'Fire alarm acceptance testing', trade: 'Fire alarm', area: 'Building {B}', hazard: 'False alarms in occupied campus', standard: 'NFPA 72 · AHJ witness test', permit: 'Campus notification', base: 'warning' },
      { name: 'Drywall finishing & concrete grinding', trade: 'Interiors', area: 'Classrooms L{L}', hazard: 'Respirable crystalline silica', standard: 'OSHA 1926.1153 (silica)', base: 'serious' },
      { name: 'Site paving & striping', trade: 'Paving', area: 'Bus loop', hazard: 'Traffic near students', standard: 'MUTCD work-zone · site logistics plan', base: 'warning' },
    ],
  },
  Commercial: {
    early: [
      { name: 'Excavation & tieback installation', trade: 'Sitework', area: 'Basement B{B}', hazard: 'Cave-in / adjacent building', standard: 'OSHA 1926 Subpart P', permit: 'Competent person daily inspection', base: 'serious' },
      { name: 'Tower crane erection', trade: 'Crane', area: 'Core', hazard: 'Crane assembly', standard: 'OSHA 1926 Subpart CC', permit: 'Crane assembly plan', base: 'critical' },
      { name: 'Foundation mat pour', trade: 'Concrete', area: 'Mat, pour {B}', hazard: 'Pump truck boom', standard: 'OSHA 1926 Subpart Q', base: 'warning' },
    ],
    mid: [
      { name: 'Tower crane jump', trade: 'Crane', area: 'Core', hazard: 'Crane climbing operation', standard: 'OSHA 1926 Subpart CC', permit: 'Crane jump plan', base: 'critical' },
      { name: 'Post-tensioned slab stressing', trade: 'Concrete', area: 'Level {L}', hazard: 'Tendon release', standard: 'OSHA 1926 Subpart Q', base: 'serious' },
      { name: 'Swing-stage facade work', trade: 'Facade', area: 'West elevation', hazard: 'Suspended scaffold', standard: 'OSHA 1926 Subpart L', base: 'serious' },
    ],
    late: [
      { name: 'Elevator installation in hoistway', trade: 'Elevator', area: 'Car {B} hoistway', hazard: 'Falls into hoistway', standard: 'OSHA 1926 Subpart M', base: 'serious' },
      { name: 'Curtain wall final closure', trade: 'Glazing', area: 'Levels 18–24', hazard: 'Dropped objects over street', standard: 'OSHA 1926 Subpart M', permit: 'Sidewalk protection / street permit', base: 'serious' },
      { name: 'MEP energization & commissioning', trade: 'Electrical', area: 'Main electrical room', hazard: 'Arc flash / energized work', standard: 'OSHA 1926 Subpart K · NFPA 70E', permit: 'Energized work permit', base: 'critical' },
    ],
  },
}

export const phaseOf = (pct: number): Phase => (pct < 35 ? 'early' : pct < 70 ? 'mid' : 'late')
const NEXT: Record<Phase, Phase> = { early: 'mid', mid: 'late', late: 'late' }

/** 3 activities from the project's current phase (rotated per project) + 1 coming up from the next phase. */
function pickActivities(p: Project, idx: number): Template[] {
  const set = TEMPLATES[p.sector] ?? TEMPLATES.Commercial
  const ph = phaseOf(p.pctComplete)
  const cur = set[ph]
  const rot = idx % cur.length
  const now = [...cur.slice(rot), ...cur.slice(0, rot)].slice(0, 3)
  const nextList = set[NEXT[ph]].filter((t) => !now.includes(t))
  const fill = (t: Template): Template => ({
    ...t,
    name: t.name.replaceAll('{B}', String(1 + (idx % 4))).replaceAll('{L}', String(2 + (idx % 5))),
    area: t.area.replaceAll('{B}', String(1 + (idx % 4))).replaceAll('{L}', String(2 + (idx % 5))),
  })
  const upcoming = ph === 'late' ? [] : nextList.filter((t) => t.standard !== now[0].standard || t.trade !== now[0].trade)
  return [...now, ...(upcoming.length ? [upcoming[idx % upcoming.length]] : [])].map(fill)
}

const CREWS: Record<string, [string, string][]> = {
  'Data Center': [['Steel erection', 'Ironline Steel'], ['Electrical', 'Brightway Electric'], ['Concrete', 'Keystone Concrete'], ['Mechanical', 'Northgate Mechanical']],
  Healthcare: [['Mechanical', 'Northgate Mechanical'], ['Plumbing', 'Riverbend Plumbing'], ['Drywall', 'Summit Interiors'], ['Electrical', 'Brightway Electric']],
  Aviation: [['Paving', 'Tarmac Partners'], ['Steel erection', 'Ironline Steel'], ['Electrical', 'Brightway Electric'], ['Demolition', 'Clearcut Demo']],
  Education: [['Masonry', 'Cornerstone Masonry'], ['Roofing', 'Apex Roofing'], ['Concrete', 'Keystone Concrete'], ['Mechanical', 'Northgate Mechanical']],
  Commercial: [['Concrete', 'Keystone Concrete'], ['Facade', 'Skyline Facades'], ['Electrical', 'Brightway Electric'], ['Mechanical', 'Northgate Mechanical']],
}

const EVENTS: Record<string, Event[]> = {
  'Data Center': [{ time: '7:00', what: 'Switchgear lineup delivery (3 trucks) — gate 2', kind: 'delivery' }, { time: '10:30', what: 'Third-party steel connection inspection — L3', kind: 'inspection' }],
  Healthcare: [{ time: '6:30', what: 'ICRA barrier inspection with hospital infection control', kind: 'inspection' }, { time: '9:00', what: 'Ductwork delivery — loading dock (before 10:00 window)', kind: 'delivery' }],
  Aviation: [{ time: '22:00', what: 'Airside escort & vehicle check — airside gate A', kind: 'inspection' }, { time: '5:00', what: 'Asphalt delivery — airside gate A', kind: 'delivery' }],
  Education: [{ time: '15:30', what: 'Steel delivery after school dismissal', kind: 'delivery' }, { time: '11:00', what: 'Masonry bracing inspection', kind: 'inspection' }],
  Commercial: [{ time: '6:00', what: 'Curtain wall units — street closure permit 6–9am', kind: 'delivery' }, { time: '13:00', what: 'City inspection — L24 rebar', kind: 'inspection' }],
}

const WHEN = ['Today', 'Tomorrow', 'Thu', 'Next Mon']
const SUPERS = ['Dana Morales', 'Chris Okafor', 'Sam Whitfield', 'Lee Park', 'Avery Brooks', 'Morgan Diaz', 'Jesse Nguyen', 'Riley Chen', 'Taylor Grant', 'Jordan Price', 'Casey Lopez', 'Drew Patel']
const WEATHER: Record<string, string> = { Northeast: '41°F · wind 18 mph gusting 28', Midwest: '38°F · light rain PM', Southeast: '66°F · clear', West: '58°F · clear', Southwest: '72°F · wind 12 mph' }
const NEAR_MISS_THEME: Record<string, string> = { 'Data Center': 'fall protection at leading edges', Healthcare: 'ladder use in corridors', Aviation: 'vehicle near-miss at airside gate', Education: 'pedestrian route breach', Commercial: 'dropped object from L22' }

/** Readiness checks derived from the project's risk signals (higher signal = more likely blocked). */
function checksFor(p: Project, i: number): Activity['checks'] {
  const s = p.signals
  const n = (x: number) => x.toString().padStart(4, '0')
  const rfiBlocked = s.rfi >= 55 && i % 2 === 0
  const subBlocked = s.submittal >= 55 && i % 2 === 1
  const lowFloat = s.schedule >= 60 && i < 2
  const matLate = s.co >= 65 && i === 1
  return [
    { label: 'Info', ok: !rfiBlocked, detail: rfiBlocked ? `RFI-${n(380 + i * 7)} open ${21 + i * 3} days` : 'No open RFIs', owner: rfiBlocked ? 'Architect / EOR' : undefined, neededBy: rfiBlocked ? WHEN[Math.max(0, i - 1)] : undefined },
    { label: 'Approvals', ok: !subBlocked, detail: subBlocked ? `Submittal ${['05 12 00', '26 24 13', '23 31 13', '07 84 00'][i % 4]} not approved` : 'Submittals approved', owner: subBlocked ? 'Design team' : undefined, neededBy: subBlocked ? WHEN[Math.max(0, i - 1)] : undefined },
    { label: 'Materials', ok: !matLate, detail: matLate ? 'Partial delivery — 1 of 3 sections short' : 'On site / confirmed', owner: matLate ? 'Supplier via PM' : undefined },
    { label: 'Float', ok: !lowFloat, detail: lowFloat ? `${Math.max(0, 4 - i * 2)} days float (critical path)` : 'Float OK' },
  ]
}

export function jobsiteDay(p: Project): JobsiteDay {
  const idx = Math.max(0, Number(p.id.replace(/\D/g, '')) - 1001)
  const tpl = pickActivities(p, idx)
  const riskBump = (p.signals.safety + p.signals.schedule) / 2 >= 55
  const activities: Activity[] = tpl.map((t, i) => ({
    ...t,
    id: `${p.id}-A${i + 1}`,
    when: WHEN[i],
    level: t.base === 'warning' && riskBump ? 'serious' : t.base,
    checks: checksFor(p, i),
  }))
  const short = p.signals.schedule >= 55
  const crews: Crew[] = (CREWS[p.sector] ?? CREWS.Commercial).map(([trade, company], i) => {
    const planned = 8 + ((idx * 3 + i * 5) % 14)
    const gap = short && i < 2 ? Math.ceil(planned * 0.3) : i === 3 && p.signals.cost >= 60 ? 2 : 0
    return { trade, company, planned, yesterday: planned - gap }
  })
  return {
    phase: phaseOf(p.pctComplete),
    project: p,
    superintendent: SUPERS[idx % SUPERS.length],
    weather: WEATHER[p.region] ?? '60°F · clear',
    nearMisses: { count: Math.round(p.signals.safety / 28), theme: NEAR_MISS_THEME[p.sector] ?? 'housekeeping' },
    activities,
    crews,
    // Deliveries/inspections follow this project's own activities (phase-aware), not a fixed sector list.
    events: [
      { time: '7:00', what: `${(activities.find((a) => !['General', 'Sitework', 'Commissioning', 'Demolition'].includes(a.trade)) ?? activities[0]).trade} materials delivery — ${(activities.find((a) => !['General', 'Sitework', 'Commissioning', 'Demolition'].includes(a.trade)) ?? activities[0]).area}`, kind: 'delivery' },
      { time: '10:30', what: `${activities[1].permit ? activities[1].permit : 'Third-party inspection'} — ${activities[1].name.toLowerCase()}`, kind: 'inspection' },
      ...(EVENTS[p.sector] ?? []).filter((e) => e.kind === 'inspection' && /ICRA|airside|escort/i.test(e.what)).slice(0, 1),
    ],
  }
}
