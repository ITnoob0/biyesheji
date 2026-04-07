import type { AchievementQueryState, CoAuthorRecordInput, TabName } from '../../types/achievements'

export const achievementEndpointMap: Record<TabName, string> = {
  papers: '/api/achievements/papers/',
  projects: '/api/achievements/projects/',
  'intellectual-properties': '/api/achievements/intellectual-properties/',
  'teaching-achievements': '/api/achievements/teaching-achievements/',
  'academic-services': '/api/achievements/academic-services/',
}

export const paperImportEndpointMap = {
  bibtexPreview: '/api/achievements/papers/import/bibtex-preview/',
  bibtexRevalidate: '/api/achievements/papers/import/bibtex-revalidate/',
  bibtexConfirm: '/api/achievements/papers/import/bibtex-confirm/',
}

export const paperSummaryEndpoint = '/api/achievements/papers/summary/'
export const paperGovernanceEndpoint = '/api/achievements/papers/governance/'
export const paperPendingReviewEndpoint = '/api/achievements/papers/pending-review/'
export const paperCompareEndpoint = '/api/achievements/papers/compare/'
export const paperExportEndpoint = '/api/achievements/papers/export/'
export const paperRepresentativeBatchEndpoint = '/api/achievements/papers/representative/batch-update/'
export const paperCleanupApplyEndpoint = '/api/achievements/papers/cleanup-apply/'

export const paperTypeOptions = [
  { label: '期刊论文', value: 'JOURNAL' },
  { label: '会议论文', value: 'CONFERENCE' },
]

export const projectLevelOptions = [
  { label: '国家级', value: 'NATIONAL' },
  { label: '省部级', value: 'PROVINCIAL' },
  { label: '企业合作', value: 'ENTERPRISE' },
]

export const projectRoleOptions = [
  { label: '负责人', value: 'PI' },
  { label: '参与人', value: 'CO_PI' },
]

export const ipTypeOptions = [
  { label: '发明专利', value: 'PATENT_INVENTION' },
  { label: '实用新型', value: 'PATENT_UTILITY' },
  { label: '软件著作权', value: 'SOFTWARE_COPYRIGHT' },
]

export const teachingTypeOptions = [
  { label: '学生竞赛', value: 'COMPETITION' },
  { label: '教改项目', value: 'TEACHING_REFORM' },
  { label: '精品课程', value: 'COURSE' },
  { label: '优秀论文指导', value: 'THESIS' },
]

export const serviceTypeOptions = [
  { label: '期刊编委', value: 'EDITOR' },
  { label: '期刊审稿', value: 'REVIEWER' },
  { label: '学术委员会', value: 'COMMITTEE' },
  { label: '特邀报告', value: 'INVITED_TALK' },
]

export const createAchievementStatusMap = (): Record<TabName, boolean> => ({
  papers: false,
  projects: false,
  'intellectual-properties': false,
  'teaching-achievements': false,
  'academic-services': false,
})

export const createAchievementQueryState = (): AchievementQueryState => ({
  papers: {
    search: '',
    paper_type: 'ALL',
    year: 'ALL',
    is_representative: 'ALL',
    sort_by: 'date_desc',
  },
  projects: {
    search: '',
  },
  'intellectual-properties': {
    search: '',
  },
  'teaching-achievements': {
    search: '',
  },
  'academic-services': {
    search: '',
  },
})

export const normalizeAchievementList = <T>(data: unknown): T[] =>
  Array.isArray(data) ? (data as T[]) : []

export const parseCoauthorInput = (raw: string): string[] =>
  parseCoauthorRankInput(raw).map(item => item.name)

export const parseCoauthorRankInput = (raw: string): CoAuthorRecordInput[] => {
  const normalizedRecords: CoAuthorRecordInput[] = []
  const seenNames = new Set<string>()
  const usedRanks = new Set<number>()
  const chunks = raw
    .split(/[\n,，、;；]+/)
    .map(item => item.trim())
    .filter(Boolean)

  for (const chunk of chunks) {
    const isCorresponding = /[*＊]\s*$/.test(chunk)
    const normalizedChunk = chunk.replace(/[*＊]\s*$/, '').trim()
    const [nameRaw, rankRaw] = normalizedChunk.split(/[#＃:：]/).map(part => (part || '').trim())
    const name = nameRaw || ''
    if (!name || seenNames.has(name)) continue

    let authorRank: number | null = null
    if (rankRaw) {
      const parsed = Number(rankRaw)
      if (Number.isFinite(parsed) && parsed >= 1) {
        authorRank = Math.floor(parsed)
      }
    }
    if (authorRank !== null && usedRanks.has(authorRank)) {
      authorRank = null
    }
    if (authorRank !== null) {
      usedRanks.add(authorRank)
    }
    seenNames.add(name)
    normalizedRecords.push({
      name,
      user_id: null,
      is_internal: false,
      order: authorRank,
      author_rank: authorRank,
      is_corresponding: isCorresponding,
    })
    if (normalizedRecords.length >= 20) break
  }

  return normalizedRecords
}

export const paperRepresentativeOptions = [
  { label: '全部记录', value: 'ALL' },
  { label: '仅代表作', value: 'true' },
  { label: '仅非代表作', value: 'false' },
]

export const paperSortOptions = [
  { label: '按时间从新到旧', value: 'date_desc' },
  { label: '按引用次数从高到低', value: 'citation_desc' },
  { label: '按时间从旧到新', value: 'date_asc' },
  { label: '按引用次数从低到高', value: 'citation_asc' },
  { label: '按题目 A-Z', value: 'title_asc' },
  { label: '按题目 Z-A', value: 'title_desc' },
  { label: '按创建时间从新到旧', value: 'created_desc' },
  { label: '代表作优先', value: 'representative_desc' },
  { label: '异常优先处理', value: 'metadata_alerts_desc' },
]
