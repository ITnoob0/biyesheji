export const buildGraphSourceSummary = meta => {
  const source = (meta?.source || 'mysql').toUpperCase()
  const isFallback = Boolean(meta?.fallback_used)

  return {
    title: isFallback ? 'MySQL 回退链路' : 'Neo4j 实时图谱',
    source,
    notice: meta?.notice || '当前图谱按照后端返回结果进行展示。',
  }
}
