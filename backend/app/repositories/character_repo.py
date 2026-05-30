class CharacterRepository:
    """DB 대신 메모리 dict에 캐릭터를 저장하는 Mock Repository.

    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._characters: dict = {}
        self._counter: int = 0

    def save(self, character_data: dict) -> dict:
        self._counter += 1
        character_id = f"char_mock_{self._counter:03d}"
        saved = {
            "characterId": character_id,
            "name": character_data.get("name"),
            "appearancePrompt": character_data.get("appearancePrompt"),
            "imageUrl": character_data.get("imageUrl"),
            "voiceId": character_data.get("voiceId"),  # 보이스 라이브러리 참조 (없으면 None)
        }
        self._characters[character_id] = saved
        return saved

    def list(self) -> list[dict]:
        return list(self._characters.values())

    def get(self, character_id: str) -> dict | None:
        return self._characters.get(character_id)

    def update(self, character_id: str, update_data: dict) -> dict | None:
        character = self._characters.get(character_id)
        if not character:
            return None
        # update_data는 라우터에서 exclude_unset으로 만든 dict이므로
        # "명시적으로 전달된 필드"만 들어 있다.
        # - name / appearancePrompt: NOT NULL 성격 → None(명시적 null)은 무시한다.
        # - imageUrl: nullable → 명시적 null이면 값을 초기화(None)한다.
        for field in ("name", "appearancePrompt"):
            if field in update_data and update_data[field] is not None:
                character[field] = update_data[field]
        if "imageUrl" in update_data:
            character["imageUrl"] = update_data["imageUrl"]
        return character

    def set_voice(self, character_id: str, voice_id: str | None) -> dict | None:
        """캐릭터에 voiceId를 연결/해제한다. (None이면 해제)"""
        character = self._characters.get(character_id)
        if not character:
            return None
        character["voiceId"] = voice_id
        return character

    def detach_voice(self, voice_id: str) -> int:
        """해당 voiceId를 참조하던 모든 캐릭터의 voiceId를 None으로 만든다. (보이스 삭제 시)"""
        count = 0
        for character in self._characters.values():
            if character.get("voiceId") == voice_id:
                character["voiceId"] = None
                count += 1
        return count

    def delete(self, character_id: str) -> bool:
        if character_id in self._characters:
            del self._characters[character_id]
            return True
        return False


character_repository = CharacterRepository()
