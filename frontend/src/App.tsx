import { useEffect, useMemo, useState } from 'react'
import { fetchMe, setPersona, type Me } from './api/genie'
import { ProjectsProvider } from './data/ProjectsProvider'
import { NotificationBell } from './components/FollowUps'
import { Radar, Wrench, HardHat, ShieldCheck, type LucideIcon } from 'lucide-react'
import { resolveBrand, type ModuleId } from './brands'
import { BrandProvider, useBrand } from './theme/BrandProvider'
import { RiskRadar } from './modules/riskRadar/RiskRadar'
import { Resolve } from './modules/resolve/Resolve'
import { Jobsite } from './modules/jobsite/Jobsite'

/** Module registry — brands choose which of these appear, and in what order. */
const MODULES: Record<ModuleId, { label: string; icon: LucideIcon }> = {
  'risk-radar': { label: 'Risk Radar', icon: Radar },
  resolve: { label: 'Resolve', icon: Wrench },
  jobsite: { label: 'Jobsite Intelligence', icon: HardHat },
}

export default function App() {
  const brand = useMemo(resolveBrand, [])
  return (
    <BrandProvider brand={brand}>
      <Shell />
    </BrandProvider>
  )
}

function Shell() {
  const brand = useBrand()
  const [tab, setTab] = useState<ModuleId>(brand.modules[0])
  const [resolveProject, setResolveProject] = useState<string>()
  /** Bumps when the demo persona changes so every tab remounts and re-queries as the new identity. */
  const [epoch, setEpoch] = useState(0)

  return (
    <div className="app">
      <header className="topbar">
        <div className="brandmark">
          <img src={brand.logo.onDark} alt={brand.logo.alt} style={{ height: brand.logo.height }} />
          <span className="divider" aria-hidden />
          <span className="app-name">{brand.appName}</span>
        </div>
        <nav className="tabs" aria-label="Modules">
          {brand.modules.map((id) => {
            const M = MODULES[id]
            return (
              <button key={id} className={tab === id ? 'active' : ''} aria-current={tab === id ? 'page' : undefined} onClick={() => setTab(id)}>
                <M.icon size={16} aria-hidden /> {brand.moduleLabels?.[id] ?? M.label}
              </button>
            )
          })}
        </nav>
        <div className="top-right">
          <NotificationBell key={epoch} />
          <PersonaSwitch onChange={() => setEpoch((e) => e + 1)} />
        </div>
      </header>

      <ProjectsProvider key={epoch}>
      <main>
        {tab === 'risk-radar' && <RiskRadar onOpenResolve={(id) => { setResolveProject(id); setTab('resolve') }} />}
        {tab === 'resolve' && <Resolve projectId={resolveProject} />}
        {tab === 'jobsite' && <Jobsite />}
      </main>
      </ProjectsProvider>

      <footer className="footer">
        <span>{brand.footer?.left ?? `${brand.appName} — built on Databricks Apps · Unity Catalog governed`}</span>
        <span className="muted">{brand.footer?.right ?? 'Synthetic demo data'}</span>
      </footer>
    </div>
  )
}

/** Header identity block. In demo mode it switches between the signed-in user and simulated identities. */
function PersonaSwitch({ onChange }: { onChange: () => void }) {
  const brand = useBrand()
  const [me, setMe] = useState<Me | null>(null)
  useEffect(() => { fetchMe().then(setMe) }, [])
  const label = me?.persona === 'presenter' || !me ? brand.demoPersona.name : me.label
  const role = me ? me.role : brand.demoPersona.role
  const scope = me ? me.scope : brand.demoPersona.scope
  const pick = async (id: string) => { setPersona(id); setMe(await fetchMe()); onChange() }
  return (
    <div className="persona" title="Signed-in identity and data scope — enforced by Unity Catalog row filters">
      <ShieldCheck size={16} aria-hidden />
      <div>
        <div className="persona-name">{label} · {role}</div>
        <div className="persona-scope">{scope}</div>
      </div>
      {me?.demo_mode && me.personas.length > 0 ? (
        <select className="persona-select" aria-label="Demo identity" value={me.persona} onChange={(e) => pick(e.target.value)}>
          {me.personas.map((p) => <option key={p.id} value={p.id}>{p.id === 'presenter' ? `You (${p.role})` : p.label}</option>)}
        </select>
      ) : (
        <span className="avatar" aria-hidden>{label.split(' ').map((n) => n[0]).join('').slice(0, 2)}</span>
      )}
    </div>
  )
}
