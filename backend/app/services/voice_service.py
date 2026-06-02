import logging
import shutil

from ..core.config import VOICE_STORAGE_DIR
from ..core.exceptions import (
    DefaultVoiceCannotBeDeletedError,
    DefaultVoiceCannotBeModifiedError,
    NoFieldsToUpdateError,
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
        self._voice_repo.delete(voice_id)
        # 참조 해제(배경 삭제와 동일 정책): 이 voiceId를 쓰던
        # - 캐릭터의 voiceId를 null로
        # - 스토리의 narratorVoiceId를 null로
        self._character_repo.detach_voice(voice_id)
        self._story_repo.detach_narrator_voice(voice_id)
        # reference/sample 등 디스크 파일도 함께 정리 (orphan 방지). 실패해도 삭제 응답은 성공.
        self._delete_voice_files(voice_id)
        return {"deleted": True, "voiceId": voice_id}

    @staticmethod
    def _delete_voice_files(voice_id: str) -> None:
        """storage/voices/{voiceId}/ 폴더(reference/sample) 삭제.

        - 폴더가 이미 없으면 조용히 무시.
        - 권한 등으로 삭제 실패하면 warning 로그만 남기고 삭제 API 자체는 실패시키지 않는다.
        """
        folder = VOICE_STORAGE_DIR / voice_id
        if not folder.exists():
            return
        try:
            shutil.rmtree(folder)
        except OSError as e:  # noqa: BLE001 (권한 등 — 레코드 삭제는 이미 성공)
            logger.warning("voice 파일 정리 실패 (voiceId=%s): %s", voice_id, e)


voice_service = VoiceService(voice_repository, character_repository, story_repository)
