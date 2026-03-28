export const buildRecommendationSortOptions = () => [
  { value: 'score', label: '按匹配分数' },
  { value: 'deadline', label: '按申报窗口' },
  { value: 'updated', label: '按最近更新' },
  { value: 'priority', label: '按关注等级' },
  { value: 'compare_delta', label: '按对比差值' },
]

export const filterRecommendationItems = (items, search, focus, options = {}) => {
  const normalizedSearch = (search || '').trim().toLowerCase()
  const selectedLevel = options.level || ''
  const selectedPriority = options.priority || ''
  const selectedLabel = options.label || ''
  const favoritesOnly = Boolean(options.favoritesOnly)
  const favoriteIds = new Set(options.favoriteIds || [])

  return (Array.isArray(items) ? items : []).filter(item => {
    const matchesSearch =
      !normalizedSearch ||
      [item.title, item.issuing_agency, item.summary]
        .filter(Boolean)
        .some(value => String(value).toLowerCase().includes(normalizedSearch))

    const matchesFocus = !focus || (item.match_category_tags || []).includes(focus)
    const matchesLevel = !selectedLevel || item.guide_level === selectedLevel
    const matchesPriority = !selectedPriority || item.priority_label === selectedPriority
    const matchesLabel = !selectedLabel || (item.recommendation_labels || []).includes(selectedLabel)
    const matchesFavorite = !favoritesOnly || favoriteIds.has(item.id)
    return matchesSearch && matchesFocus && matchesLevel && matchesPriority && matchesLabel && matchesFavorite
  })
}

export const sortRecommendationItems = (items, sortBy) => {
  const list = [...(Array.isArray(items) ? items : [])]
  return list.sort((left, right) => {
    if (sortBy === 'priority') {
      const priorityRank = { 重点关注: 3, 建议关注: 2, 可作备选: 1 }
      return (priorityRank[right.priority_label] || 0) - (priorityRank[left.priority_label] || 0)
    }

    if (sortBy === 'compare_delta') {
      return Math.abs(right.compare_delta || 0) - Math.abs(left.compare_delta || 0)
    }

    if (sortBy === 'deadline') {
      const leftTime = left.application_deadline ? new Date(left.application_deadline).getTime() : Number.MAX_SAFE_INTEGER
      const rightTime = right.application_deadline ? new Date(right.application_deadline).getTime() : Number.MAX_SAFE_INTEGER
      return leftTime - rightTime
    }

    if (sortBy === 'updated') {
      return new Date(right.updated_at || 0).getTime() - new Date(left.updated_at || 0).getTime()
    }

    return (right.recommendation_score || 0) - (left.recommendation_score || 0)
  })
}

export const buildDistributionCards = analysis => {
  if (!analysis) return []

  return [
    {
      label: '推荐结果数',
      value: analysis.recommended_count || 0,
      helper: analysis.teacher_name || '当前教师',
    },
    {
      label: '反馈覆盖率',
      value: `${analysis.response_rate || 0}%`,
      helper: `已反馈 ${analysis.responded_guide_count || 0} 条`,
    },
    {
      label: '计划/已申报',
      value: `${analysis.plan_to_apply_count || 0} / ${analysis.applied_count || 0}`,
      helper: analysis.feedback_record_count ? `累计反馈 ${analysis.feedback_record_count} 条` : '当前尚无反馈历史',
    },
    {
      label: '主要规则档位',
      value: Object.entries(analysis.rule_profile_distribution || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || '暂无',
      helper: analysis.comparison_teacher_name ? `对比 ${analysis.comparison_teacher_name}` : '管理员视角分析',
    },
    {
      label: '已收藏结果',
      value: analysis.favorited_count || 0,
      helper: Object.entries(analysis.feedback_distribution || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || '暂无反馈信号',
    },
    {
      label: '高频标签',
      value: analysis.top_labels?.[0]?.label || '暂无',
      helper: analysis.top_labels?.[0] ? `出现 ${analysis.top_labels[0].count} 次` : '当前暂无标签分布',
    },
  ]
}
