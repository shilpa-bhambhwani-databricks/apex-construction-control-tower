import type { BrandConfig } from './types'
import { apex } from './apex'

/**
 * Every brand file in this folder registers itself: add `<id>.ts` exporting a BrandConfig and it is picked up
 * at build time. Customer brand files are optional — the app builds and runs with only the neutral `apex` brand.
 */
const files = import.meta.glob<Record<string, unknown>>(['./*.ts', '!./index.ts', '!./types.ts'], { eager: true })
const isBrand = (v: unknown): v is BrandConfig => !!v && typeof v === 'object' && 'id' in v && 'colors' in v
export const BRANDS: Record<string, BrandConfig> = Object.fromEntries(
  Object.values(files).flatMap((m) => Object.values(m)).filter(isBrand).map((b) => [b.id, b]),
)

/**
 * Brand resolution order: ?brand= query param (handy for live demo switching)
 * → VITE_BRAND build env → 'apex' (neutral house brand).
 */
export function resolveBrand(): BrandConfig {
  const fromQuery = new URLSearchParams(window.location.search).get('brand')
  const id = fromQuery ?? import.meta.env.VITE_BRAND ?? 'apex'
  return BRANDS[id] ?? apex
}

export type { BrandConfig, ModuleId } from './types'
