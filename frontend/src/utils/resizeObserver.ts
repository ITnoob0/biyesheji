export const observeElementsResize = (
  elements: Array<HTMLElement | null | undefined>,
  callback: () => void,
): ResizeObserver | null => {
  if (typeof ResizeObserver === 'undefined') {
    return null
  }

  const observer = new ResizeObserver(() => callback())
  let hasObservedTarget = false

  elements.forEach(element => {
    if (!element) {
      return
    }
    observer.observe(element)
    hasObservedTarget = true
  })

  if (!hasObservedTarget) {
    observer.disconnect()
    return null
  }

  return observer
}
