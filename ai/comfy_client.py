"""원격 ComfyUI 서버 연결 확인 + 공통 HTTP wrapper.

AI 모듈 정책(ai/docs/ai_code_review_prompt.md §0):
- 이 클라이언트는 **연결 확인(/system_stats, /object_info)** 과 **공통 HTTP wrapper(get_json/post_json)** 까지 담당한다.
- 실제 생성(/prompt, /history, /view, run_workflow)은 **분리된** `comfy_workflow_runner.py` 가 담당한다.
  (workflow runner가 이 클라이언트의 post_json/get_json 을 재사용한다.)
- 저장 책임 경계: AI는 결과(bytes)만 반환하고, 저장/URL/repository는 backend가 한다.
"""

import copy
import json
import os
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
    """ComfyUI 연결 확인 + 공통 HTTP wrapper.

    health check(get_system_stats/object_info/health_check)와
    공통 HTTP 호출(get_json/post_json)을 제공한다.
    실제 생성은 comfy_workflow_runner.ComfyWorkflowRunner 가 이 클라이언트를 재사용해 수행한다.
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

    # ── 공통 HTTP wrapper (health + workflow runner 가 함께 재사용) ────────────

    def get_json(self, path: str) -> dict:
        """GET 요청 공통 처리. 외부(httpx) 예외/이상 응답을 공통 예외로 변환한다."""
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

        # 조회용 API(/system_stats, /object_info, /history)는 JSON object(dict)를 반환한다.
        if not isinstance(data, dict):
            raise ComfyUIResponseError(
                f"Unexpected ComfyUI response format (expected JSON object): GET {url}"
            )
        return data

    def post_json(self, path: str, data: dict) -> dict:
        """POST 요청 공통 처리. 외부(httpx) 예외/이상 응답을 공통 예외로 변환한다."""
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

        # JSON 파싱 실패도 공통 예외로 정리 (generic failed 로 뭉개지지 않게)
        try:
            result = response.json()
        except ValueError as exc:
            raise ComfyUIResponseError(
                f"ComfyUI response is not valid JSON: POST {url}"
            ) from exc
        if not isinstance(result, dict):
            raise ComfyUIResponseError(
                f"Unexpected ComfyUI response format (expected JSON object): POST {url}"
            )
        return result

    # ── 연결 확인 (health) ───────────────────────────────────────

    def get_system_stats(self) -> dict:
        """GET /system_stats — ComfyUI 시스템 상태 조회 (조회 전용)."""
        return self.get_json("/system_stats")

    def get_object_info(self) -> dict:
        """GET /object_info — ComfyUI 노드/모델 정보 조회 (조회 전용)."""
        return self.get_json("/object_info")

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

    # ── workflow / mapping 헬퍼 (범용, 연결 불필요) ──────────────────
    # 파일 로드/주입은 ComfyUI 연결이 필요 없으므로 staticmethod로 둔다.

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
