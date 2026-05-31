import { create } from 'zustand'

function matchesCharacter(character, characterId) {
  return character.characterId === characterId || character.id === characterId
}

const useCharacterStore = create((set) => ({
  characters: [],
  selectedCharacterId: null,

  setCharacters: (characters) => set({ characters }),

  addCharacter: (character) =>
    set((state) => ({
      characters: [...state.characters, character],
    })),

  updateCharacter: (characterId, updatedCharacter) =>
    set((state) => ({
      characters: state.characters.map((character) =>
        matchesCharacter(character, characterId) ? updatedCharacter : character,
      ),
    })),

  removeCharacter: (characterId) =>
    set((state) => ({
      characters: state.characters.filter(
        (character) => !matchesCharacter(character, characterId),
      ),
      selectedCharacterId:
        state.selectedCharacterId === characterId
          ? null
          : state.selectedCharacterId,
    })),

  selectCharacter: (characterId) => set({ selectedCharacterId: characterId }),

  setCharacterVoiceProfile: (characterId, voiceProfile) =>
    set((state) => ({
      characters: state.characters.map((character) =>
        matchesCharacter(character, characterId)
          ? {
              ...character,
              voiceId: voiceProfile?.voiceId ?? voiceProfile?.id ?? null,
              voice_profile: voiceProfile,
            }
          : character,
      ),
    })),

  reset: () => set({ characters: [], selectedCharacterId: null }),
}))

export default useCharacterStore
