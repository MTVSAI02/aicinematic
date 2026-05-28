import { create } from 'zustand'

/**
 * 캐릭터 스키마
 * {
 *   id: string,
 *   name: string,
 *   tags: string,          // 외모 태그 (프롬프트 빌더 입력값)
 *   image_url: string|null, // 생성된 캐릭터 이미지
 *   locked: boolean,        // IPAdapter 얼굴 락 여부
 * }
 */

const useCharacterStore = create((set) => ({
  // 캐릭터 라이브러리
  characters: [],

  // 씬 편집기에서 현재 선택된 캐릭터 ID
  selectedCharacterId: null,

  // ── Actions ──────────────────────────────────

  /** 새 캐릭터 추가 (POST /characters 응답 후 호출) */
  addCharacter: (character) =>
    set((state) => ({
      characters: [...state.characters, character],
    })),

  /** 캐릭터 이미지 URL 업데이트 (생성 완료 후 폴링 결과 저장) */
  updateCharacterImage: (characterId, imageUrl) =>
    set((state) => ({
      characters: state.characters.map((c) =>
        c.id === characterId ? { ...c, image_url: imageUrl } : c
      ),
    })),

  /** IPAdapter 얼굴 락 상태 토글 */
  toggleLock: (characterId) =>
    set((state) => ({
      characters: state.characters.map((c) =>
        c.id === characterId ? { ...c, locked: !c.locked } : c
      ),
    })),

  /** 씬 편집기에서 캐릭터 선택 */
  selectCharacter: (characterId) =>
    set({ selectedCharacterId: characterId }),

  /** 전체 캐릭터 목록 초기화 (서버에서 받아올 때) */
  setCharacters: (characters) => set({ characters }),

  /** 전체 초기화 */
  reset: () => set({ characters: [], selectedCharacterId: null }),
}))

export default useCharacterStore
