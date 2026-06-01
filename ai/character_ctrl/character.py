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
    - ai.comfy_client.run_workflow()   ← 박진희 담당, 아직 미구현
    - ai.image.prompt_builder.build()  ← 박진희 담당, 아직 미구현
"""

from __future__ import annotations

import uuid
from enum import Enum
from pathlib import Path

from ai.comfy_client import run_workflow
# from ai.image.prompt_builder import build as build_prompt  # TODO: prompt_builder 완성 후 해제

WORKFLOW_NAME = "character_generate"
OUTPUT_DIR = Path("backend/app/storage/characters")


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
) -> str:
    """HiDream-I1로 캐릭터 이미지를 생성한다.

    Args:
        character_id:      캐릭터 고유 ID (백엔드에서 발급).
        name:              캐릭터 이름 (로그·파일명 용도).
        appearance_prompt: 외형 설명 문자열 (백엔드 스키마 appearancePrompt).
                           예) "금발 단발, 초록 외투를 입은 작은 소년"
        variant:           HiDream 변형. 기본값 DEV.

    Returns:
        저장된 이미지의 파일 경로 문자열.

    Example:
        >>> path = generate_character(
        ...     "abc-123", "어린왕자",
        ...     "금발 단발, 초록 외투를 입은 작은 소년"
        ... )
        >>> print(path)
        "backend/app/storage/characters/abc-123.png"
    """
    config = _VARIANT_CONFIG[variant]

    # 1. appearance_prompt → HiDream 프롬프트 변환
    # TODO: prompt_builder 완성 후 아래로 교체
    # prompt = build_prompt(appearance_prompt)
    prompt = _tags_to_prompt(appearance_prompt)

    # 2. 워크플로 inputs 구성
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

    # 3. 워크플로 실행
    result = run_workflow(workflow_name=WORKFLOW_NAME, inputs=inputs)
    image_bytes = result["images"][0]

    # 4. 이미지 저장
    output_path = _save_image(character_id, image_bytes)
    return str(output_path)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _tags_to_prompt(appearance_prompt: str) -> str:
    """appearance_prompt를 HiDream 프롬프트로 변환 (임시 구현).

    HiDream은 자연어 프롬프트에 강하므로 문장형으로 조합.
    TODO: prompt_builder.py 완성 후 이 함수 제거.
    """
    return f"A single character, full body, standing, white background. {appearance_prompt.strip()}"


def _make_seed(character_id: str) -> int:
    """character_id 기반으로 재현 가능한 시드 생성.

    UUID 형식이면 UUID 기반 시드, 아니면 hash 기반 시드를 사용한다.
    (mock ID 예: 'char_mock_001' 도 처리 가능)
    """
    try:
        return int(uuid.UUID(character_id).int % (2**32))
    except ValueError:
        return abs(hash(character_id)) % (2**32)


def _save_image(character_id: str, image_bytes: bytes | None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{character_id}.png"
    if image_bytes is not None:
        output_path.write_bytes(image_bytes)
    return output_path
