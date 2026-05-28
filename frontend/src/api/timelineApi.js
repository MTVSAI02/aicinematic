export async function updateSceneDuration({ storyId, sceneId, durationSec }) {
  if (!storyId || !sceneId) {
    throw new Error('storyId와 sceneId가 필요합니다.')
  }

  await new Promise((resolve) => setTimeout(resolve, 250))

  return {
    storyId,
    sceneId,
    durationSec,
  }
}
