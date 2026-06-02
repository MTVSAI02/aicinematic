"""우리 AI FastAPI 서버 호출 클라이언트 (배경 생성).

구조: Frontend → Backend → **AI FastAPI 서버(/generate-background)** → 외부 ComfyUI
- Backend는 외부 ComfyUI(/prompt·/history·/view)를 직접 호출하지 않는다.
- Backend는 AI 서버에 항상 `{ "prompt": finalPrompt }` 만 보낸다(negativePrompt 안 보냄).
- AI 서버는 **1회 호출로 ComfyUI batch 결과(여러 장)** 를 base64 배열로 반환한다:
      { "images": ["<base64 png>", ...] }
  (개수는 ComfyUI batch가 결정. negative prompt/workflow는 AI 서버 내부 책임.)
"""

import base64
import binascii

import httpx

from ..core.config import AI_REQUEST_HEADERS, AI_SERVER_URL
from ..core.exceptions import AIServerError

# batch로 여러 장 생성하므로 timeout을 넉넉히 둔다(비동기 Job 안에서 호출).
_GENERATE_TIMEOUT_SECONDS = 180


def generate_background_images(prompt: str) -> list[bytes]:
    """AI FastAPI 서버 `/generate-background` 를 1회 호출해 배경 이미지 여러 장을 받는다.

    Args:
        prompt: 최종 프롬프트(finalPrompt). AI 서버에는 항상 'prompt' 필드명으로만 보낸다.

    Returns:
        각 이미지의 raw bytes 목록(개수는 AI/ComfyUI batch 결과에 따름).
        저장/URL/repository는 backend가 담당한다.

    Raises:
        AIServerError: AI_SERVER_URL 미설정 / 연결 실패 / 비정상 응답 / images 누락·디코드 실패.
                       (mock fallback 없음 — 실패를 그대로 Job.error에 드러낸다.)
    """
    if not AI_SERVER_URL or not AI_SERVER_URL.strip():
        raise AIServerError("AI_SERVER_URL is not configured")

    url = f"{AI_SERVER_URL.rstrip('/')}/generate-background"
    try:
        response = httpx.post(
            url, json={"prompt": prompt}, headers=AI_REQUEST_HEADERS, timeout=_GENERATE_TIMEOUT_SECONDS
        )
    except httpx.RequestError as exc:
        raise AIServerError(f"AI server connection failed: {url}") from exc

    if response.status_code != 200:
        raise AIServerError(
            f"AI server returned {response.status_code}: {url}\n{response.text[:200]}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise AIServerError(f"AI server response is not valid JSON: {url}") from exc

    images_b64 = data.get("images") if isinstance(data, dict) else None
    if not isinstance(images_b64, list) or not images_b64:
        raise AIServerError(f"AI server response has no 'images' array: {url}")

    try:
        return [base64.b64decode(b64) for b64 in images_b64]
    except (ValueError, binascii.Error, TypeError) as exc:
        raise AIServerError(f"AI server returned invalid base64 image: {url}") from exc
