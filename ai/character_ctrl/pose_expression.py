"""ControlNet — 캐릭터 포즈·표정 변형.

역할:
    - 포즈 프리셋(서있기, 앉기 등)을 ControlNet OpenPose로 적용
    - 표정 프리셋(기쁨, 슬픔 등)을 프롬프트 태그로 반영
    - face_lock.py 결과 이미지를 입력으로 받아 변형

의존:
    - ai.comfy_workflow_runner.run_workflow()  ← 워크플로 실행(생성). 결과 bytes 반환
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

# TODO: pose_expression 워크플로 연결 시 주석 해제 (run_workflow는 결과 bytes 반환, 저장은 backend)
# from ai.comfy_workflow_runner import run_workflow

WORKFLOW_NAME = "pose_expression"
OUTPUT_DIR = Path("backend/app/storage/scenes")


# ── 프리셋 정의 ───────────────────────────────────────────────────────────────

class PosePreset(str, Enum):
    """ControlNet OpenPose 포즈 프리셋."""
    STANDING   = "standing"    # 서있기 (기본)
    SITTING    = "sitting"     # 앉기
    WALKING    = "walking"     # 걷기
    WAVING     = "waving"      # 손 흔들기
    CROUCHING  = "crouching"   # 쪼그려 앉기


class ExpressionPreset(str, Enum):
    """표정 프리셋 — 프롬프트 태그로 변환."""
    NEUTRAL  = "neutral"   # 무표정
    HAPPY    = "happy"     # 기쁨
    SAD      = "sad"       # 슬픔
    ANGRY    = "angry"     # 화남
    SURPRISE = "surprise"  # 놀람


# 표정 프리셋 → 프롬프트 태그 매핑
EXPRESSION_TAGS: dict[ExpressionPreset, str] = {
    ExpressionPreset.NEUTRAL:  "neutral expression, calm face",
    ExpressionPreset.HAPPY:    "smiling, happy expression, bright eyes",
    ExpressionPreset.SAD:      "sad expression, downcast eyes, frowning",
    ExpressionPreset.ANGRY:    "angry expression, furrowed brows",
    ExpressionPreset.SURPRISE: "surprised expression, wide eyes, open mouth",
}

# 포즈 프리셋 → 워크플로에 넘길 포즈 참조 이미지 파일명
POSE_REFERENCE_MAP: dict[PosePreset, str] = {
    PosePreset.STANDING:  "pose_standing.png",
    PosePreset.SITTING:   "pose_sitting.png",
    PosePreset.WALKING:   "pose_walking.png",
    PosePreset.WAVING:    "pose_waving.png",
    PosePreset.CROUCHING: "pose_crouching.png",
}

# 포즈 레퍼런스 이미지 위치 (ai/workflows/ 폴더에 함께 관리)
POSE_REFS_DIR = Path("ai/workflows/pose_refs")


def apply_pose(
    scene_id: str,
    character_id: str,
    input_image_path: str,
    pose: PosePreset = PosePreset.STANDING,
    expression: ExpressionPreset = ExpressionPreset.NEUTRAL,
    controlnet_strength: float = 0.8,
) -> str:
    """ControlNet으로 포즈·표정을 적용한 이미지를 생성한다.

    Args:
        scene_id:            씬 ID (저장 경로용).
        character_id:        캐릭터 ID (저장 경로용).
        input_image_path:    face_lock.py 출력 이미지 경로.
        pose:                포즈 프리셋. 기본값 STANDING.
        expression:          표정 프리셋. 기본값 NEUTRAL.
        controlnet_strength: ControlNet 적용 강도 (0.0~1.0). 기본값 0.8.

    Returns:
        저장된 이미지의 파일 경로 문자열.

    Example:
        >>> path = apply_pose(
        ...     "scene-001", "abc-123",
        ...     "backend/app/storage/scenes/scene-001_abc-123.png",
        ...     pose=PosePreset.WAVING,
        ...     expression=ExpressionPreset.HAPPY,
        ... )
    """
    input_path = Path(input_image_path)
    if not input_path.exists():
        raise FileNotFoundError(f"입력 이미지 없음: {input_image_path}")

    # 1. 포즈 레퍼런스 이미지 경로
    pose_ref_path = POSE_REFS_DIR / POSE_REFERENCE_MAP[pose]

    # 2. 표정 태그 → 추가 프롬프트
    expression_prompt = EXPRESSION_TAGS[expression]

    # 3. 워크플로 실행 → image bytes → _save_image 저장
    # pose_expression 워크플로(ControlNet)가 아직 ComfyUI에 연결되지 않았다.
    # 연결되면 아래 주석을 풀어 사용한다 (저장 구조 그대로):
    # result = run_workflow(
    #     workflow_name=WORKFLOW_NAME,
    #     inputs={
    #         "input_image":          input_path.read_bytes(),
    #         "pose_reference":       pose_ref_path.read_bytes(),
    #         "expression_prompt":    expression_prompt,
    #         "controlnet_strength":  controlnet_strength,
    #         "negative_prompt":      _NEGATIVE_PROMPT,
    #     },
    # )
    # image_bytes = result["images"][0]
    # suffix = f"{pose.value}_{expression.value}"
    # return str(_save_image(scene_id, character_id, suffix, image_bytes))

    # ⚠️ 아직 미구현: 성공처럼 빈 파일 경로를 반환하지 않고 명시적으로 막는다(연결 전까지).
    raise NotImplementedError(
        "pose_expression 워크플로가 아직 ComfyUI에 연결되지 않았습니다. "
        "run_workflow('pose_expression', inputs) 연결 후 _save_image 로 저장하세요."
    )


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

_NEGATIVE_PROMPT = (
    "ugly, deformed, blurry, low quality, extra limbs, "
    "missing fingers, watermark, text, pose distortion"
)


def _save_image(
    scene_id: str,
    character_id: str,
    suffix: str,
    image_bytes: bytes | None,
) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{scene_id}_{character_id}_{suffix}.png"

    if image_bytes is not None:
        output_path.write_bytes(image_bytes)

    return output_path
