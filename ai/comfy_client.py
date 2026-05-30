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

import os

import httpx

from .core.exceptions import (
    ComfyUIConfigError,
    ComfyUIConnectionError,
    ComfyUIError,
    ComfyUIResponseError,
    ComfyUITimeoutError,
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
            return timeout_seconds
        env_timeout = os.getenv("COMFYUI_TIMEOUT_SECONDS")
        if env_timeout is None or not env_timeout.strip():
            return DEFAULT_TIMEOUT_SECONDS
        try:
            return int(env_timeout)
        except ValueError as exc:
            raise ComfyUIConfigError(
                f"COMFYUI_TIMEOUT_SECONDS must be an integer, got: {env_timeout!r}"
            ) from exc

    def _get(self, path: str) -> dict:
        """조회용 GET 요청 공통 처리. 외부(httpx) 예외를 공통 예외로 변환한다."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.get(url, timeout=self.timeout_seconds)
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
