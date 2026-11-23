import type { ReactNode } from 'react'
import { FileText, Database } from 'lucide-react'

/**
 * Minimal, safe markdown for agent/Genie text: **bold**, "- " bullets, and [citations] rendered as chips.
 * React escapes all text, so model output can never inject HTML.
 */
function inline(line: string, key: string | number): ReactNode[] {
  return line.split(/(\*\*[^*]+\*\*|\[[^\]]{3,140}\])/g).filter(Boolean).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>
    if (part.startsWith('[') && part.endsWith(']')) {
      const refs = part.slice(1, -1).split(/;\s*/)
      return refs.map((r, j) => {
        const isDoc = /\.pdf|p\.\d|§|Exh/i.test(r)
        return (
          <span key={`${key}-${i}-${j}`} className={`cite-chip ${isDoc ? 'doc' : 'tool'}`} title={r}>
            {isDoc ? <FileText size={11} aria-hidden /> : <Database size={11} aria-hidden />} {r.replace(/\.pdf/g, '').replace(/_/g, ' ')}
          </span>
        )
      })
    }
    return <span key={`${key}-${i}`}>{part}</span>
  })
}

export function Md({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length) {
      blocks.push(<ul key={blocks.length} className="bullets md-list">{bullets.map((b, i) => <li key={i}>{inline(b, i)}</li>)}</ul>)
      bullets = []
    }
  }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (/^[-*] /.test(line)) { bullets.push(line.slice(2)); continue }
    flush()
    if (/^\*\*[^*]+\*\*$/.test(line)) blocks.push(<p key={blocks.length} className="md-h">{line.slice(2, -2)}</p>)
    else if (line) blocks.push(<p key={blocks.length}>{inline(line, blocks.length)}</p>)
  }
  flush()
  return <div className="md">{blocks}</div>
}
