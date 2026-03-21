export const buildKeywordEvolution = papers => {
  const yearMap = new Map()

  papers.forEach(paper => {
    const year = Number(String(paper.date_acquired || '').slice(0, 4))
    if (!year) return

    const target = yearMap.get(year) || { keywordCounts: new Map(), paperCount: 0 }
    target.paperCount += 1
    ;(paper.keywords || []).forEach(keyword => {
      target.keywordCounts.set(keyword, (target.keywordCounts.get(keyword) || 0) + 1)
    })
    yearMap.set(year, target)
  })

  return [...yearMap.entries()]
    .sort((a, b) => b[0] - a[0])
    .slice(0, 4)
    .map(([year, value]) => ({
      year,
      paperCount: value.paperCount,
      keywords: [...value.keywordCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
        .map(([name, count]) => ({ name, count })),
    }))
}

export const buildThemeFocusSummary = papers => {
  const counts = new Map()

  papers.forEach(paper => {
    ;(paper.keywords || []).forEach(keyword => {
      counts.set(keyword, (counts.get(keyword) || 0) + 1)
    })
  })

  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }))
  const total = sorted.reduce((sum, item) => sum + item.count, 0)
  const topThreeTotal = sorted.slice(0, 3).reduce((sum, item) => sum + item.count, 0)
  const ratio = total ? Number(((topThreeTotal / total) * 100).toFixed(1)) : 0

  if (ratio >= 65) {
    return {
      ratio,
      label: '主题聚焦较强',
      description: '近年关键词主要集中在少数核心主题，适合突出持续深耕方向。',
      topKeywords: sorted.slice(0, 5),
    }
  }

  if (ratio >= 40) {
    return {
      ratio,
      label: '主题布局均衡',
      description: '近年关键词既有核心方向，也保留一定横向延展能力。',
      topKeywords: sorted.slice(0, 5),
    }
  }

  return {
    ratio,
    label: '主题覆盖较广',
    description: '近年关键词分布相对分散，更适合从交叉探索与合作拓展角度理解画像。',
    topKeywords: sorted.slice(0, 5),
  }
}

export const buildDimensionTrendNarrative = trend => {
  if (trend.length < 2) {
    return '当前趋势样本仍较少，后续补充更多年度成果后会更容易观察变化。'
  }

  const latest = trend[trend.length - 1]
  const previous = trend[trend.length - 2]
  const delta = Number((latest.total_score - previous.total_score).toFixed(1))

  if (delta > 0) {
    return `最近一年综合画像较上一年提升 ${delta} 分，说明多成果投入在当前口径下呈上升趋势。`
  }
  if (delta < 0) {
    return `最近一年综合画像较上一年回落 ${Math.abs(delta)} 分，建议结合成果结构和关键词变化一起分析原因。`
  }
  return '最近两年综合画像变化相对平稳，更适合结合结构分布观察能力重心是否发生转移。'
}
