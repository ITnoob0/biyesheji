export const buildGraphSourceSummary = meta => {
  const source = (meta?.source || 'mysql').toUpperCase()
  const isFallback = Boolean(meta?.fallback_used)

  return {
    title: isFallback ? 'MySQL 回退链路' : 'Neo4j 实时图谱',
    source,
    notice: meta?.notice || '当前图谱按照后端返回结果进行展示。',
    badge: isFallback ? '已降级' : '实时图谱',
    sourceScopeNote: meta?.source_scope_note || '当前图谱覆盖教师、成果、合作关系和研究主题等轻量节点。',
    degradationNote:
      meta?.degradation_note ||
      (isFallback ? '当前已进入 MySQL 回退链路，只保留主体展示与轻量分析。' : '当前已使用 Neo4j 增强图谱展示。'),
    interactionNote: meta?.interaction_note || '当前节点交互和路径说明只基于已加载子图解释。',
    calculationNote: meta?.calculation_note || '当前图分析按后端返回的轻量统计口径生成。',
    fallbackTip:
      meta?.fallback_tip ||
      (isFallback
        ? '当前已使用 MySQL 关系数据继续展示图谱主体与轻量分析。'
        : '若 Neo4j 不可用，系统会自动回退到 MySQL 关系数据。'),
  }
}
