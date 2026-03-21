import type { DimensionTrendPoint, PaperRecord } from './portrait'

export function buildKeywordEvolution(
  papers: PaperRecord[],
): Array<{ year: number; keywords: Array<{ name: string; count: number }>; paperCount: number }>

export function buildThemeFocusSummary(
  papers: PaperRecord[],
): { ratio: number; label: string; description: string; topKeywords: Array<{ name: string; count: number }> }

export function buildDimensionTrendNarrative(trend: DimensionTrendPoint[]): string
