import base64
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx

from ..core.config import (
    AI_REQUEST_HEADERS,
    VOICE_STORAGE_DIR,
    storage_path,
    storage_url,
)
from ..core.exceptions import AiVoiceServerError, VoiceNotFoundError
from ..repositories.voice_repository import voice_repository

PRESET_NARRATOR_VOICE_IDS = (
    "voice_preset_narrator_calm_001",
    "voice_preset_narrator_bright_001",
    "voice_preset_narrator_soft_001",
    "voice_preset_narrator_serious_001",
)

SAMPLE_TEXT = "안녕하세요. 저는 이 목소리로 동화를 들려드릴게요."
_VOICE_SAMPLE_PATH = "/voice-sample"
_TTS_PATH = "/tts"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_dev_snapshot() -> None:
    if os.getenv("SEED_DEV") != "1":
        return
    try:
        from ..core.dev_persist import save_snapshot

        save_snapshot()
    except Exception:  # noqa: BLE001 - dev persistence must not break sample generation.
        pass


def _base_ai_tts_url() -> str:
    base_url = (os.getenv("AI_TTS_URL") or "").strip()
    if not base_url:
        raise AiVoiceServerError("AI_TTS_URL이 설정되어 있지 않습니다. backend/.env를 확인해 주세요.")
    return base_url.rstrip("/")


def _timeout() -> float:
    return float(os.getenv("AI_TTS_TIMEOUT_SEC", "120"))


def _sample_payload(voice: dict) -> dict[str, Any]:
    voice_id = voice.get("voiceId")
    return {
        "voiceId": voice_id,
        "voiceType": voice.get("voiceType") or "narrator",
        "voiceName": voice.get("name"),
        "voicePrompt": voice.get("voicePrompt"),
        "sampleText": SAMPLE_TEXT,
        "text": SAMPLE_TEXT,
        "referenceAudioUrl": None,
        "referenceText": None,
        "emotionPrompt": "Speak in a clear, natural narrator sample voice.",
        "characterPrompt": None,
    }


def _tts_fallback_payload(voice: dict) -> dict[str, Any]:
    voice_id = voice.get("voiceId")
    audio_id = f"sample_{voice_id}"
    item = {
        **_sample_payload(voice),
        "audioId": audio_id,
        "itemIndex": 0,
        "type": "narration",
        "speaker": None,
        "emotion": "calm",
        "emotionLabel": "샘플",
        "text": SAMPLE_TEXT,
        "audioUrl": None,
        "durationSec": None,
        "error": None,
    }
    return {
        "storyId": "voice_sample",
        "sceneId": f"voice_sample_{voice_id}",
        "items": [item],
    }


def _decode_base64(value: str) -> bytes:
    if "," in value and value.split(",", 1)[0].endswith(";base64"):
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value)
    except Exception as exc:  # noqa: BLE001
        raise AiVoiceServerError("AI/TTS 샘플 응답 base64 디코딩에 실패했습니다.") from exc


def _absolute_audio_url(base_url: str, audio_url: str) -> str:
    parsed = urllib.parse.urlparse(audio_url)
    if parsed.scheme in {"http", "https"}:
        return audio_url
    return urllib.parse.urljoin(f"{base_url.rstrip('/')}/", audio_url.lstrip("/"))


