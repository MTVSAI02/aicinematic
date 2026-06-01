import os
from typing import Any

import httpx


TRUE_VALUES = {"1", "true", "yes", "on"}


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def _error_result(payload: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "storyId": payload.get("storyId"),
        "sceneId": payload.get("sceneId"),
        "audios": [
            {
                "audioId": item.get("audioId"),
                "audioUrl": None,
                "durationSec": None,
                "error": message,
            }
            for item in payload.get("items", [])
            if item.get("audioId")
        ],
    }


class TTSAIClient:
    """Backend -> AI/TTS contract client.

    The root TTS_AI_CONTRACT.md defines the payload shape:
    backend sends storyId, sceneId, items(audioId/text/emotion/voiceId...),
    AI returns audioId -> audioUrl/durationSec/error.
    """

    def synthesize_scene(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        ai_tts_url = os.getenv("AI_TTS_URL")
        if ai_tts_url:
            return self._request_remote(ai_tts_url, payload)

        if _enabled(os.getenv("QWEN_TTS_ENABLED")):
            return self._request_local_qwen(payload)

        return None

    def _request_remote(self, base_url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        endpoint = f"{base_url.rstrip('/')}/tts"
        try:
            with httpx.Client(timeout=float(os.getenv("AI_TTS_TIMEOUT_SEC", "120"))) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # noqa: BLE001 - preserve failure on each audio target.
            return _error_result(payload, f"AI/TTS request failed: {exc}")

    def _request_local_qwen(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            from ai.voice.tts_contract import synthesize_scene_tts

            return synthesize_scene_tts(payload)
        except Exception as exc:  # noqa: BLE001 - preserve failure on each audio target.
            return _error_result(payload, f"Local Qwen3-TTS failed: {exc}")


tts_ai_client = TTSAIClient()
