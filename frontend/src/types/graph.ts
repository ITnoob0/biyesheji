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
  highlight_cards: GraphHighlightCard[]
  scope_note: string
}

export interface GraphTopologyResponse {
  nodes: GraphNode[]
  links: GraphLink[]
  meta: GraphTopologyMeta
  analysis?: GraphTopologyAnalysis
}
