import { createContext, useContext, useLayoutEffect, type ReactNode } from 'react'
import type { BrandConfig } from '../brands'

const BrandContext = createContext<BrandConfig | null>(null)

export function useBrand(): BrandConfig {
  const b = useContext(BrandContext)
  if (!b) throw new Error('useBrand must be used inside <BrandProvider>')
  return b
}

/** Maps the brand config onto CSS custom properties; all styling reads these. */
export function BrandProvider({ brand, children }: { brand: BrandConfig; children: ReactNode }) {
  useLayoutEffect(() => {
    const s = document.documentElement.style
    const c = brand.colors
    const vars: Record<string, string> = {
      '--chrome': c.chrome,
      '--chrome-text': c.chromeText,
      '--primary': c.primary,
      '--primary-hover': c.primaryHover,
      '--primary-text': c.primaryText,
      '--primary-tint': c.primaryTint,
      '--accent': c.accent,
      '--accent-hover': c.accentHover,
      '--accent-text': c.accentText,
      '--ink': c.ink,
      '--ink-muted': c.inkMuted,
      '--border': c.border,
      '--surface': c.surface,
      '--surface-alt': c.surfaceAlt,
      '--font-body': brand.fonts.body,
      '--font-heading': brand.fonts.heading,
      '--heading-weight': String(brand.fonts.headingWeight),
      '--radius': brand.radius,
    }
    c.riskRamp.forEach((hex, i) => (vars[`--risk-${i}`] = hex))
    Object.entries(vars).forEach(([k, v]) => s.setProperty(k, v))
    document.title = `${brand.customerName} · ${brand.appName}`
    document.documentElement.dataset.brand = brand.id
  }, [brand])

  return <BrandContext.Provider value={brand}>{children}</BrandContext.Provider>
}
