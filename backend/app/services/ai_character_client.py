"""우리 AI FastAPI 서버 호출 클라이언트 (캐릭터 생성).

구조: Frontend → Backend → **AI FastAPI 서버(/generate-character)** → 외부 ComfyUI
- Backend는 외부 ComfyUI(/prompt·/history·/view)를 직접 호출하지 않는다.
- Backend는 AI 서버에 항상 `{ "prompt": characterFinalPrompt }` 만 보낸다.
  seed/steps/cfg/model/width/height/negative_prompt 는 보내지 않는다
  (AI 서버/ComfyUI 워크플로 내부 책임).
- AI 서버는 배경과 동일하게 base64 배열로 반환한다: { "images": ["<base64 png>", ...] }.
  캐릭터는 1장만 사용하므로 backend는 images[0] 만 쓴다.
"""

import base64
import binascii

import httpx

from ..core.config import AI_SERVER_URL
from ..core.exceptions import AIServerError

# 캐릭터 1장 생성도 모델/GPU 상황에 따라 길어질 수 있어 timeout을 넉넉히 둔다(비동기 Job 안에서 호출).
_GENERATE_TIMEOUT_SECONDS = 180


def generate_character_image(prompt: str) -> bytes:
    """AI FastAPI 서버 `/generate-character` 를 호출해 캐릭터 이미지 1장을 받는다.

    Args:
        prompt: 최종 프롬프트(characterFinalPrompt). AI 서버에는 항상 'prompt' 필드명으로만 보낸다.

    Returns:
        생성된 이미지의 raw bytes (PNG). 저장/URL/repository는 backend가 담당한다.

    Raises:
        AIServerError: AI_SERVER_URL 미설정 / 연결 실패 / 비정상 응답 / images 누락·디코드 실패.
                       (mock fallback 없음 — 실패를 그대로 Job.error에 드러낸다.)
    """
    if not AI_SERVER_URL or not AI_SERVER_URL.strip():
        raise AIServerError("AI_SERVER_URL is not configured")

    url = f"{AI_SERVER_URL.rstrip('/')}/generate-character"
    try:
        response = httpx.post(
            url, json={"prompt": prompt}, timeout=_GENERATE_TIMEOUT_SECONDS
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

    # 캐릭터는 1장만 사용한다(응답 형식은 배경과 통일하기 위해 images 배열).
    try:
        return base64.b64decode(images_b64[0])
    except (ValueError, binascii.Error, TypeError) as exc:
        raise AIServerError(f"AI server returned invalid base64 image: {url}") from exc
