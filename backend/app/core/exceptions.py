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


class NotificationNotFoundError(AppException):
    status_code = 404
    detail = "Notification not found"


class NoFieldsToUpdateError(AppException):
    status_code = 400
    detail = "No fields to update"


class CharacterGenerationFailedError(AppException):
    status_code = 500
    detail = "Character generation failed"


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


class VoiceNotReadyError(AppException):
    """연결하려는 보이스가 아직 ready 가 아님 (pending/processing/failed). voiceType 은 제한하지 않음."""

    status_code = 400
    detail = "이 보이스는 아직 사용할 수 없습니다 (클로닝 완료(ready) 후 연결 가능)."


class VoiceNotConnectedError(AppException):
    """대상(나레이션/캐릭터)에 보이스가 아직 연결되지 않아 잠글 수 없음."""

    status_code = 400
    detail = "먼저 목소리를 연결해주세요."


class VoiceLockTargetNotFoundError(AppException):
    """잠금/해제 대상(targetType/targetId)이 유효하지 않음 (예: 없는 캐릭터)."""

    status_code = 404
    detail = "잠금 대상을 찾을 수 없습니다."


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


class RenderPlanInvalidError(AppException):
    """렌더 플랜이 비어 있거나 렌더링 불가(예: scene 0개)."""

    status_code = 400
    detail = "Render plan is empty or invalid."


class FFmpegNotInstalledError(AppException):
    """ffmpeg 실행 파일을 찾지 못함(env/PATH/번들 모두 없음).

    detail 은 프론트(job.error)에 그대로 노출되므로 사용자용 한국어 문구로 둔다.
    """

    status_code = 500
    detail = "ffmpeg가 설치되어 있지 않아 렌더링할 수 없습니다."


class FFmpegRenderFailedError(AppException):
    status_code = 500
    detail = "Video render (ffmpeg) failed"


class RenderAudioNotReadyError(AppException):
    """렌더 전 음성 검증 실패(미잠금/실패/누락/파일없음). detail 이 프론트에 그대로 노출된다."""

    status_code = 400
    detail = "생성되지 않은 음성이 있습니다. 타임라인 또는 보이스 페이지에서 음성을 다시 확인해 주세요."


class VoiceCloneValidationError(AppException):
    """보이스 클로닝 입력이 잘못됨 (referenceText 비었음, voiceType 잘못 등)."""

    status_code = 400
    detail = "Invalid voice clone request."


class InvalidAudioFileError(AppException):
    """업로드한 오디오 파일이 없거나 허용 확장자(webm/wav/mp3/m4a)가 아님."""

    status_code = 400
    detail = "Invalid audio file (allowed: webm/wav/mp3/m4a)."


class VoiceInUseError(AppException):
    """캐릭터에 연결된 보이스는 삭제 불가 — 먼저 캐릭터에서 보이스 연결을 해제해야 함."""

    status_code = 409
    detail = "연결된 캐릭터가 있어 삭제할 수 없습니다. 먼저 캐릭터에서 보이스 연결을 해제해 주세요."


class VoiceReferenceConversionError(AppException):
    """업로드한 reference 오디오(webm 등)를 wav 로 변환하지 못함(ffmpeg 실패/깨진 파일/빈 결과).

    fallback 으로 원본을 보내면 클론 품질이 깨지므로, 조용히 넘기지 않고 명확히 드러낸다.
    """

    status_code = 400
    detail = "녹음 파일을 변환할 수 없습니다. 다시 녹음해 주세요."


class VoiceCloneFailedError(AppException):
    status_code = 500
    detail = "Voice clone failed"


class AiVoiceServerError(AppException):
    """AI 보이스 클로닝 서버 호출 실패 (미설정/연결/응답). detail 이 job.error 로 노출된다."""

    status_code = 502
    detail = "AI voice clone server request failed"
