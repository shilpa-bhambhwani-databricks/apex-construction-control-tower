/**
 * Thin client for the FastAPI Genie proxy (/api/genie/*). The backend calls the
 * Genie Conversation API on behalf of the signed-in user (OBO), so ABAC applies.
 */
export interface GenieTable { columns: string[]; rows: (string | null)[][] }
export interface GenieReply { conversation_id: string; message_id: string; text?: string | null; sql?: string | null; table?: GenieTable | null }

let liveStatus: Promise<boolean> | null = null

/** Demo persona (presenter / simulated identities). Sent on every API call; backend picks the identity. */
let persona = 'presenter'
export const setPersona = (p: string) => { persona = p }
export const apiHeaders = (extra: Record<string, string> = {}) => ({ 'x-demo-persona': persona, ...extra })

export interface Persona { id: string; label: string; role: string; scope: string }
export interface Me { email?: string; persona: string; label: string; role: string; scope: string; demo_mode: boolean; personas: Persona[] }
export async function fetchMe(): Promise<Me | null> {
  try { const r = await fetch('/api/me', { headers: apiHeaders() }); return r.ok ? r.json() : null } catch { return null }
}

/** True when the backend is reachable AND has a Genie space configured. Cached per page load. */
export function genieIsLive(): Promise<boolean> {
  liveStatus ??= fetch('/api/health')
    .then((r) => (r.ok ? r.json() : { genie: false }))
    .then((j) => Boolean(j?.genie))
    .catch(() => false)
  return liveStatus
}

export async function askGenie(question: string, conversationId?: string): Promise<GenieReply> {
  const r = await fetch('/api/genie/ask', {
    method: 'POST',
    headers: apiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question, conversation_id: conversationId ?? null }),
  })
  if (!r.ok) {
    const raw = await r.text()
    let msg = raw
    try { msg = JSON.parse(raw).detail ?? raw } catch { /* not JSON */ }
    throw new Error(msg || `Genie request failed (${r.status})`)
  }
  return r.json()
}
