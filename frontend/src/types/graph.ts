export type GraphNodeType =
  | 'CenterTeacher'
  | 'Paper'
  | 'Keyword'
  | 'ExternalScholar'
  | 'Project'
  | 'IntellectualProperty'
  | 'TeachingAchievement'
  | 'AcademicService'
  | string

export interface GraphNode {
  id: string
  name: string
  category: number
  symbolSize: number
  nodeType: GraphNodeType
  nodeTypeLabel?: string
  detailLines?: string[]
}

export interface GraphLink {
  source: string
  target: string
  name: string
  relationLabel?: string
  description?: string
}

export interface GraphTopologyMeta {
  source?: string
  fallback_used?: boolean
  node_count?: number
  link_count?: number
  notice?: string
  analysis_level?: string
  calculation_note?: string
  fallback_tip?: string
}

export interface GraphAnalysisRankingItem {
  name: string
  count: number
}

export interface GraphHighlightCard {
  title: string
  value: string
  detail: string
}

export interface GraphTopologyAnalysis {
  top_collaborators: GraphAnalysisRankingItem[]
  top_keywords: GraphAnalysisRankingItem[]
  network_overview: {
    paper_count: number
    collaborator_total: number
    keyword_total: number
  }
  collaboration_overview: {
    paper_count: number
    collaborator_total: number
    collaboration_links: number
    average_collaborators_per_paper: number
    strongest_collaborator: GraphAnalysisRankingItem | null
  }
  collaborator_type_breakdown: {
    internal_count: number
    external_count: number
    internal_ratio: number
    external_ratio: number
    description: string
  }
  theme_hotspots: {
    top_keywords: GraphAnalysisRankingItem[]
    focus_ratio: number
    focus_label: string
    yearly_focus: Array<{ year: number; keywords: GraphAnalysisRankingItem[] }>
    description: string
  }
  highlight_cards: GraphHighlightCard[]
  scope_note: string
  analysis_level: string
  analysis_method_note: string
}

export interface GraphTopologyResponse {
  nodes: GraphNode[]
  links: GraphLink[]
  meta: GraphTopologyMeta
  analysis?: GraphTopologyAnalysis
}
