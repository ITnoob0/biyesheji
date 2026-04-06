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
  AchievementReviewActionResponse,
  AchievementWorkflowHistoryResponse,
  AchievementMutationPayloadMap,
  AchievementOperationHistoryResponse,
  AchievementQueryState,
  AchievementRecordMap,
  BibtexPreviewEntry,
  PaperCleanupResponse,
  PaperComparisonResponse,
  PaperGovernanceResponse,
  PaperHistoryResponse,
  PaperRepresentativeBatchResponse,
  PaperSummaryResponse,
  PaperRecord,
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

    if (tab === 'papers' && key === 'year') {
      if (normalized === 'RECENT_1') {
        params.append('year_from', String(new Date().getFullYear()))
        return
      }
      if (normalized === 'RECENT_3') {
        params.append('year_from', String(new Date().getFullYear() - 2))
        return
      }
      if (normalized === 'RECENT_5') {
        params.append('year_from', String(new Date().getFullYear() - 4))
        return
      }
    }

    params.append(key, normalized)
  })

  return Object.fromEntries(params.entries())
}

const buildLooseQueryParams = (rawState?: Record<string, string | number | boolean | undefined | null>) => {
  const params = new URLSearchParams()

  Object.entries(rawState || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    const normalized = String(value).trim()
    if (!normalized) return
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

export const fetchAchievementOperations = async (
  tab: TabName,
  queryState?: Record<string, string | number | boolean | undefined | null>,
): Promise<AchievementOperationHistoryResponse> => {
  const response = await axios.get<AchievementOperationHistoryResponse>(`${achievementEndpointMap[tab]}operations/`, {
    params: buildLooseQueryParams(queryState),
  })
  return response.data
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

export const fetchAchievementWorkflowHistory = async (
  tab: TabName,
  achievementId: number,
): Promise<AchievementWorkflowHistoryResponse> => {
  const response = await axios.get<AchievementWorkflowHistoryResponse>(
    `${achievementEndpointMap[tab]}${achievementId}/workflow-logs/`,
  )
  return response.data
}

export const fetchPendingReviewAchievements = async <T extends TabName>(
  tab: T,
): Promise<AchievementListResponseMap[T]> => {
  const response = await axios.get<AchievementListResponseMap[T]>(`${achievementEndpointMap[tab]}pending-review/`)
  return Array.isArray(response.data) ? response.data : []
}

export const submitAchievementForReview = async <T extends TabName>(
  tab: T,
  id: number,
): Promise<AchievementRecordMap[T]> => {
  const response = await axios.post<AchievementRecordMap[T]>(`${achievementEndpointMap[tab]}${id}/submit-review/`)
  return response.data
}

export const approveAchievement = async <T extends TabName>(
  tab: T,
  id: number,
  reason?: string,
): Promise<AchievementReviewActionResponse> => {
  const payload = reason?.trim() ? { reason: reason.trim() } : undefined
  const response = await axios.post<AchievementReviewActionResponse>(`${achievementEndpointMap[tab]}${id}/approve/`, payload)
  return response.data
}

export const rejectAchievement = async <T extends TabName>(
  tab: T,
  id: number,
  reason: string,
): Promise<AchievementReviewActionResponse> => {
  const response = await axios.post<AchievementReviewActionResponse>(`${achievementEndpointMap[tab]}${id}/reject/`, {
    reason,
  })
  return response.data
}

export const fetchPendingReviewPapers = async (): Promise<PaperRecord[]> => {
  return fetchPendingReviewAchievements('papers')
}

export const approvePaper = async (paperId: number): Promise<AchievementReviewActionResponse> => {
  return approveAchievement('papers', paperId)
}

export const rejectPaper = async (
  paperId: number,
  reason: string,
): Promise<AchievementReviewActionResponse> => {
  return rejectAchievement('papers', paperId, reason)
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
