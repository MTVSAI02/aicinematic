"""배경 생성용 ComfyUI 연동 진입점 (연결 준비 단계).

이번 단계 범위 (중요):
- 배경용 workflow JSON / mapping JSON 로드
- finalPrompt / negativePrompt 를 workflow 에 주입할 payload 구성

절대 하지 않는 것:
- 실제 이미지 생성 (POST /prompt 실행 / workflow 실행)
- 결과 이미지 저장, candidateId / backgroundId 생성, scene 연결
- 이미지 개수 강제 (count/numImages/batch size) — 개수는 ComfyUI workflow 가 결정한다.

원칙:
- AI 는 prompt 작성자가 아니라 주입자다. 백엔드가 만든 finalPrompt / negativePrompt 를
  그대로 받아 workflow 에 꽂을 준비만 한다.
- 배경은 background only / no characters / no people / no animals.
"""

from pathlib import Path

from ..comfy_client import ComfyUIClient
from ..core.exceptions import BackgroundWorkflowPrepareError

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"
BACKGROUND_WORKFLOW_PATH = WORKFLOWS_DIR / "background_generate.json"
BACKGROUND_MAPPING_PATH = WORKFLOWS_DIR / "background_generate_mapping.json"


def load_background_workflow() -> dict:
    """배경 workflow JSON 을 로드한다. (실행하지 않음)"""
    return ComfyUIClient.load_workflow_json(BACKGROUND_WORKFLOW_PATH)


def load_background_mapping() -> dict:
    """배경 mapping JSON 을 로드한다."""
    return ComfyUIClient.load_mapping_json(BACKGROUND_MAPPING_PATH)


def _is_placeholder_workflow(workflow: dict) -> bool:
    """실제 workflow 가 아직 placeholder 인지 판단한다.

    placeholder 는 {"_comment": "..."} 형태이고 실제 노드(dict)가 없다.
    """
    real_nodes = [v for v in workflow.values() if isinstance(v, dict)]
    return len(real_nodes) == 0


def build_background_workflow_payload(finalPrompt: str, negativePrompt: str) -> dict:
    """finalPrompt / negativePrompt 를 배경 workflow 에 주입할 payload 를 준비한다.

    - 실제 생성은 하지 않는다. "실행 준비용 payload 생성"까지만 한다.
    - workflow 가 아직 placeholder 면 주입을 보류하고 준비 정보만 반환한다(workflowReady=False).
      실제 workflow JSON 으로 교체되면 그때 자동으로 주입된다(workflowReady=True).
    """
    if not finalPrompt or not finalPrompt.strip():
        raise BackgroundWorkflowPrepareError("finalPrompt is empty")
    if not negativePrompt or not negativePrompt.strip():
        raise BackgroundWorkflowPrepareError("negativePrompt is empty")

    workflow = load_background_workflow()
    mapping = load_background_mapping()
    values = {"finalPrompt": finalPrompt, "negativePrompt": negativePrompt}

    if _is_placeholder_workflow(workflow):
        # 실제 workflow 미완성 → 주입 보류, 준비 정보만 반환
        return {
            "workflowReady": False,
            "values": values,
            "mapping": mapping,
            "note": "placeholder workflow — prompt not injected yet (replace background_generate.json)",
        }

    injected = ComfyUIClient.apply_mapping(workflow, mapping, values)
    return {"workflowReady": True, "workflow": injected}


# 선택적 별칭: prepare 의미를 더 분명히 드러내고 싶을 때 사용한다.
def prepare_background_generation(finalPrompt: str, negativePrompt: str) -> dict:
    """배경 생성을 위한 준비(payload 구성)까지만 수행한다. 실제 생성은 하지 않는다."""
    return build_background_workflow_payload(finalPrompt, negativePrompt)
