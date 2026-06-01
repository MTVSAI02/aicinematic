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
