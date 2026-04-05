const normalizeToken = value => String(value || '').trim().toLowerCase().replace(/[\W_]+/g, '')

const normalizeDuplicateSignature = (title, journalName, year) =>
  [normalizeToken(title), normalizeToken(journalName), normalizeToken(year)].filter(Boolean).join('::')

export const buildPaperDuplicateWarnings = (form, papers, editingId) => {
  const warnings = []
  const candidates = papers.filter(item => item.id !== editingId)
  const normalizedDoi = String(form.doi || '').trim().toLowerCase()

  if (normalizedDoi && candidates.some(item => String(item.doi || '').trim().toLowerCase() === normalizedDoi)) {
    warnings.push('当前列表中已存在相同 DOI 的论文，建议先核对是否重复录入。')
  }

  const year = String(form.date_acquired || '').slice(0, 4)
  const signature = normalizeDuplicateSignature(form.title, form.journal_name, year)
  if (
    signature &&
    candidates.some(item => normalizeDuplicateSignature(item.title, item.journal_name, String(item.publication_year || '')) === signature)
  ) {
    warnings.push('当前列表中已存在题目、期刊/会议与年份高度相近的论文，建议确认是否为同一成果。')
  }

  return warnings
}

export const buildPaperMetadataHints = form => {
  const hints = []

  if (!String(form.doi || '').trim()) {
    hints.push('建议补充 DOI，便于后续去重、检索和画像联动。')
  }
  if (!String(form.pages || '').trim()) {
    hints.push('建议补充页码范围，方便后续成果核验。')
  }
  if (!String(form.source_url || '').trim()) {
    hints.push('建议补充来源链接，便于回溯原始成果页面。')
  }

  return hints
}

export const buildPaperYearOptions = summary => {
  const options = (summary?.yearly_distribution || []).map(item => ({
    label: `${item.year} 年`,
    value: String(item.year),
  }))

  return [
    { label: '全部年份', value: 'ALL' },
    { label: '近一年', value: 'RECENT_1' },
    { label: '近三年', value: 'RECENT_3' },
    { label: '近五年', value: 'RECENT_5' },
    ...options,
  ]
}

export const buildImportFeedbackLines = payload => {
  const lines = [
    `成功导入 ${payload.imported_count} 条`,
    `重复跳过 ${payload.skipped_count} 条`,
    `写入失败 ${payload.failed_count} 条`,
  ]

  if (payload.classified_counts) {
    const classifiedSummary = Object.entries(payload.classified_counts)
      .map(([key, value]) => `${key}: ${value}`)
      .join(' / ')
    if (classifiedSummary) {
      lines.push(`分类结果：${classifiedSummary}`)
    }
  }

  const firstSkipped = payload.skipped_entries[0]
  if (firstSkipped?.issue_summary) {
    lines.push(`首条跳过原因：${firstSkipped.issue_summary}`)
  }

  const firstFailed = payload.failed_entries[0]
  if (firstFailed?.issue_summary) {
    lines.push(`首条失败原因：${firstFailed.issue_summary}`)
  }

  return lines
}
