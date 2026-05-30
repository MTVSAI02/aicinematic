from ..core.exceptions import NoFieldsToUpdateError, VoiceNotFoundError
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository


class VoiceService:
    """보이스 라이브러리(재사용 자산) CRUD.

    실제 클로닝/합성은 AI/TTS 파트(김도연)가 담당하고, 여기서는 voiceId 발급/메타 관리만 한다.
    """

    def __init__(self, voice_repo, character_repo, story_repo):
        self._voice_repo = voice_repo
        self._character_repo = character_repo
        self._story_repo = story_repo

    def create_voice(self, voice_data: dict) -> dict:
        return self._voice_repo.save(voice_data)

    def list_voices(self) -> list[dict]:
        return self._voice_repo.list()

    def get_voice(self, voice_id: str) -> dict:
        voice = self._voice_repo.get(voice_id)
        if voice is None:
            raise VoiceNotFoundError()
        return voice

    def update_voice(self, voice_id: str, update_data: dict) -> dict:
        if not update_data:
            raise NoFieldsToUpdateError()
        updated = self._voice_repo.update(voice_id, update_data)
        if updated is None:
            raise VoiceNotFoundError()
        return updated

    def delete_voice(self, voice_id: str) -> dict:
        if not self._voice_repo.delete(voice_id):
            raise VoiceNotFoundError()
        # 참조 해제(배경 삭제와 동일 정책): 이 voiceId를 쓰던
        # - 캐릭터의 voiceId를 null로
        # - 스토리의 narratorVoiceId를 null로
        self._character_repo.detach_voice(voice_id)
        self._story_repo.detach_narrator_voice(voice_id)
        return {"deleted": True, "voiceId": voice_id}


voice_service = VoiceService(voice_repository, character_repository, story_repository)
