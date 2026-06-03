from __future__ import annotations

import copy
import os
import time
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any

from ai.comfy_client import ComfyUIClient
from ai.core.exceptions import (
    ComfyUIConfigError,
    ComfyUIError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    WorkflowLoadError,
    WorkflowMappingError,
)


VOICE_COMFY_URL_ENV = "COMFYUI_VOICE_URL"
TTS_WORKFLOW_PATH_ENV = "COMFYUI_TTS_WORKFLOW_PATH"
TTS_MAPPING_PATH_ENV = "COMFYUI_TTS_MAPPING_PATH"
TTS_VOICE_MAP_PATH_ENV = "COMFYUI_TTS_VOICE_MAP_PATH"
TTS_OUTPUT_DIR_ENV = "COMFYUI_TTS_OUTPUT_DIR"
TTS_TIMEOUT_ENV = "COMFYUI_TTS_TIMEOUT_SECONDS"
TTS_POLL_INTERVAL_ENV = "COMFYUI_TTS_POLL_INTERVAL_SECONDS"
DEFAULT_TTS_TIMEOUT_SECONDS = 600
DEFAULT_TTS_POLL_INTERVAL_SECONDS = 2
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ComfyUIConfigError(f"{name} must be an integer, got: {value!r}") from exc
    if parsed <= 0:
        raise ComfyUIConfigError(f"{name} must be positive, got: {parsed}")
    return parsed


def _resolve_voice_comfy_url() -> str:
    base_url = os.getenv(VOICE_COMFY_URL_ENV)
    if not base_url or not base_url.strip():
        raise ComfyUIConfigError(f"{VOICE_COMFY_URL_ENV} is not configured")
    return base_url.rstrip("/")


def _resolve_path(env_name: str) -> Path:
    value = os.getenv(env_name)
    if not value or not value.strip():
        raise ComfyUIConfigError(f"{env_name} is not configured")
    return Path(value).expanduser().resolve()


@lru_cache(maxsize=1)
def _load_tts_workflow_and_mapping() -> tuple[dict[str, Any], dict[str, Any]]:
    workflow_path = _resolve_path(TTS_WORKFLOW_PATH_ENV)
    mapping_path = _resolve_path(TTS_MAPPING_PATH_ENV)
    workflow = ComfyUIClient.load_workflow_json(workflow_path)
    mapping = ComfyUIClient.load_mapping_json(mapping_path)
    if not isinstance(workflow, dict) or not workflow:
        raise WorkflowLoadError(f"TTS workflow is empty: {workflow_path}")
    if not isinstance(mapping, dict) or "text" not in mapping:
        raise WorkflowMappingError("TTS mapping must include at least a 'text' mapping")
    return workflow, mapping


@lru_cache(maxsize=1)
def _load_voice_map() -> dict[str, dict[str, Any]]:
    value = os.getenv(TTS_VOICE_MAP_PATH_ENV)
    if not value or not value.strip():
        return {}

    path = _resolve_path(TTS_VOICE_MAP_PATH_ENV)
    voice_map = ComfyUIClient.load_mapping_json(path)
    if not isinstance(voice_map, dict):
        raise WorkflowMappingError("TTS voice map must be a JSON object")
    for voice_id, voice_values in voice_map.items():
        if not isinstance(voice_id, str) or not isinstance(voice_values, dict):
            raise WorkflowMappingError(
                "TTS voice map must be shaped as { voiceId: { ...values } }"
            )
    return voice_map


def _set_path_value(target: dict[str, Any], path: list[str], value: Any, *, node_id: str) -> None:
    current: Any = target
    for step in path[:-1]:
        if not isinstance(current, dict) or step not in current:
            raise WorkflowMappingError(f"Path {path} not found in node '{node_id}'")
        current = current[step]
    if not isinstance(current, dict) or path[-1] not in current:
        raise WorkflowMappingError(f"Path {path} not found in node '{node_id}'")
    current[path[-1]] = value


