"""원격 ComfyUI 서버와 통신하는 공통 클라이언트.

이번 단계 범위 (중요):
- ComfyUI 서버 URL을 환경변수로 관리한다.
- 원격 ComfyUI 서버 연결 여부를 확인한다.
- ComfyUI의 "조회용" API(GET /system_stats, GET /object_info)만 호출한다.

절대 하지 않는 것:
- 이미지 생성 실행 (POST /prompt 호출 금지)
- workflow JSON 실행
- GET /history, GET /view 호출

캐릭터 생성 모델 방향은 SDXL + IPAdapter 에서
HiDream-I1 + IP-Adapter for Flux 로 변경되었으나,
실제 workflow가 아직 완성되지 않았으므로 이 클라이언트에서는
workflow 실행/이미지 생성을 하지 않는다. (조회용 통로만 제공)
"""

import copy
import json
import os
import random
import time
import urllib.parse
from pathlib import Path

import httpx

from .core.exceptions import (
    ComfyUIConfigError,
    ComfyUIConnectionError,
    ComfyUIError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
    WorkflowLoadError,
    WorkflowMappingError,
)

DEFAULT_TIMEOUT_SECONDS = 10


class ComfyUIClient:
    """ComfyUI 조회용 API 호출을 담당하는 공통 통로.

    나중에 backend JobManager 또는 ai/image, ai/voice 파트에서
    공통으로 재사용할 수 있도록 설계한다.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
    ):
        # base_url 우선순위: 생성자 인자 → COMFYUI_DEFAULT_URL → 없으면 ConfigError
        resolved_url = base_url or os.getenv("COMFYUI_DEFAULT_URL")
        if not resolved_url or not resolved_url.strip():
            raise ComfyUIConfigError("COMFYUI_DEFAULT_URL is not configured")
        self.base_url = resolved_url.rstrip("/")

        # timeout 우선순위: 생성자 인자 → COMFYUI_TIMEOUT_SECONDS → 기본값 10초
        self.timeout_seconds = self._resolve_timeout(timeout_seconds)

    @staticmethod
    def _resolve_timeout(timeout_seconds: int | None) -> int:
        if timeout_seconds is not None:
            resolved = timeout_seconds
        else:
            env_timeout = os.getenv("COMFYUI_TIMEOUT_SECONDS")
            if env_timeout is None or not env_timeout.strip():
                return DEFAULT_TIMEOUT_SECONDS
            try:
                resolved = int(env_timeout)
            except ValueError as exc:
                raise ComfyUIConfigError(
                    f"COMFYUI_TIMEOUT_SECONDS must be an integer, got: {env_timeout!r}"
                ) from exc
        # 0/음수는 httpx에서 예상 밖 동작을 유발하므로 공통 예외로 막는다.
        if resolved <= 0:
            raise ComfyUIConfigError(
                f"timeout must be a positive integer, got: {resolved}"
            )
        return resolved

    # 리버스 프록시가 User-Agent 없으면 403 반환하므로 공통 헤더에 포함
    _DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

    def _get(self, path: str) -> dict:
        """조회용 GET 요청 공통 처리. 외부(httpx) 예외를 공통 예외로 변환한다."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.get(url, headers=self._DEFAULT_HEADERS, timeout=self.timeout_seconds)
        except httpx.TimeoutException as exc:
            raise ComfyUITimeoutError(f"ComfyUI request timed out: GET {url}") from exc
        except httpx.RequestError as exc:
            raise ComfyUIConnectionError(
                f"Failed to connect to ComfyUI server: GET {url}"
            ) from exc

        if response.status_code != 200:
            raise ComfyUIResponseError(
                f"ComfyUI server returned non-200 response "
                f"({response.status_code}): GET {url}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ComfyUIResponseError(
                f"ComfyUI response is not valid JSON: GET {url}"
            ) from exc

        # 조회용 API(/system_stats, /object_info)는 JSON object(dict)를 반환한다.
        # list/str/빈 값 등 예상과 다른 구조면 응답 오류로 처리한다.
        # (이게 없으면 health_check가 이상한 응답에도 ok=True가 될 수 있다.)
        if not isinstance(data, dict):
            raise ComfyUIResponseError(
                f"Unexpected ComfyUI response format (expected JSON object): GET {url}"
            )
        return data

    def get_system_stats(self) -> dict:
        """GET /system_stats — ComfyUI 시스템 상태 조회 (조회 전용)."""
        return self._get("/system_stats")

    def get_object_info(self) -> dict:
        """GET /object_info — ComfyUI 노드/모델 정보 조회 (조회 전용)."""
        return self._get("/object_info")

    def health_check(self) -> dict:
        """연결 확인용. 예외를 그대로 터뜨리지 않고 결과를 dict로 반환한다.

        성공: {"ok": True, "baseUrl": ..., "systemStatsAvailable": True, "objectInfoAvailable": True}
        실패: {"ok": False, "baseUrl": ..., "error": "..."}
        """
        try:
            self.get_system_stats()
            self.get_object_info()
        except ComfyUIError as exc:
            return {"ok": False, "baseUrl": self.base_url, "error": exc.message}

        return {
            "ok": True,
            "baseUrl": self.base_url,
            "systemStatsAvailable": True,
            "objectInfoAvailable": True,
        }

    def is_available(self) -> bool:
        """연결 가능 여부를 bool로 반환한다 (health_check 결과를 감싼다)."""
        return self.health_check().get("ok", False)

    # ── 워크플로 실행 ─────────────────────────────────────────────

    def _post(self, path: str, data: dict) -> dict:
        """POST 요청 공통 처리."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(
                url, json=data, headers=self._DEFAULT_HEADERS, timeout=self.timeout_seconds
            )
        except httpx.TimeoutException as exc:
            raise ComfyUITimeoutError(f"ComfyUI request timed out: POST {url}") from exc
        except httpx.RequestError as exc:
            raise ComfyUIConnectionError(f"Failed to connect: POST {url}") from exc
        if response.status_code != 200:
            raise ComfyUIResponseError(
                f"ComfyUI returned {response.status_code}: POST {url}\n{response.text[:300]}"
            )
        return response.json()

    def queue_prompt(self, workflow: dict) -> str:
        """워크플로를 ComfyUI 큐에 등록하고 prompt_id를 반환한다."""
        result = self._post("/prompt", {"prompt": workflow})
        return result["prompt_id"]

    def wait_for_result(
        self, prompt_id: str, timeout: int = 300, poll_interval: int = 5
    ) -> list[dict]:
        """생성 완료까지 폴링. 완료된 이미지 info dict 목록 반환."""
        start = time.time()
        while time.time() - start < timeout:
            history = self._get(f"/history/{prompt_id}")
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
            response = httpx.get(url, headers=self._DEFAULT_HEADERS, timeout=60)
        except httpx.RequestError as exc:
            raise ComfyUIConnectionError(f"이미지 다운로드 실패: {filename}") from exc
        if response.status_code != 200:
            raise ComfyUIResponseError(f"이미지 다운로드 실패 ({response.status_code}): {filename}")
        return response.content

    # ── workflow / mapping 헬퍼 (범용) ───────────────────────────
    # 파일 로드/주입은 ComfyUI 연결이 필요 없으므로 staticmethod로 둔다.
    # 배경 전용 래퍼는 ai/image/background.py 에 있다.

    @staticmethod
    def load_workflow_json(workflow_path) -> dict:
        """ComfyUI workflow JSON 파일을 읽어 dict로 반환한다. 실행하지 않는다."""
        path = Path(workflow_path)
        if not path.is_file():
            raise WorkflowLoadError(f"Workflow JSON not found: {workflow_path}")
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError) as exc:
            raise WorkflowLoadError(
                f"Workflow JSON is not valid: {workflow_path}"
            ) from exc

    @staticmethod
    def load_mapping_json(mapping_path) -> dict:
        """prompt 주입 위치를 정의한 mapping JSON 파일을 읽어 dict로 반환한다."""
        path = Path(mapping_path)
        if not path.is_file():
            raise WorkflowMappingError(f"Mapping JSON not found: {mapping_path}")
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError) as exc:
            raise WorkflowMappingError(
                f"Mapping JSON is not valid: {mapping_path}"
            ) from exc

    @staticmethod
    def apply_mapping(workflow: dict, mapping: dict, values: dict) -> dict:
        """mapping 기준으로 values(finalPrompt/negativePrompt 등)를 workflow에 주입한다.

        mapping 예: {"finalPrompt": {"nodeId": "6", "path": ["inputs", "text"]}}
        원본 workflow는 변경하지 않고 복사본을 반환한다.
        대상 노드/경로가 없으면 WorkflowMappingError를 발생시킨다.
        """
        result = copy.deepcopy(workflow)
        for key, value in values.items():
            spec = mapping.get(key)
            if not spec or "nodeId" not in spec or not spec.get("path"):
                raise WorkflowMappingError(f"Invalid or missing mapping for '{key}'")

            node_id = spec["nodeId"]
            path = spec["path"]
            if node_id not in result:
                raise WorkflowMappingError(
                    f"Node '{node_id}' not found in workflow (mapping key '{key}')"
                )

            target = result[node_id]
            for step in path[:-1]:
                if not isinstance(target, dict) or step not in target:
                    raise WorkflowMappingError(
                        f"Path {path} not found in node '{node_id}' (mapping key '{key}')"
                    )
                target = target[step]
            # 마지막 key도 반드시 존재해야 한다. (mapping 오타로 새 필드가 생기는 것 방지)
            if not isinstance(target, dict) or path[-1] not in target:
                raise WorkflowMappingError(
                    f"Path {path} not found in node '{node_id}' (mapping key '{key}')"
                )
            target[path[-1]] = value
        return result


# ── 모듈 레벨 API (character.py / face_lock.py 등에서 import해서 사용) ──────────

# character_generate 워크플로 노드 ID (ai/workflows/character_generate.json 기준)
_CHAR_NODE_PROMPT = "171"   # PrimitiveStringMultiline — 사용자 프롬프트
_CHAR_NODE_REFINE = "177"   # PrimitiveBoolean         — Gemma 정제 ON/OFF
_CHAR_NODE_SAMPLER = "108"  # SamplerCustom            — noise_seed

_WORKFLOWS_DIR = Path(__file__).parent / "workflows"


def run_workflow(workflow_name: str, inputs: dict) -> dict:
    """워크플로를 실행하고 결과를 반환한다.

    Args:
        workflow_name: ai/workflows/ 안의 JSON 파일명 (확장자 제외).
                       예) "character_generate"
        inputs:        워크플로별 파라미터 dict.
                       character_generate 기준:
                         - positive_prompt (str) : 생성 프롬프트
                         - seed (int, optional)  : 재현 시드 (생략 시 랜덤)

    Returns:
        {"images": [bytes, ...]}  — 생성된 이미지의 raw bytes 목록
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

    client = ComfyUIClient()
    prompt_id = client.queue_prompt(workflow)
    image_infos = client.wait_for_result(prompt_id)

    image_bytes_list = [
        client.download_image(info["filename"], info.get("subfolder", ""))
        for info in image_infos
    ]
    return {"images": image_bytes_list}
