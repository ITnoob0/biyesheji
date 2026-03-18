import type { RecommendationItem } from '../../types/projectGuides'

export function buildRecommendationSortOptions(): Array<{ value: string; label: string }>
export function filterRecommendationItems(
  items: RecommendationItem[],
  search: string,
  focus: string,
): RecommendationItem[]
export function sortRecommendationItems(items: RecommendationItem[], sortBy: string): RecommendationItem[]
