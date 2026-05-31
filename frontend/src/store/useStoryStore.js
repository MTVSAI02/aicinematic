import { create } from 'zustand'

/**
 * 씬 스키마 (백엔드 Story Parse 응답 기준)
 *
 * StoryItem: { type: 'narration'|'dialogue', speaker: string|null, text: string,
 *              emotion: string, emotionLabel: string }
 * Scene: { sceneId: string, order: number, backgroundId: string|null, items: StoryItem[] }
 *
 * duration 은 백엔드 응답에 없고, 타임라인에서 사용자가 조절하는 프론트 전용 필드다
 * (updateSceneDuration 으로 scene 에 얹는다. 미설정 씬은 화면에서 기본값으로 표시).
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

  /** 특정 씬의 duration 업데이트 (타임라인 전용 프론트 필드) */
  updateSceneDuration: (sceneId, duration) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.sceneId === sceneId ? { ...s, duration } : s
      ),
    })),

  /** 전체 초기화 (새 프로젝트 시작 시) */
  reset: () =>
    set({ storyId: null, storyTitle: '', storyText: '', scenes: [] }),
}))

export default useStoryStore
