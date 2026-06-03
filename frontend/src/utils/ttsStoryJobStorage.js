const STORAGE_KEY = 'aicinematic.ttsStoryJob'

export function loadTtsStoryJob(storyId) {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const job = JSON.parse(raw)
    if (storyId && job.storyId !== storyId) return null
    return job
  } catch {
    return null
  }
}

export function saveTtsStoryJob(job) {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      ...job,
      updatedAt: new Date().toISOString(),
    }),
  )
}

export function clearTtsStoryJob(storyId) {
  const job = loadTtsStoryJob()
  if (!job || (storyId && job.storyId !== storyId)) return
  window.localStorage.removeItem(STORAGE_KEY)
}
