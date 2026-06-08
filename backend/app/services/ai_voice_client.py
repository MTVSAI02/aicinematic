"""AI 보이스 클로닝 서버 호출 (multipart 업로드).

- 백엔드가 저장한 reference 오디오 **바이트를 multipart 로 업로드**한다(원격 AI 가 우리 파일시스템을 못 읽으므로 경로 전달 X).
- 응답은 (1) 오디오 바이트 직접, 또는 (2) JSON(base64 sample) 둘 다 방어적으로 처리한다.
- 주소는 .env 의 AI_VOICE_CLONE_URL (하드코딩 금지). 미설정/실패는 AiVoiceServerError 로 그대로 드러낸다(mock fallback 없음).
"""

import base64
import os

import httpx

from ..core.config import AI_REQUEST_HEADERS, AI_VOICE_CLONE_URL
from ..core.exceptions import AiVoiceServerError

_MIME = {"webm": "audio/webm", "wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4"}
# 클론은 GPU 추론이라 길어질 수 있다(TTS=900s 와 균형). 120s 는 너무 짧아 단건도 끊겼다.
# 직렬 큐(job_manager)로 동시 요청은 막되, 단건 자체 여유도 확보.
_TIMEOUT = float(os.getenv("AI_VOICE_CLONE_TIMEOUT_SEC", "600"))
_DEFAULT_PROVIDER = "qwen"
_DEFAULT_MODEL = "Qwen3-TTS-12Hz-0.6B-Base"
_SAMPLE_TEXT = "이 목소리는 동화 속 캐릭터 대사에 사용됩니다."


def clone_voice(
    *,
    voice_id: str,
    voice_type: str,
    character_id: str | None,
    reference_text: str,
    voice_prompt: str | None,
    audio_bytes: bytes,
    audio_ext: str,
) -> dict:
    """AI 서버에 reference 오디오 + 메타를 multipart 로 보내고 sample 오디오를 받는다.

    반환: {"sample_bytes": bytes, "provider": str, "model": str, "durationSec": float|None}
    """
    url = (os.getenv("AI_VOICE_CLONE_URL") or AI_VOICE_CLONE_URL or "").strip()
    if not url:
        raise AiVoiceServerError("AI_VOICE_CLONE_URL 이 설정되지 않았습니다 (.env 확인).")

    mime = _MIME.get(audio_ext, "application/octet-stream")
    files = {"audioFile": (f"reference.{audio_ext}", audio_bytes, mime)}
    data = {
        "voiceId": voice_id,
        "voiceType": voice_type,
        "characterId": character_id or "",
        "referenceText": reference_text,
        "sampleText": _SAMPLE_TEXT,
        "voicePrompt": voice_prompt or "",
        "language": "Korean",
        "provider": _DEFAULT_PROVIDER,
        "model": _DEFAULT_MODEL,
    }
    try:
        resp = httpx.post(url, data=data, files=files, headers=AI_REQUEST_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise AiVoiceServerError(f"AI 보이스 클로닝 요청 실패: {e}") from e

    ctype = resp.headers.get("content-type", "")
    # (1) 오디오 바이트 직접 응답
    if ctype.startswith("audio/") or ctype == "application/octet-stream":
        return {"sample_bytes": resp.content, "provider": _DEFAULT_PROVIDER, "model": _DEFAULT_MODEL, "durationSec": None}

    # (2) JSON 응답
    try:
        body = resp.json()
    except Exception as e:  # noqa: BLE001
        raise AiVoiceServerError("AI 응답을 해석할 수 없습니다 (오디오/JSON 아님).") from e
    if body.get("status") == "failed" or body.get("error"):
        raise AiVoiceServerError(body.get("error") or "AI voice clone failed")
    b64 = body.get("sampleAudioBase64") or body.get("audioBase64")
    if not b64:
        raise AiVoiceServerError("AI 응답에 sample 오디오(base64)가 없습니다.")
    try:
        sample = base64.b64decode(b64)
    except Exception as e:  # noqa: BLE001
        raise AiVoiceServerError("AI 응답 base64 디코딩 실패.") from e
    return {
        "sample_bytes": sample,
        "provider": body.get("provider") or _DEFAULT_PROVIDER,
        "model": body.get("model") or _DEFAULT_MODEL,
        "durationSec": body.get("durationSec"),
    }
