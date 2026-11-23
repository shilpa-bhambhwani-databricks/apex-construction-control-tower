import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { PROJECTS, type Project } from '../modules/riskRadar/data'
import { apiHeaders } from '../api/genie'

/**
 * One shared project list for every tab, read from /api/risk/projects (UC metric view, as the
 * selected identity). If the backend is unreachable, falls back to the bundled sample data so the
 * UI still works offline. Remounted per persona (App keys <main> by persona epoch) → refetch.
 */
interface State { projects: Project[]; live: boolean; loading: boolean; error?: string }
const Ctx = createContext<State>({ projects: PROJECTS, live: false, loading: false })

export function ProjectsProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ projects: [], live: false, loading: true })
  useEffect(() => {
    let cancelled = false
    fetch('/api/risk/projects', { headers: apiHeaders() })
      .then(async (r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then((j) => {
        if (cancelled) return
        setState({ projects: j.projects as Project[], live: true, loading: false })
        prefetch(j.projects as Project[])
      })
      .catch((e) => { if (!cancelled) setState({ projects: PROJECTS, live: false, loading: false, error: String(e) }) })
    return () => { cancelled = true }
  }, [])
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>
}

/**
 * Warm the backend's per-identity cache for the tabs the demo opens next (Resolve → CO-0142, Jobsite → Atlas),
 * in the background, so switching tabs doesn't wait on the SQL warehouse. Results are discarded here.
 */
function prefetch(projects: Project[]) {
  const pid = (projects.find((p) => p.id === 'P-1001') ?? projects[0])?.id
  if (!pid) return
  const h = { headers: apiHeaders() }
  const quiet = () => {}
  window.setTimeout(() => {
    fetch(`/api/jobsite/day?project_id=${pid}`, h).catch(quiet)
    fetch(`/api/resolve/backlog?project_id=${pid}`, h)
      .then((r) => (r.ok ? r.json() : null))
      .then((j: { items: { id: string }[] } | null) => {
        const ids = j?.items.map((i) => i.id) ?? []
        const first = ids.includes('CO-0142') ? 'CO-0142' : ids[0]
        if (first) fetch(`/api/resolve/item?project_id=${pid}&item_id=${first}`, h).catch(quiet)
        ids.filter((i) => i !== first && i.startsWith('RFI')).slice(0, 2)
          .forEach((i) => fetch(`/api/resolve/item?project_id=${pid}&item_id=${i}`, h).catch(quiet))
      })
      .catch(quiet)
  }, 300)
}

export const useProjects = () => useContext(Ctx)
