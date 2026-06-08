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


def generate_background_image(prompt: str) -> tuple[bytes, str | None]:
    """AI FastAPI 서버 `/generate-background` 를 1회 호출해 배경 이미지 1장 + AI 서버 경로를 받는다.

    응답 형식(둘 다 호환):
      - 신: { "image": "<base64>", "image_path": "/.../bg.png" }  (단일 — 현행 AI 서버)
      - 구: { "images": ["<base64>", ...] }                       (배열 — 첫 장만 사용)

    Args:
        prompt: 최종 프롬프트(finalPrompt). AI 서버에는 항상 'prompt' 필드명으로만 보낸다.

    Returns:
        (image_bytes, ai_image_path) — 이미지 raw bytes + AI 서버 원본 경로(없으면 None).
        저장/URL/repository는 backend가 담당한다.

    Raises:
        AIServerError: AI_SERVER_URL 미설정 / 연결 실패 / 비정상 응답 / image 누락·디코드 실패.
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

    if not isinstance(data, dict):
        raise AIServerError(f"AI server response is not an object: {url}")

    # base64는 'images'(배열, 첫 장) 또는 'image'(단수) 둘 다 허용.
    images_b64 = data.get("images")
    b64 = images_b64[0] if isinstance(images_b64, list) and images_b64 else data.get("image")
    if not isinstance(b64, str) or not b64:
        raise AIServerError(f"AI server response has no image (images[]/image): {url}")

    # AI 서버 원본 경로(있으면 보관 — 확장 대비, 배경엔 현재 미사용).
    ai_image_path = data.get("image_path") if isinstance(data.get("image_path"), str) else None

    try:
        return base64.b64decode(b64), ai_image_path
    except (ValueError, binascii.Error, TypeError) as exc:
        raise AIServerError(f"AI server returned invalid base64 image: {url}") from exc
