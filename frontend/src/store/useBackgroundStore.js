import { create } from 'zustand'

/**
 * 배경 전역 상태 (캐릭터와 별도 store).
 *
 * 배경은 2단계 구조다:
 *   candidates(임시, candidateId) → 1장 선택 저장 → backgrounds(라이브러리, backgroundId)
 * 씬에는 candidateId 가 아니라 저장된 backgroundId 만 연결한다.
 *
 * 중요: promptInput 과 finalPromptPreview 는 분리한다.
 *   - generateBackground 에 보내는 값은 promptInput (사용자가 수정한 원본 프롬프트)
 *   - finalPromptPreview 는 백엔드가 조립한 finalPrompt 의 화면 표시용 (전송하지 않음)
 */
const useBackgroundStore = create((set) => ({
  // 라이브러리 / 후보
  backgrounds: [],
  candidates: [],

  // 선택 상태
  selectedBackgroundId: null,
  selectedCandidateId: null,

  // Job
  currentJobId: null,

  // 프롬프트 (분리 관리)
  promptInput: '',
  // 백엔드가 finalPrompt에 덧붙이는 고정 suffix(배경 규칙). 추천 응답에서 추출해 보관하고,
  // 미리보기는 항상 "현재 promptInput + suffix"로 실시간 계산한다(stale 방지).
  promptSuffix: '',
  negativePrompt: '',
  sourceText: '',

  // 씬 추천/연결 공용 임시 입력 (나중에 Scene Editor 연결 시 외부에서 주입 가능)
  storyId: '',
  sceneId: '',

  loading: false,
  error: null,

  // ── setters ──────────────────────────────────
  setBackgrounds: (backgrounds) => set({ backgrounds }),
  setCandidates: (candidates) => set({ candidates }),
  setSelectedBackgroundId: (selectedBackgroundId) => set({ selectedBackgroundId }),
  setSelectedCandidateId: (selectedCandidateId) => set({ selectedCandidateId }),
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setPromptInput: (promptInput) => set({ promptInput }),
  setPromptSuffix: (promptSuffix) => set({ promptSuffix }),
  setNegativePrompt: (negativePrompt) => set({ negativePrompt }),
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
  resetCandidates: () => set({ candidates: [], selectedCandidateId: null }),

  reset: () =>
    set({
      backgrounds: [],
      candidates: [],
      selectedBackgroundId: null,
      selectedCandidateId: null,
      currentJobId: null,
      promptInput: '',
      promptSuffix: '',
      negativePrompt: '',
      sourceText: '',
      storyId: '',
      sceneId: '',
      loading: false,
      error: null,
    }),
}))

export default useBackgroundStore
