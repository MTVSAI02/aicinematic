import { create } from 'zustand'

/**
 * 배경 전역 상태 (캐릭터와 별도 store).
 *
 * 배경은 **1장 생성 → 라이브러리 자동 저장** 구조다(후보/선택 단계 없음).
 *   generateBackground → Job 완료 시 백엔드가 라이브러리에 저장 → 목록(backgrounds) 갱신.
 * 씬에는 저장된 backgroundId 만 연결한다.
 *
 * 중요: promptInput 과 finalPromptPreview 는 분리한다.
 *   - generateBackground 에 보내는 값은 promptInput (사용자가 수정한 원본 프롬프트)
 *   - finalPromptPreview 는 백엔드가 조립한 finalPrompt 의 화면 표시용 (전송하지 않음)
 */
const useBackgroundStore = create((set) => ({
  // 라이브러리
  backgrounds: [],

  // 선택 상태
  selectedBackgroundId: null,

  // Job
  currentJobId: null,

  // 프롬프트 (분리 관리)
  promptInput: '',
  // 백엔드가 finalPrompt에 덧붙이는 고정 suffix(배경 규칙). 추천 응답에서 추출해 보관하고,
  // 미리보기는 항상 "현재 promptInput + suffix"로 실시간 계산한다(stale 방지).
  promptSuffix: '',
  sourceText: '',

  // 씬 추천/연결 공용 임시 입력 (나중에 Scene Editor 연결 시 외부에서 주입 가능)
  storyId: '',
  sceneId: '',

  loading: false,
  error: null,

  // ── setters ──────────────────────────────────
  setBackgrounds: (backgrounds) => set({ backgrounds }),
  setSelectedBackgroundId: (selectedBackgroundId) => set({ selectedBackgroundId }),
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setPromptInput: (promptInput) => set({ promptInput }),
  setPromptSuffix: (promptSuffix) => set({ promptSuffix }),
  setSourceText: (sourceText) => set({ sourceText }),
  setStoryId: (storyId) => set({ storyId }),
  setSceneId: (sceneId) => set({ sceneId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  // ── library mutations ────────────────────────
  addBackground: (background) =>
    set((state) => ({ backgrounds: [...state.backgrounds, background] })),

  updateBackground: (backgroundId, updatedBackground) =>
    set((state) => ({
      backgrounds: state.backgrounds.map((b) =>
        b.backgroundId === backgroundId ? updatedBackground : b
      ),
    })),

  removeBackground: (backgroundId) =>
    set((state) => ({
      backgrounds: state.backgrounds.filter((b) => b.backgroundId !== backgroundId),
      selectedBackgroundId:
        state.selectedBackgroundId === backgroundId ? null : state.selectedBackgroundId,
    })),

  // ── resets ───────────────────────────────────
  reset: () =>
    set({
      backgrounds: [],
      selectedBackgroundId: null,
      currentJobId: null,
      promptInput: '',
      promptSuffix: '',
      sourceText: '',
      storyId: '',
      sceneId: '',
      loading: false,
      error: null,
    }),
}))

export default useBackgroundStore
