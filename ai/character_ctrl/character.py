"""HiDream-I1 캐릭터 이미지 생성.

역할:
    - 태그 문자열을 받아 프롬프트로 변환
    - ComfyUI의 character_generate 워크플로를 실행 (HiDream-I1)
    - 생성된 이미지를 storage에 저장하고 경로 반환

모델 정보:
    HiDream-I1 — 17B DiT + MoE 하이브리드 아키텍처 (Flux 계열)
    텍스트 인코더: Llama-3.1-8B + flan-t5-xxl + CLIP
    VAE: Flux VAE 공유 사용

변형(Variant) 선택 가이드:
    - Full : 최고 품질, steps=50, cfg=5.0, VRAM 20GB
    - Dev  : 품질/속도 균형, steps=28, cfg=1.0, VRAM 16GB  ← 기본값
    - Fast : 빠른 반복, steps=16, cfg=1.0, VRAM 16GB

    ⚠️ Dev / Fast는 negative_prompt 불필요 (cfg=1.0 사용)

의존:
    - ai.comfy_workflow_runner.run_workflow()  ← 워크플로 실행(생성). 결과 bytes 반환
    - ai.image.prompt_builder.build()          ← TODO: prompt_builder 완성 후 해제
"""

from __future__ import annotations

import hashlib
import uuid
from enum import Enum

from ai.comfy_workflow_runner import run_workflow
# from ai.image.prompt_builder import build as build_prompt  # TODO: prompt_builder 완성 후 해제

WORKFLOW_NAME = "character_generate"


class HiDreamVariant(str, Enum):
    FULL = "hidream_i1_full"   # 최고 품질
    DEV  = "hidream_i1_dev"    # 균형 (기본값)
    FAST = "hidream_i1_fast"   # 빠른 반복

# 변형별 샘플링 설정
_VARIANT_CONFIG: dict[HiDreamVariant, dict] = {
    HiDreamVariant.FULL: {"steps": 50, "cfg": 5.0,  "use_negative": True},
    HiDreamVariant.DEV:  {"steps": 28, "cfg": 1.0,  "use_negative": False},
    HiDreamVariant.FAST: {"steps": 16, "cfg": 1.0,  "use_negative": False},
}

_NEGATIVE_PROMPT = (
    "ugly, deformed, blurry, low quality, extra limbs, "
    "missing fingers, watermark, text"
)


def generate_character(
    character_id: str,
    name: str,
    appearance_prompt: str,
    variant: HiDreamVariant = HiDreamVariant.DEV,
) -> bytes:
    """HiDream-I1로 캐릭터 이미지를 생성하고 **이미지 bytes를 반환한다.**

    저장 책임 경계(ai_code_review_prompt.md §0): AI는 생성 결과(bytes)만 반환한다.
    파일 저장 / `/storage` URL 생성 / repository 저장은 backend가 담당한다.

    Args:
        character_id:      캐릭터 고유 ID (백엔드에서 발급). seed 재현에 사용.
        name:              캐릭터 이름 (로그 용도).
        appearance_prompt: 외형 설명 문자열 (백엔드 스키마 appearancePrompt).
        variant:           HiDream 변형. 기본값 DEV.

    Returns:
        생성된 이미지의 raw bytes (PNG).
    """
    config = _VARIANT_CONFIG[variant]

    # 1. appearance_prompt → HiDream 프롬프트 변환
    # TODO: prompt_builder 완성 후 아래로 교체
    # prompt = build_prompt(appearance_prompt)
    prompt = _tags_to_prompt(appearance_prompt)

    # 2. 워크플로 inputs 구성
    # ⚠️ 현재 run_workflow(character_generate)는 positive_prompt / seed 만 워크플로에 주입한다.
    #    아래 steps/cfg/model/width/height/negative_prompt 는 아직 워크플로에 반영되지 않는다
    #    (Full/Dev/Fast variant 설정은 동작하지 않음 — 워크플로 JSON의 고정값이 쓰인다).
    #    캐릭터를 AI FastAPI 서버 호출 방식으로 이관할 때 이 파라미터 전달을 함께 재설계한다.
    inputs = {
        "positive_prompt": prompt,
        "seed": _make_seed(character_id),
        "steps": config["steps"],
        "cfg": config["cfg"],
        "model": variant.value,
        "width": 1024,
        "height": 1024,
    }
    if config["use_negative"]:
        inputs["negative_prompt"] = _NEGATIVE_PROMPT

    # 3. 워크플로 실행 → 이미지 bytes 반환 (저장은 backend)
    result = run_workflow(workflow_name=WORKFLOW_NAME, inputs=inputs)
    return result["images"][0]


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _tags_to_prompt(appearance_prompt: str) -> str:
    """appearance_prompt를 HiDream 프롬프트로 변환 (임시 구현).

    HiDream은 자연어 프롬프트에 강하므로 문장형으로 조합.
    TODO: prompt_builder.py 완성 후 이 함수 제거.
    """
    return f"A single character, full body, standing, white background. {appearance_prompt.strip()}"


def _make_seed(character_id: str) -> int:
    """character_id 기반으로 **재현 가능한** 시드 생성.

    UUID 형식이면 UUID 기반, 아니면 sha256 기반 시드를 사용한다.
    ⚠️ Python 내장 hash()는 PYTHONHASHSEED로 프로세스마다 값이 달라져
       'char_mock_001' 같은 ID의 시드가 재시작 후 바뀐다. 그래서 sha256으로 고정한다.
    """
    try:
        return int(uuid.UUID(character_id).int % (2**32))
    except ValueError:
        digest = hashlib.sha256(character_id.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big")  # 0 ~ 2**32-1, 프로세스 무관 재현
