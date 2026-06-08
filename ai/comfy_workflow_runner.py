"""ComfyUI 실제 workflow 실행(생성) 전용 모듈.

AI 모듈 정책(ai/docs/ai_code_review_prompt.md §0): 실제 생성은 허용하되, **연결 확인(health)과 분리**한다.
- 연결 확인(/system_stats, /object_info)은 `comfy_client.ComfyUIClient`(health + 공통 HTTP wrapper).
- 실제 생성(/prompt, /history, /view, run_workflow)은 이 모듈.

저장 책임 경계: 이 모듈은 **이미지 bytes를 반환**한다. 저장(파일/URL/repository)은 backend가 담당한다.
"""

from __future__ import annotations

import random
import time
import urllib.parse
from pathlib import Path

import httpx

from .comfy_client import ComfyUIClient
from .core.exceptions import (
    ComfyUIConnectionError,
    ComfyUIError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    WorkflowMappingError,
)

# character_generate 워크플로 노드 ID (ai/workflows/character_generate.json 기준)
_CHAR_NODE_PROMPT = "171"   # PrimitiveStringMultiline — 사용자 프롬프트
_CHAR_NODE_REFINE = "177"   # PrimitiveBoolean         — Gemma 정제 ON/OFF
_CHAR_NODE_SAMPLER = "108"  # SamplerCustom            — noise_seed

_WORKFLOWS_DIR = Path(__file__).parent / "workflows"
_HEADERS = {"User-Agent": "Mozilla/5.0"}  # 리버스 프록시 403 방지


class ComfyWorkflowRunner:
    """ComfyUI 워크플로 실행 전용. 공통 HTTP wrapper(ComfyUIClient)를 재사용한다."""

    def __init__(self, client: ComfyUIClient | None = None):
        self._client = client or ComfyUIClient()

    @property
    def base_url(self) -> str:
        return self._client.base_url

    def queue_prompt(self, workflow: dict) -> str:
        """워크플로를 ComfyUI 큐에 등록하고 prompt_id를 반환한다. (POST /prompt)"""
        result = self._client.post_json("/prompt", {"prompt": workflow})
        prompt_id = result.get("prompt_id") if isinstance(result, dict) else None
        if not prompt_id:
            raise ComfyUIResponseError(
                f"ComfyUI /prompt 응답에 prompt_id가 없습니다: {str(result)[:200]}"
            )
        return prompt_id

    def wait_for_result(
        self, prompt_id: str, timeout: int = 300, poll_interval: int = 5
    ) -> list[dict]:
        """생성 완료까지 폴링. 완료된 이미지 info dict 목록 반환. (GET /history)"""
        start = time.time()
        while time.time() - start < timeout:
            history = self._client.get_json(f"/history/{prompt_id}")
            if prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {})

                if status.get("status_str") == "error":
                    for msg_type, msg_data in status.get("messages", []):
                        if msg_type == "execution_error":
                            err = msg_data.get("exception_message", "알 수 없는 오류")
                            node = msg_data.get("node_type", "?")
                            raise ComfyUIError(
                                f"ComfyUI 실행 오류 [{node}]: {err.strip()}"
                            )

                outputs = entry.get("outputs", {})
                images = []
                for node_output in outputs.values():
                    if "images" in node_output:
                        images.extend(node_output["images"])
                return images

            time.sleep(poll_interval)

        raise ComfyUITimeoutError(f"생성 시간 초과 ({timeout}초)")

    def download_image(self, filename: str, subfolder: str = "") -> bytes:
        """GET /view — 생성된 이미지를 bytes로 다운로드한다."""
        url = (
            f"{self.base_url}/view"
            f"?filename={urllib.parse.quote(filename)}"
            f"&subfolder={subfolder}&type=output"
        )
        try:
            response = httpx.get(url, headers=_HEADERS, timeout=60)
        except httpx.TimeoutException as exc:
            # 공통 client(get_json/post_json)와 동일하게 timeout을 connection error와 분리한다.
            raise ComfyUITimeoutError(f"이미지 다운로드 시간 초과: {filename}") from exc
        except httpx.RequestError as exc:
            raise ComfyUIConnectionError(f"이미지 다운로드 실패: {filename}") from exc
        if response.status_code != 200:
            raise ComfyUIResponseError(
                f"이미지 다운로드 실패 ({response.status_code}): {filename}"
            )
        return response.content


def run_workflow(workflow_name: str, inputs: dict) -> dict:
    """워크플로를 실행하고 결과(이미지 bytes 목록)를 반환한다.

    Args:
        workflow_name: ai/workflows/ 안의 JSON 파일명 (확장자 제외). 예) "character_generate"
        inputs:        워크플로별 파라미터 dict.
                       character_generate 기준: positive_prompt(str), seed(int, optional)

    Returns:
        {"images": [bytes, ...]}  — 생성된 이미지의 raw bytes 목록
        (저장은 하지 않는다. backend가 storage 경로/URL/repository를 담당한다.)
    """
    workflow_path = _WORKFLOWS_DIR / f"{workflow_name}.json"
    workflow = ComfyUIClient.load_workflow_json(workflow_path)

    if workflow_name == "character_generate":
        workflow[_CHAR_NODE_PROMPT]["inputs"]["value"] = inputs.get("positive_prompt", "")
        workflow[_CHAR_NODE_REFINE]["inputs"]["value"] = False  # 영어 프롬프트 직접 사용
        workflow[_CHAR_NODE_SAMPLER]["inputs"]["noise_seed"] = inputs.get(
            "seed", random.randint(0, 2**32 - 1)
        )
    else:
        raise WorkflowMappingError(f"지원하지 않는 워크플로: {workflow_name}")

    runner = ComfyWorkflowRunner()
    prompt_id = runner.queue_prompt(workflow)
    image_infos = runner.wait_for_result(prompt_id)
    image_bytes_list = [
        runner.download_image(info["filename"], info.get("subfolder", ""))
        for info in image_infos
    ]
    return {"images": image_bytes_list}
