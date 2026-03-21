import axios from 'axios'
import { achievementEndpointMap, paperSummaryEndpoint } from './constants'
import type {
  AchievementListResponseMap,
  AchievementMutationPayloadMap,
  AchievementQueryState,
  AchievementRecordMap,
  PaperSummaryResponse,
  TabName,
} from '../../types/achievements'

const buildQueryParams = <T extends TabName>(tab: T, rawState?: Partial<AchievementQueryState[T]>) => {
  const params = new URLSearchParams()

  Object.entries(rawState || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return
    }

    const normalized = String(value).trim()
    if (!normalized) {
      return
    }

    if (tab === 'papers' && ['paper_type', 'year', 'is_representative'].includes(key) && normalized === 'ALL') {
      return
    }

    params.append(key, normalized)
  })

  return Object.fromEntries(params.entries())
}

export const fetchAchievementList = async <T extends TabName>(
  tab: T,
  queryState?: Partial<AchievementQueryState[T]>,
): Promise<AchievementListResponseMap[T]> => {
  const response = await axios.get<AchievementListResponseMap[T]>(achievementEndpointMap[tab], {
    params: buildQueryParams(tab, queryState),
  })

  return Array.isArray(response.data) ? response.data : []
}

export const createAchievement = async <T extends TabName>(
  tab: T,
  payload: AchievementMutationPayloadMap[T],
): Promise<AchievementRecordMap[T]> => {
  const response = await axios.post<AchievementRecordMap[T]>(achievementEndpointMap[tab], payload)
  return response.data
}

export const updateAchievement = async <T extends TabName>(
  tab: T,
  id: number,
  payload: AchievementMutationPayloadMap[T],
): Promise<AchievementRecordMap[T]> => {
  const response = await axios.patch<AchievementRecordMap[T]>(`${achievementEndpointMap[tab]}${id}/`, payload)
  return response.data
}

export const deleteAchievement = async (tab: TabName, id: number): Promise<void> => {
  await axios.delete(`${achievementEndpointMap[tab]}${id}/`)
}

export const fetchPaperSummary = async (
  queryState?: Partial<AchievementQueryState['papers']>,
): Promise<PaperSummaryResponse> => {
  const response = await axios.get<PaperSummaryResponse>(paperSummaryEndpoint, {
    params: buildQueryParams('papers', queryState),
  })
  return response.data
}
