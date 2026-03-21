import type { GraphTopologyMeta } from '../../types/graph'

export function buildGraphSourceSummary(meta: GraphTopologyMeta | null | undefined): {
  title: string
  source: string
  notice: string
  badge: string
  calculationNote: string
  fallbackTip: string
}
