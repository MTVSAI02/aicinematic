import { create } from 'zustand'

/**
 * 씬 스키마 (RULES.md 단일 계약 기준)
 *
 * SceneSegment: { type: 'narration'|'dialogue', speaker: string|null, text: string }
 * Scene: {
 *   id: string, order: number, duration: number,
 *   segments: SceneSegment[],
 *   background_tag: string|null,
 *   character_id: string|null,
 *   image_url: string|null,
 *   audio_url: string|null,
 * }
 */

const useStoryStore = create((set) => ({
  // 현재 스토리
  storyId: null,
  storyTitle: '',
  storyText: '',

  // 파싱된 씬 목록 (백엔드 응답 기준: sceneId, order, items)
  scenes: [],

  // ── Actions ──────────────────────────────────

  setStoryText: (text) => set({ storyText: text }),

  setStoryId: (id) => set({ storyId: id }),

  setStoryTitle: (title) => set({ storyTitle: title }),

  setScenes: (scenes) => set({ scenes }),

  /** 특정 씬의 duration 업데이트 (타임라인에서 사용) */
  updateSceneDuration: (sceneId, duration) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.sceneId === sceneId ? { ...s, duration } : s
      ),
    })),

  /** 특정 씬에 캐릭터 배정 (씬 편집기에서 사용) */
  assignCharacter: (sceneId, characterId) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.sceneId === sceneId ? { ...s, character_id: characterId } : s
      ),
    })),

  /** 특정 씬에 생성된 이미지 URL 저장 */
  setSceneImageUrl: (sceneId, imageUrl) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.sceneId === sceneId ? { ...s, image_url: imageUrl } : s
      ),
    })),

  /** 특정 씬에 음성 URL 저장 */
  setSceneAudioUrl: (sceneId, audioUrl) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.sceneId === sceneId ? { ...s, audio_url: audioUrl } : s
      ),
    })),

  /** 전체 초기화 (새 프로젝트 시작 시) */
  reset: () =>
    set({ storyId: null, storyTitle: '', storyText: '', scenes: [] }),
}))

export default useStoryStore
