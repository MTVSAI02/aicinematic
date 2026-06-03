# Qwen3-TTS local setup

이 폴더는 언리얼 B 담당 음성 파트를 프로젝트에서 바로 실험하기 위한 로컬 실행용 스크립트를 담는다.

## 현재 설치 상태

- 프로젝트 전용 Python: `.venv-qwen3-tts`
- Python version: `3.12.13`
- Package: `qwen-tts`
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- PyTorch: CUDA 사용 가능
- 기본 테스트 모델: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`

README 원본이 Python 3.12 격리 환경을 권장해서, 시스템 Python 3.14 계열 대신 프로젝트 전용 3.12 가상환경으로 고정했다.

## 기본 한국어 TTS 테스트

프로젝트 루트에서 실행한다.

```powershell
.\.venv-qwen3-tts\Scripts\python.exe .\ai\voice\qwen3_tts_smoke.py
```

출력 파일:

```text
backend/app/storage/voice/qwen3_tts_custom_voice.wav
```

문장을 바꿔서 실행할 수도 있다.

```powershell
.\.venv-qwen3-tts\Scripts\python.exe .\ai\voice\qwen3_tts_smoke.py --text "숲속 작은 마을에 별빛을 모으는 아이가 살고 있었어요."
```

## 보이스 클로닝 테스트

사용자 음성 샘플과 해당 샘플의 대본이 필요하다.

```powershell
.\.venv-qwen3-tts\Scripts\python.exe .\ai\voice\qwen3_voice_clone_smoke.py --ref-audio ".\sample.wav" --ref-text "샘플 음성에서 실제로 말한 문장입니다." --text "이 목소리로 새로운 대사를 합성합니다."
```

출력 파일:

```text
backend/app/storage/voice/qwen3_tts_voice_clone.wav
```

## 백엔드 연동용 함수

FastAPI 라우터는 `TTS_AI_CONTRACT.md` 기준으로 `audioId`가 포함된 payload를 만든다.
로컬 Qwen 연동은 `ai.voice.tts_contract.synthesize_scene_tts`가 담당한다.

```python
from ai.voice.tts_contract import synthesize_scene_tts

result = synthesize_scene_tts({
    "storyId": "story_mock_001",
    "sceneId": "scene_001",
    "items": [{"audioId": "audio_mock_001", "text": "안녕하세요.", "emotion": "calm"}],
})
```

백엔드에서 실제 Qwen 합성을 켜려면:

```powershell
$env:QWEN_TTS_ENABLED="1"
.\.venv-qwen3-tts\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

## 운영 메모

- 첫 실행 시 Hugging Face에서 모델을 다운로드한다. 현재 노트북에서는 기본 사용자 캐시인 `C:\Users\Admin\.cache\huggingface`에 모델이 저장된다.
- 이 노트북은 VRAM 8GB라 0.6B 모델을 기본값으로 둔다. 발표용 품질을 더 올릴 때는 4090 머신이나 클라우드 GPU에서 1.7B 모델로 교체한다.
- `flash-attn is not installed` 경고는 Windows 로컬 테스트에서는 무시해도 된다. 속도 최적화용이며 필수 설치 항목은 아니다.
- `SoX could not be found` 경고가 보일 수 있다. 기본 CustomVoice 테스트는 우선 진행하고, 보이스 클로닝에서 오디오 로딩 문제가 생기면 Windows용 SoX 설치를 별도로 진행한다.

## Runtime notes

- `ai/voice/qwen3_runtime.py` sets `NUMBA_CACHE_DIR` to `.cache/qwen3_tts/numba` before importing `qwen_tts`. This avoids long Windows temp/cache stalls during `librosa`/`numba` import.
- `load_qwen3_model()` resolves the Hugging Face cached snapshot first and passes the local snapshot path to `from_pretrained()`. This prevents `AutoProcessor` from making an extra Hugging Face API request during local/offline runs.
- Local FastAPI integration test:

