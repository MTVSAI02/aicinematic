"""IP-Adapter for Flux — 씬 간 얼굴 일관성 고정.

역할:
    - HiDream-I1 (Flux 계열 DiT) 에서 얼굴 일관성을 유지
    - IP-Adapter for Flux를 사용해 레퍼런스 얼굴을 새 씬에 이식

아키텍처 배경:
    HiDream-I1은 Flux 계열 DiT 구조로, SDXL용 IPAdapter FaceID와 직접 호환되지 않음.
    대신 IP-Adapter for Flux (comfyorg/comfyui-ipadapter) 를 사용.
    InsightFace로 얼굴 임베딩 추출 → Flux cross-attention에 주입.

필요 모델 (ComfyUI models/ 폴더):
    - ip-adapter/ip_adapter_flux_image_encoder/  (CLIP Vision)
    - ip-adapter/ip_adapter_flux_dev.safetensors (or full)
    - insightface/models/antelopev2/

의존:
    - ai.comfy_client.run_workflow()   ← 박진희 담당, 아직 미구현
    - ai.image.prompt_builder.build()  ← 박진희 담당, 아직 미구현
"""

from __future__ import annotations

from pathlib import Path

from .character import HiDreamVariant, _VARIANT_CONFIG

# TODO: 박진희 comfy_client 완성 후 주석 해제
# from ai.comfy_client import run_workflow
# from ai.image.prompt_builder import build as build_prompt

WORKFLOW_NAME = "face_lock"
OUTPUT_DIR = Path("backend/app/storage/scenes")

# IP-Adapter 적용 강도 (0.0 ~ 1.0)
# 높을수록 레퍼런스 얼굴과 닮음↑, 낮을수록 씬 프롬프트 자유도↑
DEFAULT_IP_STRENGTH = 0.80


def lock_face(
    character_id: str,
    scene_id: str,
    reference_image_path: str,
    scene_appearance_prompt: str,
    variant: HiDreamVariant = HiDreamVariant.DEV,
    ip_strength: float = DEFAULT_IP_STRENGTH,
) -> str:
    """IP-Adapter for Flux로 얼굴을 고정한 씬 이미지를 생성한다.

    Args:
        character_id:          캐릭터 ID.
        scene_id:              씬 ID (저장 경로용).
        reference_image_path:  character.py가 생성한 원본 캐릭터 이미지 경로.
        scene_appearance_prompt: 씬에서의 캐릭터 외형 설명. 예) "서있는 자세, 밝은 표정, 야외"
        variant:               HiDream 변형. 기본값 DEV.
        ip_strength:           IP-Adapter 강도. 기본값 0.80.

    Returns:
        저장된 이미지의 파일 경로 문자열.

    Example:
        >>> path = lock_face(
        ...     "abc-123", "scene-001",
        ...     "backend/app/storage/characters/abc-123.png",
        ...     "standing, waving hand, outdoor",
        ... )
        >>> print(path)
        "backend/app/storage/scenes/scene-001_abc-123.png"
    """
    ref_path = Path(reference_image_path)
    if not ref_path.exists():
        raise FileNotFoundError(f"레퍼런스 이미지 없음: {reference_image_path}")

    config = _VARIANT_CONFIG[variant]

    # 1. appearance_prompt → 프롬프트 변환
    # TODO: prompt_builder 완성 후 아래로 교체
    # prompt = build_prompt(scene_appearance_prompt)
    prompt = _tags_to_prompt(scene_appearance_prompt)

    # 2. 워크플로 inputs 구성
    inputs = {
        "reference_image": None,   # TODO: ref_path.read_bytes()
        "positive_prompt": prompt,
        "ip_strength": ip_strength,
        "steps": config["steps"],
        "cfg": config["cfg"],
        "model": variant.value,
        "width": 1024,
        "height": 1024,
    }
    if config["use_negative"]:
        inputs["negative_prompt"] = _NEGATIVE_PROMPT

    # 3. 워크플로 실행
    # TODO: comfy_client 완성 후 아래로 교체
    # result = run_workflow(workflow_name=WORKFLOW_NAME, inputs=inputs)
    # image_bytes = result["images"][0]
    image_bytes = None  # TODO: 제거

    # 4. 저장
    output_path = _save_image(scene_id, character_id, image_bytes)
    return str(output_path)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

_NEGATIVE_PROMPT = (
    "ugly, deformed, blurry, low quality, extra limbs, "
    "missing fingers, watermark, text, face distortion"
)


def _tags_to_prompt(appearance_prompt: str) -> str:
    """appearance_prompt를 프롬프트로 변환 (임시).

    TODO: prompt_builder.py 완성 후 제거.
    """
    return f"A single character. {appearance_prompt.strip()}"


def _save_image(scene_id: str, character_id: str, image_bytes: bytes | None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{scene_id}_{character_id}.png"
    if image_bytes is not None:
        output_path.write_bytes(image_bytes)
    return output_path
