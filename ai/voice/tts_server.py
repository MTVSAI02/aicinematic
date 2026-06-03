from __future__ import annotations

import io
import importlib.util
import math
import os
from pathlib import Path
import struct
from typing import Any
import urllib.parse
import wave

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import httpx

from ai.voice.comfy_tts import (
    TTS_OUTPUT_DIR_ENV,
    health_check as comfy_tts_health_check,
    synthesize_scene_tts_via_comfy,
)

MOCK_ENV = "TTS_ADAPTER_MOCK"

app = FastAPI(
    title="Mongsil ComfyUI TTS Adapter",
    description="Remote AI_TTS_URL server that adapts /tts requests to a ComfyUI voice workflow.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _tts_output_dir() -> Path | None:
    output_dir = os.getenv(TTS_OUTPUT_DIR_ENV)
    if not output_dir:
        return None
    return Path(output_dir).expanduser().resolve()


def _public_base_url(request: Request) -> str:
    configured = os.getenv("AI_TTS_PUBLIC_BASE_URL")
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _mock_enabled() -> bool:
    return _enabled(os.getenv(MOCK_ENV))


def _mock_audio_url(public_base_url: str, audio_id: str) -> str:
    quoted = urllib.parse.quote(audio_id)
    return f"{public_base_url.rstrip('/')}/mock-audio/{quoted}.wav"


def _mock_tts_response(payload: dict[str, Any], public_base_url: str) -> dict[str, Any]:
    audios = []
    for item in payload.get("items", []):
        audio_id = item.get("audioId")
        if not audio_id:
            continue
        text = (item.get("text") or "").strip()
        audios.append(
            {
                "audioId": audio_id,
                "audioUrl": _mock_audio_url(public_base_url, audio_id) if text else None,
                "durationSec": 0.8 if text else None,
                "error": None if text else "Text is empty.",
            }
        )
    return {
        "storyId": payload.get("storyId"),
        "sceneId": payload.get("sceneId"),
        "audios": audios,
    }


def _voice_sample_tts_payload(payload: dict[str, Any]) -> dict[str, Any]:
    voice_id = payload.get("voiceId") or "voice_sample"
    sample_text = payload.get("sampleText") or payload.get("text") or "안녕하세요. 저는 이 목소리로 동화를 들려드릴게요."
    audio_id = f"sample_{voice_id}"
    return {
        "storyId": "voice_sample",
        "sceneId": f"voice_sample_{voice_id}",
        "items": [
            {
                "audioId": audio_id,
                "itemIndex": 0,
                "type": "narration",
                "speaker": None,
                "text": sample_text,
                "emotion": "calm",
                "emotionLabel": "샘플",
                "voiceType": payload.get("voiceType") or "narrator",
                "voiceId": voice_id,
                "voiceName": payload.get("voiceName"),
                "voicePrompt": payload.get("voicePrompt"),
                "emotionPrompt": payload.get("emotionPrompt") or "Speak in a clear, natural narrator sample voice.",
                "characterPrompt": payload.get("characterPrompt"),
                "referenceAudioUrl": payload.get("referenceAudioUrl"),
                "referenceText": payload.get("referenceText"),
            }
        ],
    }


def _voice_sample_response(result: dict[str, Any]) -> dict[str, Any]:
    audios = result.get("audios") or []
    audio = audios[0] if audios else {}
    return {
        "audioUrl": audio.get("audioUrl"),
        "durationSec": audio.get("durationSec"),
        "error": audio.get("error"),
        "provider": "comfyui",
        "model": "qwen3-tts-adapter",
    }


def _mock_wav_bytes(audio_id: str) -> bytes:
    sample_rate = 16000
    duration_seconds = 0.8
    frequency = 420 + (sum(audio_id.encode("utf-8")) % 220)
    frame_count = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frame_count):
            t = index / sample_rate
            envelope = min(1.0, index / 1200, (frame_count - index) / 1200)
            value = int(9000 * envelope * math.sin(2 * math.pi * frequency * t))
            wav.writeframesraw(struct.pack("<h", value))

    return buffer.getvalue()


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "mongsil-comfy-tts-adapter",
        "status": "running",
        "health": "/health",
        "tts": "/tts",
        "voiceSample": "/voice-sample",
    }


@app.get("/health")
def health(request: Request) -> dict[str, Any]:
    public_base_url = _public_base_url(request)
    mock_enabled = _mock_enabled()
    comfy = {"ok": True, "mock": True} if mock_enabled else comfy_tts_health_check()
    return {
        "ok": bool(comfy.get("ok")),
        "service": "mongsil-comfy-tts-adapter",
        "mode": "mock" if mock_enabled else "comfy",
        "mockEnabled": mock_enabled,
        "publicBaseUrl": public_base_url,
        "comfy": comfy,
        "fastapiInstalled": _module_available("fastapi"),
        "httpxInstalled": _module_available("httpx"),
    }


@app.post("/tts")
async def tts(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if _mock_enabled():
        return _mock_tts_response(payload, _public_base_url(request))
    return synthesize_scene_tts_via_comfy(
        payload,
        public_base_url=_public_base_url(request),
    )


@app.post("/voice-sample")
async def voice_sample(request: Request) -> dict[str, Any]:
    payload = _voice_sample_tts_payload(await request.json())
    if _mock_enabled():
        result = _mock_tts_response(payload, _public_base_url(request))
    else:
        result = synthesize_scene_tts_via_comfy(
            payload,
            public_base_url=_public_base_url(request),
        )
    return _voice_sample_response(result)


@app.get("/view")
def proxy_comfy_view(filename: str, subfolder: str = "", type: str = "output") -> Response:
    base_url = os.getenv("COMFYUI_VOICE_URL", "").rstrip("/")
    if not base_url:
        return Response("COMFYUI_VOICE_URL is not configured", status_code=500)

    try:
        response = httpx.get(
            f"{base_url}/view",
            params={"filename": filename, "subfolder": subfolder, "type": type},
            timeout=120,
        )
    except httpx.RequestError as exc:
        return Response(f"Failed to proxy ComfyUI /view: {exc}", status_code=502)

    if response.status_code != 200:
        return Response(response.text, status_code=response.status_code)

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "audio/wav"),
    )


@app.get("/mock-audio/{audio_id}.wav")
def serve_mock_audio(audio_id: str) -> Response:
    return Response(content=_mock_wav_bytes(audio_id), media_type="audio/wav")


@app.get("/tts-output/{filename}")
def serve_tts_output(filename: str):
    output_dir = _tts_output_dir()
    if output_dir is None:
        return Response(f"{TTS_OUTPUT_DIR_ENV} is not configured", status_code=404)
    target = (output_dir / filename).resolve()
    if output_dir not in target.parents or not target.is_file():
        return Response("Audio file not found", status_code=404)
    return FileResponse(target, media_type="audio/wav")
