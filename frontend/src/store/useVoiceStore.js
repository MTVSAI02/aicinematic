import { create } from 'zustand'
import { getVoiceLocks } from '@/api/stories'

/**
 * 보이스 매핑 페이지 전역 상태 (백엔드 Voice/Story/Character API 기준).
 *
 * - voices: 보이스 라이브러리 (preset narrator + 사용자 character). GET /api/voices 동기화.
 * - story: 선택된 스토리 (scenes / narratorVoiceId 포함). 나레이션 연결 대상.
 * - characters: GET /api/characters 결과. dialogue speaker 와 name 으로 매칭.
 * - selectedTarget: 현재 보이스를 붙일 대상. (voiceType 제한 없음 — status==ready 면 연결)
 *     { type: 'narrator'|'character', name, characterId, targetType, targetId }
 * - voiceLocks: 대상별 잠금/TTS 상태(GET /voice-locks). 연결 가능/잠금 여부 판단에 사용.
 * - selectedVoiceId: (보조) 선택한 보이스 기억용.
 *
 * 최종 저장소는 백엔드이며 이 store 는 전역 캐시 역할. 연결 성공 시 로컬도 갱신해
 * 대상 카드의 "현재 목소리" 표시가 바로 반영되게 한다.
 * provider/model, 실제 클로닝/샘플/합성은 프론트가 다루지 않는다(AI 단계).
 */
const useVoiceStore = create((set, get) => ({
  voices: [],
  story: null,
  characters: [],
  selectedTarget: null,
  selectedVoiceId: null,
  loading: false,
  error: null,
  message: null,

  // ── 대상별 보이스 잠금 상태 (GET /voice-locks 로 동기화) ──
  // voiceLocks: [{targetType,targetId,displayName,imageUrl,matched,voiceId,voiceName,lockStatus,ttsStatus,reason}]
  voiceLocks: [],
  allLocked: false,
  nextStepEnabled: false,

  // ── 보이스 라이브러리 ──────────────────────────
  setVoices: (voices) => set({ voices }),
  addVoice: (voice) => set((state) => ({ voices: [...state.voices, voice] })),
  updateVoice: (voiceId, updated) =>
    set((state) => ({
      voices: state.voices.map((v) => (v.voiceId === voiceId ? updated : v)),
    })),
  removeVoice: (voiceId) =>
    set((state) => ({
      voices: state.voices.filter((v) => v.voiceId !== voiceId),
    })),

  /** 보이스 삭제 시 로컬 참조도 정리 (백엔드 캐스케이드와 동일하게 character.voiceId /
   *  story.narratorVoiceId 를 null 로). 캐릭터 voice 만 삭제 가능하지만 방어적으로 둘 다 처리. */
  detachDeletedVoice: (voiceId) =>
    set((state) => ({
      characters: state.characters.map((c) =>
        c.voiceId === voiceId ? { ...c, voiceId: null } : c
      ),
      story:
        state.story && state.story.narratorVoiceId === voiceId
          ? { ...state.story, narratorVoiceId: null }
          : state.story,
    })),

  // ── 연결 대상 데이터 ──────────────────────────
  setStory: (story) => set({ story }),
  setCharacters: (characters) => set({ characters }),

  // 연결 결과 로컬 반영 (PATCH 성공 후)
  setNarratorVoiceId: (voiceId) =>
    set((state) => ({
      story: state.story ? { ...state.story, narratorVoiceId: voiceId } : state.story,
    })),
  setCharacterVoiceId: (characterId, voiceId) =>
    set((state) => ({
      characters: state.characters.map((c) =>
        c.characterId === characterId ? { ...c, voiceId } : c
      ),
    })),

  // GET /voice-locks 응답 반영
  setVoiceLocks: (data) =>
    set({
      voiceLocks: data?.voiceLocks ?? [],
      allLocked: Boolean(data?.allLocked),
      nextStepEnabled: Boolean(data?.nextStepEnabled),
    }),

  // 현재 story 기준 대상별 잠금 상태 재조회 (연결/잠금/해제 후 호출)
  refreshVoiceLocks: async () => {
    const storyId = get().story?.storyId
    if (!storyId) return
    try {
      const data = await getVoiceLocks(storyId)
      set({
        voiceLocks: data?.voiceLocks ?? [],
        allLocked: Boolean(data?.allLocked),
        nextStepEnabled: Boolean(data?.nextStepEnabled),
      })
    } catch {
      // 일시 오류는 다음 호출/폴링에서 복구
    }
  },

  // ── 선택/상태 ──────────────────────────────────
  setSelectedTarget: (selectedTarget) => set({ selectedTarget }),
  setSelectedVoiceId: (selectedVoiceId) => set({ selectedVoiceId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setMessage: (message) => set({ message }),

  reset: () =>
    set({
      voices: [],
      story: null,
      characters: [],
      selectedTarget: null,
      selectedVoiceId: null,
      loading: false,
      error: null,
      message: null,
      voiceLocks: [],
      allLocked: false,
      nextStepEnabled: false,
    }),
}))

export default useVoiceStore