def _download_audio_url(client: httpx.Client, base_url: str, audio_url: str) -> bytes:
    target = _absolute_audio_url(base_url, audio_url)
    try:
        response = client.get(target, headers=AI_REQUEST_HEADERS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AiVoiceServerError(f"AI/TTS 샘플 audioUrl 다운로드 실패: {exc}") from exc
    if not response.content:
        raise AiVoiceServerError("AI/TTS 샘플 audioUrl에서 빈 오디오가 내려왔습니다.")
    _ensure_audio_bytes(response.content)
    return response.content


def _is_audio_bytes(data: bytes) -> bool:
    return (
        data.startswith(b"RIFF") and data[8:12] == b"WAVE"
        or data.startswith(b"ID3")
        or data.startswith(b"OggS")
        or data.startswith(b"fLaC")
    )


def _ensure_audio_bytes(data: bytes) -> None:
    if _is_audio_bytes(data):
        return
    prefix = data[:80].decode("utf-8", errors="ignore").replace("\n", " ").strip()
    raise AiVoiceServerError(f"AI/TTS 샘플 응답이 오디오 파일이 아닙니다: {prefix}")


def _json_audio_result(
    body: dict[str, Any],
    *,
    client: httpx.Client,
    base_url: str,
) -> dict[str, Any]:
    if body.get("status") == "failed" or body.get("error"):
        raise AiVoiceServerError(body.get("error") or "AI/TTS sample generation failed")

    source = body
    audios = body.get("audios")
    if isinstance(audios, list) and audios:
        source = audios[0]
        if source.get("error"):
            raise AiVoiceServerError(source.get("error"))

    b64 = (
        source.get("sampleAudioBase64")
        or source.get("audioBase64")
        or body.get("sampleAudioBase64")
        or body.get("audioBase64")
    )
    if b64:
        sample_bytes = _decode_base64(b64)
    else:
        audio_url = (
            source.get("sampleAudioUrl")
            or source.get("audioUrl")
            or body.get("sampleAudioUrl")
            or body.get("audioUrl")
        )
        if not audio_url:
            raise AiVoiceServerError("AI/TTS 샘플 응답에 오디오가 없습니다.")
        sample_bytes = _download_audio_url(client, base_url, audio_url)

    return {
        "sample_bytes": sample_bytes,
        "durationSec": source.get("durationSec") or body.get("durationSec"),
        "provider": source.get("provider") or body.get("provider"),
        "model": source.get("model") or body.get("model"),
    }


def _parse_sample_response(
    response: httpx.Response,
    *,
    client: httpx.Client,
    base_url: str,
) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "").lower()
    if content_type.startswith("audio/") or content_type.startswith("application/octet-stream"):
        _ensure_audio_bytes(response.content)
        return {"sample_bytes": response.content, "durationSec": None, "provider": None, "model": None}

    try:
        body = response.json()
    except Exception as exc:  # noqa: BLE001
        raise AiVoiceServerError("AI/TTS 샘플 응답이 audio 또는 JSON 형식이 아닙니다.") from exc
    if not isinstance(body, dict):
        raise AiVoiceServerError("AI/TTS 샘플 JSON 응답 형식이 올바르지 않습니다.")
    return _json_audio_result(body, client=client, base_url=base_url)


def _request_ai_sample(voice: dict) -> dict[str, Any]:
    base_url = _base_ai_tts_url()
    with httpx.Client(timeout=_timeout(), headers=AI_REQUEST_HEADERS) as client:
        sample_endpoint = f"{base_url}{_VOICE_SAMPLE_PATH}"
        try:
            response = client.post(sample_endpoint, json=_sample_payload(voice))
        except httpx.HTTPError as exc:
            raise AiVoiceServerError(f"AI/TTS 샘플 생성 요청 실패: {exc}") from exc

        if response.status_code not in {404, 405}:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise AiVoiceServerError(f"AI/TTS 샘플 생성 요청 실패: {exc}") from exc
            return _parse_sample_response(response, client=client, base_url=base_url)

        fallback_endpoint = f"{base_url}{_TTS_PATH}"
        try:
            fallback_response = client.post(fallback_endpoint, json=_tts_fallback_payload(voice))
            fallback_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AiVoiceServerError(f"AI/TTS /tts 샘플 fallback 요청 실패: {exc}") from exc
        return _parse_sample_response(fallback_response, client=client, base_url=base_url)


class VoiceSampleService:
    def __init__(self, voice_repo):
        self._voice_repo = voice_repo

    def generate_sample(self, voice_id: str) -> dict:
        voice = self._voice_repo.get(voice_id)
        if voice is None:
            raise VoiceNotFoundError()

        current_url = voice.get("sampleAudioUrl")
        current_path = storage_path(current_url)
        if current_url and current_path and current_path.is_file():
            if _is_audio_bytes(current_path.read_bytes()[:16]):
                return voice
            current_path.unlink(missing_ok=True)

        result = _request_ai_sample(voice)
        sample_bytes = result.get("sample_bytes")
        if not sample_bytes:
            raise AiVoiceServerError("AI/TTS 샘플 응답 오디오가 비어 있습니다.")
        _ensure_audio_bytes(sample_bytes)

        target_dir = VOICE_STORAGE_DIR / voice_id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "sample.wav").write_bytes(sample_bytes)

        sample_url = storage_url("voices", voice_id, "sample.wav")
        updated = self._voice_repo.apply_clone_update(
            voice_id,
            {
                "status": "ready",
                "sampleAudioUrl": sample_url,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "durationSec": result.get("durationSec"),
                "error": None,
                "updatedAt": _now(),
            },
        )
        _persist_dev_snapshot()
        return updated

    def generate_preset_samples(self) -> list[dict]:
        return [self.generate_sample(voice_id) for voice_id in PRESET_NARRATOR_VOICE_IDS]


voice_sample_service = VoiceSampleService(voice_repository)
