export const upsertAchievementRecord = (records, nextRecord) => {
  const list = Array.isArray(records) ? [...records] : []
  const index = list.findIndex(item => item?.id === nextRecord?.id)

  if (index >= 0) {
    list[index] = nextRecord
    return list
  }

  return [nextRecord, ...list]
}

export const removeAchievementRecord = (records, recordId) => {
  return (Array.isArray(records) ? records : []).filter(item => item?.id !== recordId)
}
