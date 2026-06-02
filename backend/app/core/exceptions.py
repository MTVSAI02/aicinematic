class AppException(Exception):
    """애플리케이션 공통 예외 베이스.

    각 예외는 HTTP 상태 코드와 detail 메시지를 가지며,
    main.py에 등록된 글로벌 핸들러가 이를 HTTP 응답으로 변환한다.
    """

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class CharacterNotFoundError(AppException):
    status_code = 404
    detail = "Character not found"


class JobNotFoundError(AppException):
    status_code = 404
    detail = "Job not found"


class NoFieldsToUpdateError(AppException):
    status_code = 400
    detail = "No fields to update"


class CharacterGenerationFailedError(AppException):
    status_code = 500
    detail = "Character generation failed"


class BackgroundCandidateNotFoundError(AppException):
    status_code = 404
    detail = "Background candidate not found"


class BackgroundNotFoundError(AppException):
    status_code = 404
    detail = "Background not found"


class BackgroundGenerationFailedError(AppException):
    status_code = 500
    detail = "Background generation failed"


class StoryNotFoundError(AppException):
    status_code = 404
    detail = "Story not found"


class SceneNotFoundError(AppException):
    status_code = 404
    detail = "Scene not found"


class TimelineValidationError(AppException):
    """타임라인 PATCH 요청이 story의 scene 집합과 맞지 않을 때 (전체 목록 누락/초과/중복)."""

    status_code = 400
    detail = "Timeline request must include exactly all scenes of the story (once each)."


class CueTimingValidationError(AppException):
    """자막 cue 타이밍이 잘못됐을 때 (씬에 없는 cueOrder / cueOrder 중복 / 씬 duration 초과)."""

    status_code = 400
    detail = "Invalid cue timing: cueOrder must exist in the scene, be unique, and fit within the scene duration."


class TTSGenerationFailedError(AppException):
    status_code = 500
    detail = "TTS generation failed"


class TTSAudioNotFoundError(AppException):
    status_code = 404
    detail = "TTS audio not found"


class EmptySceneItemsError(AppException):
    status_code = 400
    detail = "Scene has no items to generate TTS"


class VoiceNotFoundError(AppException):
    status_code = 404
    detail = "Voice not found"


class DefaultVoiceCannotBeModifiedError(AppException):
    status_code = 400
    detail = "Default voice cannot be modified."


class DefaultVoiceCannotBeDeletedError(AppException):
    status_code = 400
    detail = "Default voice cannot be deleted."


class InvalidNarratorVoiceError(AppException):
    status_code = 400
    detail = "Only a narrator-type voice can be connected as narrator."


class InvalidCharacterVoiceError(AppException):
    status_code = 400
    detail = 'Character voice must have voiceType="character".'


class AIServerError(AppException):
    """우리 AI FastAPI 서버 호출 실패 (연결/설정/응답).

    비동기 Job 안에서 발생하면 job_manager가 str(exc)=detail 을 job.error에 남긴다.
    (mock fallback 없이 실패를 그대로 드러내 디버깅이 쉽도록 한다.)
    """

    status_code = 502
    detail = "AI server request failed"


class CharacterPoseSourceMissingError(AppException):
    """포즈 생성용 원본 경로(aiImagePath)가 없는 캐릭터 (예: 기능 추가 전 생성된 캐릭터)."""

    status_code = 400
    detail = "이 캐릭터는 포즈 생성용 원본 경로가 없어 다시 생성이 필요합니다."


class PoseGenerationFailedError(AppException):
    status_code = 502
    detail = "Character pose generation failed"


class CharacterPoseNotFoundError(AppException):
    status_code = 404
    detail = "Character pose not found"
