from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.voice.qwen3_runtime import DEFAULT_OUTPUT_DIR
from ai.voice.tts import generate_tts


QWEN_SPEAKER_BY_VOICE_ID = {
    "voice_preset_narrator_calm_001": "sohee",
    "voice_preset_narrator_bright_001": "serena",
    "voice_preset_narrator_soft_001": "vivian",
    "voice_preset_narrator_serious_001": "ryan",
}


def _storage_url_for(path: str) -> str:
    storage_root = DEFAULT_OUTPUT_DIR.parent.resolve()
    audio_path = Path(path).resolve()
    relative_path = audio_path.relative_to(storage_root)
    return f"/storage/{relative_path.as_posix()}"


def _instruction_for(item: dict[str, Any]) -> str | None:
    instructions = []
    voice_prompt = item.get("voicePrompt")
    voice_name = item.get("voiceName")
    emotion = item.get("emotion")
    emotion_label = item.get("emotionLabel")

    if voice_prompt:
        instructions.append(f"Voice style: {voice_prompt}")
    elif voice_name:
        instructions.append(f"Voice style: {voice_name}")

    if emotion or emotion_label:
        instructions.append(f"Emotion: {emotion or emotion_label}")

    if not instructions:
        return None
    return ". ".join(instructions)


def _speaker_for(item: dict[str, Any]) -> str:
    voice_id = item.get("voiceId")
    return QWEN_SPEAKER_BY_VOICE_ID.get(voice_id, "sohee")


def synthesize_scene_tts(payload: dict[str, Any]) -> dict[str, Any]:
    """AI/TTS-side implementation of TTS_AI_CONTRACT.md.

    Input:
        { storyId, sceneId, items: [{ audioId, text, emotion, voiceType, voiceId, ... }] }
    Output:
        { storyId, sceneId, audios: [{ audioId, audioUrl, durationSec, error }] }
    """
    audios = []

    for item in payload.get("items", []):
        audio_id = item.get("audioId")
        text = (item.get("text") or "").strip()

        if not audio_id:
            continue

        if not text:
            audios.append(
                {
                    "audioId": audio_id,
                    "audioUrl": None,
                    "durationSec": None,
                    "error": "Text is empty.",
                }
            )
            continue

        try:
            result = generate_tts(
                text,
                speaker=_speaker_for(item),
                language="Korean",
                instruct=_instruction_for(item),
            )
            audios.append(
                {
                    "audioId": audio_id,
                    "audioUrl": _storage_url_for(result["audio_path"]),
                    "durationSec": result.get("duration_sec"),
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - contract allows per-item errors.
            audios.append(
                {
                    "audioId": audio_id,
                    "audioUrl": None,
                    "durationSec": None,
                    "error": str(exc),
                }
            )

    return {
        "storyId": payload.get("storyId"),
        "sceneId": payload.get("sceneId"),
        "audios": audios,
    }
