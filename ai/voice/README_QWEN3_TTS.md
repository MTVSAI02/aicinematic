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

FastAPI 라우터에서는 아래 함수만 감싸서 호출하면 된다.

```python
from ai.voice.tts import generate_tts
from ai.voice.clone import generate_voice_clone

tts_result = generate_tts("안녕하세요.", speaker="Sohee")
clone_result = generate_voice_clone(
    "새로 합성할 문장입니다.",
    ref_audio="backend/app/storage/voice/sample.wav",
    ref_text="샘플에서 실제로 말한 문장입니다.",
)
```

## 운영 메모

- 첫 실행 시 Hugging Face에서 모델을 다운로드한다. 현재 노트북에서는 기본 사용자 캐시인 `C:\Users\Admin\.cache\huggingface`에 모델이 저장된다.
- 이 노트북은 VRAM 8GB라 0.6B 모델을 기본값으로 둔다. 발표용 품질을 더 올릴 때는 4090 머신이나 클라우드 GPU에서 1.7B 모델로 교체한다.
- `flash-attn is not installed` 경고는 Windows 로컬 테스트에서는 무시해도 된다. 속도 최적화용이며 필수 설치 항목은 아니다.
- `SoX could not be found` 경고가 보일 수 있다. 기본 CustomVoice 테스트는 우선 진행하고, 보이스 클로닝에서 오디오 로딩 문제가 생기면 Windows용 SoX 설치를 별도로 진행한다.