def _apply_optional_mapping(
    workflow: dict[str, Any],
    mapping: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(workflow)
    for key, value in values.items():
        if key not in mapping or value is None:
            continue
        spec = mapping[key]
        node_id = spec.get("nodeId")
        path = spec.get("path")
        if not node_id or not path:
            raise WorkflowMappingError(f"Invalid mapping for '{key}'")
        if node_id not in result:
            raise WorkflowMappingError(f"Node '{node_id}' not found for mapping '{key}'")
        _set_path_value(result[node_id], path, value, node_id=node_id)
    return result


def _item_values(item: dict[str, Any]) -> dict[str, Any]:
    reference_audio_url = item.get("referenceAudioUrl")
    reference_text = item.get("referenceText")
    emotion_prompt = item.get("emotionPrompt")
    character_prompt = item.get("characterPrompt")

    return {
        "audioId": item.get("audioId"),
        "itemIndex": item.get("itemIndex"),
        "text": item.get("text"),
        "type": item.get("type"),
        "sceneSpeaker": item.get("speaker"),
        "emotion": item.get("emotion"),
        "emotionLabel": item.get("emotionLabel"),
        "voiceType": item.get("voiceType"),
        "characterId": item.get("characterId"),
        "voiceId": item.get("voiceId"),
        "voiceName": item.get("voiceName"),
        "voicePrompt": item.get("voicePrompt"),
        "emotionPrompt": emotion_prompt,
        "characterPrompt": character_prompt,
        "referenceAudioUrl": reference_audio_url,
        "referenceText": reference_text,
        "speaker": item.get("speaker"),
        "refAudio": item.get("refAudio") or reference_audio_url,
        "refText": item.get("refText") or reference_text,
        "sampleAudioUrl": item.get("sampleAudioUrl"),
    }


def _workflow_values_for_item(
    item: dict[str, Any],
    voice_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    values = _item_values(item)
    voice_id = item.get("voiceId")
    if voice_id and voice_id in voice_map:
        values.update(voice_map[voice_id])
    return values


def _queue_prompt(client: ComfyUIClient, workflow: dict[str, Any]) -> str:
    result = client.post_json("/prompt", {"prompt": workflow})
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise ComfyUIResponseError(f"ComfyUI /prompt response has no prompt_id: {result}")
    return prompt_id


def _wait_for_history(client: ComfyUIClient, prompt_id: str) -> dict[str, Any]:
    timeout = _env_int(TTS_TIMEOUT_ENV, DEFAULT_TTS_TIMEOUT_SECONDS)
    poll_interval = _env_int(TTS_POLL_INTERVAL_ENV, DEFAULT_TTS_POLL_INTERVAL_SECONDS)
    start = time.time()

    while time.time() - start < timeout:
        history = client.get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                for msg_type, msg_data in status.get("messages", []):
                    if msg_type == "execution_error":
                        node = msg_data.get("node_type", "?")
                        message = msg_data.get("exception_message", "Unknown ComfyUI error")
                        raise ComfyUIError(f"ComfyUI execution error [{node}]: {message}")
                raise ComfyUIError("ComfyUI execution failed")
            return entry
        time.sleep(poll_interval)

    raise ComfyUITimeoutError(f"TTS generation timed out ({timeout}s)")


def _is_audio_filename(filename: str | None) -> bool:
    return bool(filename and Path(filename).suffix.lower() in _AUDIO_EXTENSIONS)


def _collect_audio_infos(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        filename = value.get("filename")
        if _is_audio_filename(filename):
            found.append(
                {
                    "filename": filename,
                    "subfolder": value.get("subfolder", ""),
                    "type": value.get("type", "output"),
                }
            )
        for child in value.values():
            found.extend(_collect_audio_infos(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_collect_audio_infos(child))
    return found


def _find_latest_local_audio(started_at: float) -> Path | None:
    output_dir = os.getenv(TTS_OUTPUT_DIR_ENV)
    if not output_dir:
        return None
    root = Path(output_dir).expanduser().resolve()
    if not root.is_dir():
        raise ComfyUIConfigError(f"{TTS_OUTPUT_DIR_ENV} does not exist: {root}")
    candidates = [
        path
        for path in root.glob("*")
        if path.is_file()
        and path.suffix.lower() in _AUDIO_EXTENSIONS
        and path.stat().st_mtime >= started_at - 1
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _build_proxy_view_url(
    public_base_url: str,
    audio_info: dict[str, Any],
) -> str:
    query = urllib.parse.urlencode(
        {
            "filename": audio_info["filename"],
            "subfolder": audio_info.get("subfolder", ""),
            "type": audio_info.get("type", "output"),
        }
    )
    return f"{public_base_url.rstrip('/')}/view?{query}"


def _build_local_output_url(public_base_url: str, path: Path) -> str:
    return f"{public_base_url.rstrip('/')}/tts-output/{urllib.parse.quote(path.name)}"


def synthesize_scene_tts_via_comfy(
    payload: dict[str, Any],
    *,
    public_base_url: str,
) -> dict[str, Any]:
    try:
        client = ComfyUIClient(base_url=_resolve_voice_comfy_url())
        workflow_template, mapping = _load_tts_workflow_and_mapping()
        voice_map = _load_voice_map()
    except Exception as exc:  # noqa: BLE001 - return contract-shaped item errors.
        return {
            "storyId": payload.get("storyId"),
            "sceneId": payload.get("sceneId"),
            "audios": [
                {
                    "audioId": item.get("audioId"),
                    "audioUrl": None,
                    "durationSec": None,
                    "error": str(exc),
                }
                for item in payload.get("items", [])
                if item.get("audioId")
            ],
        }

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

        started_at = time.time()
        try:
            workflow = _apply_optional_mapping(
                workflow_template,
                mapping,
                _workflow_values_for_item({**item, "text": text}, voice_map),
            )
            prompt_id = _queue_prompt(client, workflow)
            history_entry = _wait_for_history(client, prompt_id)
            audio_infos = _collect_audio_infos(history_entry.get("outputs", {}))

            if audio_infos:
                audio_url = _build_proxy_view_url(public_base_url, audio_infos[0])
            else:
                local_audio = _find_latest_local_audio(started_at)
                if not local_audio:
                    raise ComfyUIResponseError(
                        "ComfyUI finished but no audio file was found in history outputs."
                    )
                audio_url = _build_local_output_url(public_base_url, local_audio)

            audios.append(
                {
                    "audioId": audio_id,
                    "audioUrl": audio_url,
                    "durationSec": None,
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - contract supports per-item errors.
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


def health_check() -> dict[str, Any]:
    try:
        client = ComfyUIClient(base_url=_resolve_voice_comfy_url())
        comfy_health = client.health_check()
    except ComfyUIError as exc:
        comfy_health = {"ok": False, "error": exc.message}

    workflow_path = os.getenv(TTS_WORKFLOW_PATH_ENV)
    mapping_path = os.getenv(TTS_MAPPING_PATH_ENV)
    voice_map_path = os.getenv(TTS_VOICE_MAP_PATH_ENV)
    output_dir = os.getenv(TTS_OUTPUT_DIR_ENV)
    workflow_exists = bool(workflow_path and Path(workflow_path).expanduser().is_file())
    mapping_exists = bool(mapping_path and Path(mapping_path).expanduser().is_file())
    voice_map_exists = bool(
        not voice_map_path or Path(voice_map_path).expanduser().is_file()
    )
    output_dir_exists = bool(output_dir and Path(output_dir).expanduser().is_dir())
    return {
        "ok": bool(
            comfy_health.get("ok")
            and workflow_exists
            and mapping_exists
            and voice_map_exists
        ),
        "comfy": comfy_health,
        "workflowPath": workflow_path,
        "workflowExists": workflow_exists,
        "mappingPath": mapping_path,
        "mappingExists": mapping_exists,
        "voiceMapPath": voice_map_path,
        "voiceMapExists": voice_map_exists,
        "outputDir": output_dir,
        "outputDirExists": output_dir_exists,
    }
