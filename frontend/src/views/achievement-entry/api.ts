import axios from 'axios'
import {
  achievementEndpointMap,
  paperCleanupApplyEndpoint,
  paperCompareEndpoint,
  paperExportEndpoint,
  paperGovernanceEndpoint,
  paperImportEndpointMap,
  paperRepresentativeBatchEndpoint,
  paperSummaryEndpoint,
} from './constants'
import type {
  AchievementListResponseMap,
  AchievementMutationPayloadMap,
  AchievementQueryState,
  AchievementRecordMap,
  BibtexPreviewEntry,
  PaperCleanupResponse,
  PaperComparisonResponse,
  PaperGovernanceResponse,
  PaperHistoryResponse,
  PaperRepresentativeBatchResponse,
  PaperSummaryResponse,
  TabName,
} from '../../types/achievements'

const buildQueryParams = <T extends TabName>(tab: T, rawState?: Partial<AchievementQueryState[T]>) => {
  const params = new URLSearchParams()

  Object.entries(rawState || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return

    const normalized = String(value).trim()
    if (!normalized) return

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

export const fetchPaperGovernance = async (
  queryState?: Partial<AchievementQueryState['papers']>,
): Promise<PaperGovernanceResponse> => {
  const response = await axios.get<PaperGovernanceResponse>(paperGovernanceEndpoint, {
    params: buildQueryParams('papers', queryState),
  })
  return response.data
}

export const fetchPaperComparison = async (leftId: number, rightId: number): Promise<PaperComparisonResponse> => {
  const response = await axios.get<PaperComparisonResponse>(paperCompareEndpoint, {
    params: { left_id: leftId, right_id: rightId },
  })
  return response.data
}

export const fetchPaperHistory = async (paperId: number): Promise<PaperHistoryResponse> => {
  const response = await axios.get<PaperHistoryResponse>(`${achievementEndpointMap.papers}${paperId}/history/`)
  return response.data
}

export const exportPaperGovernance = async (queryState?: Partial<AchievementQueryState['papers']>): Promise<Blob> => {
  const response = await axios.get(paperExportEndpoint, {
    params: buildQueryParams('papers', queryState),
    responseType: 'blob',
  })
  return response.data
}

export const batchUpdatePaperRepresentative = async (
  paperIds: number[],
  isRepresentative: boolean,
): Promise<PaperRepresentativeBatchResponse> => {
  const response = await axios.post<PaperRepresentativeBatchResponse>(paperRepresentativeBatchEndpoint, {
    paper_ids: paperIds,
    is_representative: isRepresentative,
  })
  return response.data
}

export const applyPaperCleanup = async (
  paperIds: number[],
  action = 'normalize_text_fields',
): Promise<PaperCleanupResponse> => {
  const response = await axios.post<PaperCleanupResponse>(paperCleanupApplyEndpoint, {
    paper_ids: paperIds,
    action,
  })
  return response.data
}

export const revalidateBibtexEntries = async (entries: BibtexPreviewEntry[]) => {
  const response = await axios.post(paperImportEndpointMap.bibtexRevalidate, { entries })
  return response.data
}
