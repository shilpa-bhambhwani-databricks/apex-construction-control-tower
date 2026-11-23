/**
 * Brand contract. Rebranding the app for a new customer = add one file that
 * satisfies this interface + drop logos in /public/brands/<id>/. No component
 * code should ever reference a customer by name.
 */
export type ModuleId = 'risk-radar' | 'resolve' | 'jobsite'

export interface BrandColors {
  /** Top bar / brand chrome (usually the logo color). */
  chrome: string
  chromeText: string
  /** Primary interactive color: links, active tab, selected rows, focus. */
  primary: string
  primaryHover: string
  primaryText: string
  /** Call-to-action accent (buttons, arrows). Never used for data/status. */
  accent: string
  accentHover: string
  accentText: string
  ink: string
  inkMuted: string
  border: string
  surface: string
  surfaceAlt: string
  /** Light tint of primary for selected / hover backgrounds. */
  primaryTint: string
  /** Diverging risk scale, low → high: cool green/teal → neutral gray midpoint → reddish-brown. */
  riskRamp: [string, string, string, string, string, string, string]
}

export interface BrandConfig {
  id: string
  customerName: string
  /** Short name used inside sentences, e.g. "Apex EHS standards". Falls back to customerName. */
  shortName?: string
  /** Product name shown next to the logo, e.g. "Control Tower". */
  appName: string
  tagline: string
  /** Bottom band text. No customer name by default — set per brand when asked. */
  footer?: { left?: string; right?: string }
  logo: {
    /** Logo used on the dark chrome bar. */
    onDark: string
    /** Logo used on light surfaces. */
    onLight: string
    alt: string
    height: number
  }
  colors: BrandColors
  fonts: {
    /** CSS font-family stack. Put the licensed brand face first, then a free fallback. */
    body: string
    heading: string
    /** Brand weights — some brands use light weights for large text. */
    headingWeight: number
  }
  /** Corner radius for cards/buttons. */
  radius: string
  /** Which tabs are enabled, in order. */
  modules: ModuleId[]
  /** Optional per-customer labels for module tabs. */
  moduleLabels?: Partial<Record<ModuleId, string>>
  /** Demo persona shown in the header until real OBO identity is wired in. */
  demoPersona: { name: string; role: string; scope: string }
  /** Market sectors used for filters. */
  sectors: string[]
  regions: string[]
  /** Customer systems of record — shown as "source" chips so we never look like a replacement. */
  systemsOfRecord: string[]
}
