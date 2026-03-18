export const buildRecommendationSortOptions = () => [
  { value: 'score', label: '按匹配分数' },
  { value: 'deadline', label: '按申报窗口' },
  { value: 'updated', label: '按最近更新' },
]

export const filterRecommendationItems = (items, search, focus) => {
  const normalizedSearch = (search || '').trim().toLowerCase()
  return (Array.isArray(items) ? items : []).filter(item => {
    const matchesSearch =
      !normalizedSearch ||
      [item.title, item.issuing_agency, item.summary]
        .filter(Boolean)
        .some(value => String(value).toLowerCase().includes(normalizedSearch))

    const matchesFocus = !focus || (item.match_category_tags || []).includes(focus)
    return matchesSearch && matchesFocus
  })
}

export const sortRecommendationItems = (items, sortBy) => {
  const list = [...(Array.isArray(items) ? items : [])]
  return list.sort((left, right) => {
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
