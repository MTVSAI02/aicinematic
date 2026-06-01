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
) -> bytes:
    """ControlNet으로 포즈·표정을 적용한 이미지를 생성한다.

    저장 책임 경계: AI는 생성 결과(bytes)만 반환한다. 파일 저장 / `/storage` URL /
    repository 저장은 backend가 담당한다(캐릭터/배경과 동일 계약).

    Args:
        scene_id:            씬 ID (backend 저장 시 파일명용으로 전달).
        character_id:        캐릭터 ID (backend 저장 시 파일명용으로 전달).
        input_image_path:    face_lock.py 출력 이미지 경로.
        pose:                포즈 프리셋. 기본값 STANDING.
        expression:          표정 프리셋. 기본값 NEUTRAL.
        controlnet_strength: ControlNet 적용 강도 (0.0~1.0). 기본값 0.8.

    Returns:
        생성된 이미지의 raw bytes (PNG).
    """
    input_path = Path(input_image_path)
    if not input_path.exists():
        raise FileNotFoundError(f"입력 이미지 없음: {input_image_path}")

    # 1. 포즈 레퍼런스 이미지 경로
    pose_ref_path = POSE_REFS_DIR / POSE_REFERENCE_MAP[pose]

    # 2. 표정 태그 → 추가 프롬프트
    expression_prompt = EXPRESSION_TAGS[expression]

    # 3. 워크플로 실행 → image bytes 반환 (저장은 backend)
    # pose_expression 워크플로(ControlNet)가 아직 ComfyUI에 연결되지 않았다.
    # 연결되면 아래 주석을 풀어 사용한다 (AI는 bytes만 반환, 저장은 backend):
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
    # return result["images"][0]

    # ⚠️ 아직 미구현: 빈 결과를 성공처럼 반환하지 않고 명시적으로 막는다(연결 전까지).
    raise NotImplementedError(
        "pose_expression 워크플로가 아직 ComfyUI에 연결되지 않았습니다. "
        "run_workflow('pose_expression', inputs) 연결 후 result['images'][0](bytes)를 반환하세요."
    )


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

_NEGATIVE_PROMPT = (
    "ugly, deformed, blurry, low quality, extra limbs, "
    "missing fingers, watermark, text, pose distortion"
)


