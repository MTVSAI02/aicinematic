import { create } from 'zustand'

/**
 * 캐릭터 스키마 (백엔드 Character API 기준)
 * {
 *   characterId: string,
 *   name: string,
 *   appearancePrompt: string,
 *   imageUrl: string | null,
 * }
 *
 * 최종 저장소는 백엔드이며, Zustand store 는 프론트 전역 캐시 역할만 한다.
 * 페이지 진입 시 GET /api/characters 로 백엔드 데이터와 동기화한다.
 *
 * 캐릭터 락(locked) / seed / referenceImageUrl / lockProfile 은
 * ComfyUI/AI 파트에서 담당하므로 프론트 store 에서 다루지 않는다.
 */

const useCharacterStore = create((set) => ({
  // 캐릭터 라이브러리 (전역 캐시)
  characters: [],

  // 현재 선택된 캐릭터 ID (락이 아니라 단순 선택 기억용)
  selectedCharacterId: null,

  // ── Actions ──────────────────────────────────

  /** 전체 캐릭터 목록 교체 (GET /api/characters 결과 동기화) */
  setCharacters: (characters) => set({ characters }),

  /** 새 캐릭터 추가 */
  addCharacter: (character) =>
    set((state) => ({
      characters: [...state.characters, character],
    })),

  /** 캐릭터 갱신 (PATCH 결과 반영) */
  updateCharacter: (characterId, updatedCharacter) =>
    set((state) => ({
      characters: state.characters.map((character) =>
        character.characterId === characterId ? updatedCharacter : character
      ),
    })),

  /** 캐릭터 제거. 선택된 캐릭터가 삭제되면 선택도 해제한다. */
  removeCharacter: (characterId) =>
    set((state) => ({
      characters: state.characters.filter(
        (character) => character.characterId !== characterId
      ),
      selectedCharacterId:
        state.selectedCharacterId === characterId
          ? null
          : state.selectedCharacterId,
    })),

  /** 캐릭터 선택 (프론트 전역 선택 상태 기억) */
  selectCharacter: (characterId) => set({ selectedCharacterId: characterId }),

  /** 전체 초기화 */
  reset: () => set({ characters: [], selectedCharacterId: null }),
}))

export default useCharacterStore
