import type { GraphTopologyMeta } from '../../types/graph'

export function buildGraphSourceSummary(meta: GraphTopologyMeta | null | undefined): {
  title: string
  source: string
  notice: string
  badge: string
  sourceScopeNote: string
  degradationNote: string
  interactionNote: string
  calculationNote: string
  fallbackTip: string
}