```powershell
$env:QWEN_TTS_ENABLED="1"
$env:HF_HUB_OFFLINE="1"
.\.venv-qwen3-tts\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

## Remote AI_TTS_URL ComfyUI adapter for teammates

The team flow is:

```text
Frontend
-> teammate backend POST /api/tts/scene
-> AI_TTS_URL adapter POST /tts
-> ComfyUI /prompt + /history
-> ComfyUI output/qwen3_tts/*.wav
-> adapter returns playable audioUrl
```

Mock adapter test without ComfyUI:

```bash
cd ~/aicinematic2
python -m pip install fastapi uvicorn httpx
export TTS_ADAPTER_MOCK="1"
export AI_TTS_PUBLIC_BASE_URL="http://127.0.0.1:8100"
python -m uvicorn ai.voice.tts_server:app --host 0.0.0.0 --port 8100
```

When `TTS_ADAPTER_MOCK=1`, `POST /tts` returns one playable mock wav URL per
input item:

```text
http://127.0.0.1:8100/mock-audio/<audioId>.wav
```

Run the voice/TTS ComfyUI on the shared PC. If GPU 0 is used by character or
background generation, run voice/TTS on GPU 1:

```bash
cd ~/comfyui_project/ComfyUI
source ~/comfyui_project/.venv/bin/activate
CUDA_VISIBLE_DEVICES=1 python main.py --listen 0.0.0.0 --port 8189
```

Run the `/tts` adapter in a separate terminal on the same shared PC:

```bash
cd ~/aicinematic2
source ~/comfyui_project/.venv/bin/activate
python -m pip install fastapi uvicorn httpx
export COMFYUI_VOICE_URL="http://127.0.0.1:8189"
export COMFYUI_TTS_WORKFLOW_PATH="/path/to/qwen3_tts_workflow_api.json"
export COMFYUI_TTS_MAPPING_PATH="/path/to/qwen3_tts_mapping.json"
export COMFYUI_TTS_VOICE_MAP_PATH="/path/to/qwen3_tts_voice_map.json"
export COMFYUI_TTS_OUTPUT_DIR="$HOME/comfyui_project/ComfyUI/output/qwen3_tts"
export AI_TTS_PUBLIC_BASE_URL="http://<SHARED_PC_LAN_IP>:8100"
python -m uvicorn ai.voice.tts_server:app --host 0.0.0.0 --port 8100
```

The workflow JSON must be the ComfyUI API-format workflow. The mapping JSON says
which workflow node receives `text`, `voicePrompt`, `emotion`, etc. At minimum it
must map `text`. See `ai/workflows/qwen3_tts_mapping.example.json`, for example:

```json
{
  "text": { "nodeId": "12", "path": ["inputs", "text"] },
  "voicePrompt": { "nodeId": "13", "path": ["inputs", "text"] },
  "speaker": { "nodeId": "14", "path": ["inputs", "speaker"] },
  "refAudio": { "nodeId": "15", "path": ["inputs", "audio"] },
  "refText": { "nodeId": "16", "path": ["inputs", "text"] },
  "seed": { "nodeId": "20", "path": ["inputs", "seed"] }
}
```

The optional voice map JSON translates backend `voiceId` values into ComfyUI
voice inputs. See `ai/workflows/qwen3_tts_voice_map.example.json`, for example:

```json
{
  "voice_preset_narrator_calm_001": {
    "speaker": "sohee",
    "voicePrompt": "calm, warm narrator",
    "refAudio": "/path/to/reference.wav",
    "refText": "The exact sentence spoken in the reference audio."
  }
}
```

Health check from another teammate PC:

```bash
curl http://<SHARED_PC_LAN_IP>:8100/health
```

On each teammate backend PC, put this in `backend/.env`:

```env
AI_TTS_URL=http://<SHARED_PC_LAN_IP>:8100
QWEN_TTS_ENABLED=0
AI_TTS_TIMEOUT_SEC=300
```

If `/health` works but audio does not play, check the shared PC firewall and make
sure port `8100` is allowed.
