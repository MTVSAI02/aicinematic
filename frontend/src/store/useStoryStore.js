import { create } from 'zustand'

function matchesScene(scene, sceneId) {
  return scene.sceneId === sceneId || scene.id === sceneId
}

function getDuration(scene) {
  return scene.duration ?? scene.durationSec ?? 1
}

const useStoryStore = create((set) => ({
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

  setSceneAudioMeta: (sceneId, audioUrl, audioDurationSec) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        matchesScene(scene, sceneId)
          ? {
              ...scene,
              audioUrl,
              audio_url: audioUrl,
              audioDurationSec,
              audio_duration_sec: audioDurationSec,
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
}))

export default useStoryStore
