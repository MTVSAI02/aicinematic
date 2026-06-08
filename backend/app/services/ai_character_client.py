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

from ..core.config import AI_REQUEST_HEADERS, AI_SERVER_URL
from ..core.exceptions import AIServerError

# 캐릭터 1장 생성도 모델/GPU 상황에 따라 길어질 수 있어 timeout을 넉넉히 둔다(비동기 Job 안에서 호출).
_GENERATE_TIMEOUT_SECONDS = 180


def generate_character_image(prompt: str) -> tuple[bytes, str | None]:
    """AI FastAPI 서버 `/generate-character` 를 호출해 캐릭터 이미지 1장 + AI 서버 경로를 받는다.

    Args:
        prompt: 최종 프롬프트(characterFinalPrompt). AI 서버에는 항상 'prompt' 필드명으로만 보낸다.

    Returns:
        (image_bytes, ai_image_path):
        - image_bytes: 생성 이미지 raw bytes (PNG). 저장/URL/repository는 backend 담당.
        - ai_image_path: AI 서버 로컬 파일 경로(있으면). 포즈 생성(reference image)용으로 저장. 없으면 None.

    Raises:
        AIServerError: AI_SERVER_URL 미설정 / 연결 실패 / 비정상 응답 / 이미지 누락·디코드 실패.
                       (mock fallback 없음 — 실패를 그대로 Job.error에 드러낸다.)
    """
    if not AI_SERVER_URL or not AI_SERVER_URL.strip():
        raise AIServerError("AI_SERVER_URL is not configured")

    url = f"{AI_SERVER_URL.rstrip('/')}/generate-character"
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

    # base64는 'images'(배열) 또는 'image'(단수) 둘 다 허용(AI 서버 응답 형식 호환).
    images_b64 = data.get("images")
    b64 = images_b64[0] if isinstance(images_b64, list) and images_b64 else data.get("image")
    if not isinstance(b64, str) or not b64:
        raise AIServerError(f"AI server response has no image (images[]/image): {url}")

    # 포즈 생성용 reference 경로(있으면). 형식: image_path 우선, 없으면 None.
    ai_image_path = data.get("image_path") if isinstance(data.get("image_path"), str) else None

    try:
        return base64.b64decode(b64), ai_image_path
    except (ValueError, binascii.Error, TypeError) as exc:
        raise AIServerError(f"AI server returned invalid base64 image: {url}") from exc
