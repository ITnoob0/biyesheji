import type { RecommendationAdminAnalysis, RecommendationItem } from './types'

export interface RecommendationFilterOptions {
  level?: string
  priority?: string
  label?: string
  favoritesOnly?: boolean
  favoriteIds?: number[]
}

export interface RecommendationSortOption {
  value: string
  label: string
}

export interface DistributionCard {
  label: string
  value: number | string
  helper: string
}

export declare function buildRecommendationSortOptions(): RecommendationSortOption[]

export declare function filterRecommendationItems(
  items: RecommendationItem[],
  search: string,
  focus: string,
  options?: RecommendationFilterOptions,
): RecommendationItem[]

export declare function sortRecommendationItems(items: RecommendationItem[], sortBy: string): RecommendationItem[]

export declare function buildDistributionCards(
  analysis: RecommendationAdminAnalysis | null,
): DistributionCard[]
