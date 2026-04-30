import axios from 'axios'
import type {
  RuleAchievementEntryConfigResponse,
  RuleAchievementRecord,
  RuleAchievementScorePreview,
  RuleAchievementWorkflowHistory,
} from '../../types/ruleAchievements'

const baseEndpoint = '/api/achievements/rule-achievements/'

export const fetchRuleAchievementEntryConfig = async () => {
  const { data } = await axios.get<RuleAchievementEntryConfigResponse>(`${baseEndpoint}entry-config/`)
  return data
}

export const fetchRuleAchievements = async (params?: Record<string, string | number | undefined>) => {
  const { data } = await axios.get<RuleAchievementRecord[]>(baseEndpoint, { params })
  return Array.isArray(data) ? data : []
}

export const previewRuleAchievementScore = async (payload: Record<string, unknown>) => {
  const { data } = await axios.post<RuleAchievementScorePreview>(`${baseEndpoint}preview-score/`, payload)
  return data
}

export const createRuleAchievement = async (payload: FormData) => {
  const { data } = await axios.post<RuleAchievementRecord>(baseEndpoint, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const updateRuleAchievement = async (id: number, payload: FormData) => {
  const { data } = await axios.patch<RuleAchievementRecord>(`${baseEndpoint}${id}/`, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const deleteRuleAchievement = async (id: number) => {
  await axios.delete(`${baseEndpoint}${id}/`)
}

export const fetchPendingRuleAchievements = async () => {
  const { data } = await axios.get<RuleAchievementRecord[]>(`${baseEndpoint}pending-review/`)
  return Array.isArray(data) ? data : []
}

export const approveRuleAchievement = async (id: number, finalScore: number | string) => {
  const { data } = await axios.post<RuleAchievementRecord>(`${baseEndpoint}${id}/approve/`, {
    final_score: finalScore,
  })
  return data
}

export const rejectRuleAchievement = async (id: number, reason: string) => {
  const { data } = await axios.post<RuleAchievementRecord>(`${baseEndpoint}${id}/reject/`, { reason })
  return data
}

export const fetchRuleAchievementWorkflow = async (id: number) => {
  const { data } = await axios.get<RuleAchievementWorkflowHistory>(`${baseEndpoint}${id}/workflow-logs/`)
  return data
}
