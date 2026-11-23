import { useCallback, useEffect, useState } from 'react'
import { Bell, CalendarClock, Check, Send, UserPlus, X } from 'lucide-react'
import { apiHeaders } from '../api/genie'

/**
 * Assign follow-up & notify (agent action level 2): writes to Lakebase via /api/followups, which first checks
 * the caller can see the project (Unity Catalog row filter). Notifies in-app + queues email and Slack.
 */
export interface FollowUp { id: number; project_id: string; project_name?: string; item_ref?: string; owner: string; due_date?: string; note?: string; status: string; created_by: string; created_at: string }

const EVT = 'ct-followups-changed'
const notifyChanged = () => window.dispatchEvent(new Event(EVT))

export async function createFollowUp(body: { project_id: string; item_ref?: string; owner: string; due_date?: string; note?: string; source?: string }) {
  const r = await fetch('/api/followups', { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) })
  if (!r.ok) { let m = await r.text(); try { m = JSON.parse(m).detail ?? m } catch { /* plain */ } throw new Error(m) }
  notifyChanged()
  return r.json() as Promise<{ id: number; title: string; notified: string[]; slack_channel?: string | null }>
}

function useFollowUps(projectId?: string) {
  const [items, setItems] = useState<FollowUp[]>([])
  const load = useCallback(() => {
    fetch(`/api/followups${projectId ? `?project_id=${projectId}` : ''}`, { headers: apiHeaders() })
      .then((r) => (r.ok ? r.json() : [])).then(setItems).catch(() => setItems([]))
  }, [projectId])
  useEffect(() => { load(); window.addEventListener(EVT, load); return () => window.removeEventListener(EVT, load) }, [load])
  return items
}

const inDays = (n: number) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10)
const fmtDue = (d?: string) => (d ? new Date(d + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'no due date')

/** Form + list, used on the Risk Radar project detail card. `prefill` lets Genie answers hand off a note. */
export function FollowUpPanel({ projectId, ownerHints, prefill, onPrefillUsed }: { projectId: string; ownerHints: string[]; prefill?: string; onPrefillUsed?: () => void }) {
  const items = useFollowUps(projectId)
  const [open, setOpen] = useState(false)
  const [owner, setOwner] = useState('')
  const [due, setDue] = useState(inDays(3))
  const [itemRef, setItemRef] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => { if (prefill) { setOpen(true); setNote(prefill); onPrefillUsed?.() } }, [prefill, onPrefillUsed])
  useEffect(() => { setOpen(false); setMsg(null) }, [projectId])

  const submit = async () => {
    if (owner.trim().length < 2) { setMsg({ ok: false, text: 'Add an owner.' }); return }
    setBusy(true); setMsg(null)
    try {
      const r = await createFollowUp({ project_id: projectId, owner: owner.trim(), due_date: due || undefined, item_ref: itemRef.trim() || undefined, note: note.trim() || undefined })
      setMsg({ ok: true, text: `Assigned to ${owner.trim()} · notified ${r.notified.map(c => c === 'slack' && r.slack_channel ? `Slack ${r.slack_channel}` : c).join(' + ')}` })
      setOwner(''); setItemRef(''); setNote(''); setOpen(false)
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }) } finally { setBusy(false) }
  }

  return (
    <div className="fu">
      {!open ? (
        <button className="btn btn-ghost wide" onClick={() => { setOpen(true); setMsg(null) }}><UserPlus size={14} aria-hidden /> Assign follow-up</button>
      ) : (
        <form className="fu-form" onSubmit={(e) => { e.preventDefault(); submit() }}>
          <div className="fu-row">
            <label>Owner<input list="fu-owners" value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="Who should act?" autoFocus /></label>
            <label>Due<input type="date" value={due} onChange={(e) => setDue(e.target.value)} /></label>
          </div>
          <datalist id="fu-owners">{ownerHints.map((o) => <option key={o} value={o} />)}</datalist>
          <label>Item (optional)<input value={itemRef} onChange={(e) => setItemRef(e.target.value)} placeholder="e.g. RFI-0387, CO-0142" /></label>
          <label>Note<textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="What needs to happen?" /></label>
          <div className="fu-actions">
            <button type="submit" className="btn btn-primary" disabled={busy}><Send size={14} aria-hidden /> {busy ? 'Assigning…' : 'Assign & notify'}</button>
            <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}><X size={14} aria-hidden /> Cancel</button>
          </div>
          <p className="muted small">Saved in Control Tower (Lakebase) — notifies the owner in-app, by email and in Slack. Nothing is written to Procore or Clearstory.</p>
        </form>
      )}
      {msg && <p className={`fu-msg ${msg.ok ? 'ok' : 'bad'}`}>{msg.ok ? <Check size={14} aria-hidden /> : <X size={14} aria-hidden />} {msg.text}</p>}
      {items.length > 0 && (
        <ul className="fu-list" aria-label="Follow-ups">
          {items.slice(0, 4).map((f) => (
            <li key={f.id}>
              <CalendarClock size={14} aria-hidden />
              <div><strong>{f.owner}</strong>{f.item_ref ? ` · ${f.item_ref}` : ''} <span className="muted small">due {fmtDue(f.due_date)}</span>
                {f.note && <div className="small">{f.note}</div>}
                <div className="muted small">by {f.created_by}</div></div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Header bell: in-app notifications the current identity can see. */
export function NotificationBell() {
  const [items, setItems] = useState<{ id: number; title: string; body: string; created_at: string }[]>([])
  const [open, setOpen] = useState(false)
  const load = useCallback(() => {
    fetch('/api/notifications', { headers: apiHeaders() }).then((r) => (r.ok ? r.json() : [])).then(setItems).catch(() => setItems([]))
  }, [])
  useEffect(() => { load(); window.addEventListener(EVT, load); return () => window.removeEventListener(EVT, load) }, [load])
  return (
    <div className="bell">
      <button className="bell-btn" aria-label={`Notifications (${items.length})`} onClick={() => setOpen((v) => !v)}>
        <Bell size={18} />{items.length > 0 && <span className="bell-count">{items.length}</span>}
      </button>
      {open && (
        <div className="bell-pop" role="dialog" aria-label="Notifications">
          <p className="sugg-label">Notifications</p>
          {items.length === 0 ? <p className="muted small">No notifications yet.</p> : (
            <ul>{items.map((n) => <li key={n.id}><strong>{n.title}</strong><div className="small">{n.body}</div><div className="muted small">{new Date(n.created_at).toLocaleString()}</div></li>)}</ul>
          )}
        </div>
      )}
    </div>
  )
}
