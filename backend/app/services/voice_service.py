import logging

from ..core import storage
from ..core.exceptions import (
    DefaultVoiceCannotBeDeletedError,
    DefaultVoiceCannotBeModifiedError,
    NoFieldsToUpdateError,
    VoiceInUseError,
    VoiceNotFoundError,
)
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.voice_repository import voice_repository

logger = logging.getLogger(__name__)


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
        voice = self._voice_repo.get(voice_id)
        if voice is None:
            raise VoiceNotFoundError()
        # 기본 제공(preset) 보이스는 수정 불가
        if voice.get("isPreset"):
            raise DefaultVoiceCannotBeModifiedError()
        if not update_data:
            raise NoFieldsToUpdateError()
        return self._voice_repo.update(voice_id, update_data)

    def delete_voice(self, voice_id: str) -> dict:
        voice = self._voice_repo.get(voice_id)
        if voice is None:
            raise VoiceNotFoundError()
        # 기본 제공(preset) 보이스는 삭제 불가
        if voice.get("isPreset"):
            raise DefaultVoiceCannotBeDeletedError()
        # 캐릭터에 연결돼 있으면 삭제 불가 — 먼저 캐릭터에서 보이스 연결을 해제해야 함.
        if self._character_repo.names_using_voice(voice_id):
            raise VoiceInUseError()
        self._voice_repo.delete(voice_id)
        # 캐릭터 연결은 위에서 차단했으므로(연결 0건) 여기선 나레이션 연결만 해제한다.
        self._story_repo.detach_narrator_voice(voice_id)
        # reference/sample 등 디스크 파일도 함께 정리 (orphan 방지). 실패해도 삭제 응답은 성공.
        self._delete_voice_files(voice_id)
        return {"deleted": True, "voiceId": voice_id}

    @staticmethod
    def _delete_voice_files(voice_id: str) -> None:
        """voices/{voiceId}/ 하위 파일(reference_original/reference/sample) 삭제.

        - storage 추상화 경유: R2 모드면 prefix 하위 객체 일괄 삭제, 로컬이면 폴더 삭제.
        - 없어도 에러 없음. 실패해도 삭제 API 자체는 성공으로 둔다(레코드는 이미 삭제됨).
        """
        try:
            storage.delete_prefix(f"voices/{voice_id}/")
        except Exception as e:  # noqa: BLE001 (파일 정리 실패가 삭제 API 를 막지 않게)
            logger.warning("voice 파일 정리 실패 (voiceId=%s): %s", voice_id, e)


voice_service = VoiceService(voice_repository, character_repository, story_repository)
