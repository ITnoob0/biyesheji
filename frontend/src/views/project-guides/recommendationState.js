const STORAGE_KEY = 'project-guide-recommendation-flags'

const readStore = () => {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

const writeStore = store => {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store))
}

export const loadFavoriteGuideIds = teacherId => {
  const store = readStore()
  const items = store[String(teacherId)] || []
  return Array.isArray(items) ? items : []
}

export const toggleFavoriteGuideId = (teacherId, guideId) => {
  const store = readStore()
  const key = String(teacherId)
  const current = new Set(loadFavoriteGuideIds(teacherId))

  if (current.has(guideId)) {
    current.delete(guideId)
  } else {
    current.add(guideId)
  }

  store[key] = [...current]
  writeStore(store)
  return store[key]
}
