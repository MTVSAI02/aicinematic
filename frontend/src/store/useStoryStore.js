import { create } from 'zustand'
import { persist } from 'zustand/middleware'

function matchesScene(scene, sceneId) {
  return scene.sceneId === sceneId || scene.id === sceneId
}

function getDuration(scene) {
  return scene.duration ?? scene.durationSec ?? 1
}

// 새로고침 후에도 사용자가 고른 스토리를 유지하기 위해 storyId/storyTitle 만 localStorage 에 persist.
// scenes 는 persist 하지 않는다 — 새로고침 후 백엔드에서 다시 조회해야 최신과 일치한다(App.jsx).
const useStoryStore = create(
  persist(
    (set) => ({
      storyId: null,
      storyTitle: '',
      storyText: '',
      scenes: [],

  setStoryText: (text) => set({ storyText: text }),

  setStoryId: (id) => set({ storyId: id }),

  setStoryTitle: (title) => set({ storyTitle: title }),

  setScenes: (scenes) => set({ scenes: Array.isArray(scenes) ? scenes : [] }),

  updateSceneDuration: (sceneId, duration) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId) ? { ...scene, duration } : scene,
      ),
    })),

  setSceneAudioMeta: (sceneId, audioUrl, audioDurationSec, audioItems = []) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId)
          ? {
              ...scene,
              audioUrl,
              audio_url: audioUrl,
              audioDurationSec,
              audio_duration_sec: audioDurationSec,
              audioItems,
              duration: Math.max(
                getDuration(scene),
                audioDurationSec ? audioDurationSec + 0.5 : 1,
              ),
            }
          : scene,
      ),
    })),

  assignCharacter: (sceneId, characterId) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId)
          ? { ...scene, characterId, character_id: characterId }
          : scene,
      ),
    })),

  setSceneImageUrl: (sceneId, imageUrl) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId)
          ? { ...scene, imageUrl, image_url: imageUrl }
          : scene,
      ),
    })),

  setSceneAudioUrl: (sceneId, audioUrl) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId)
          ? { ...scene, audioUrl, audio_url: audioUrl }
          : scene,
      ),
    })),

      reset: () => set({ storyId: null, storyTitle: '', storyText: '', scenes: [] }),
    }),
    {
      name: 'mongle-story-store',
      // storyId/storyTitle 만 저장. scenes/storyText 는 새로고침 시 백엔드에서 재조회.
      partialize: (state) => ({ storyId: state.storyId, storyTitle: state.storyTitle }),
    },
  ),
)

export default useStoryStore
