"""우리 AI FastAPI 서버 호출 클라이언트 (캐릭터 포즈 생성).

구조: Frontend → Backend → **AI FastAPI 서버(/generate-pose)** → 외부 ComfyUI
- 백엔드는 캐릭터의 aiImagePath(AI 서버 로컬 경로)와 pose_prompt 를 보낸다.
- AI 서버는 그 경로의 이미지를 reference 로 새 포즈를 생성해 base64 로 반환한다.
- 응답 base64는 'images'(배열) 또는 'image'(단수) 둘 다 허용(캐릭터 생성과 동일 호환).
"""

import base64
import binascii

import httpx

from ..core.config import AI_REQUEST_HEADERS, AI_SERVER_URL
from ..core.exceptions import AIServerError

_GENERATE_TIMEOUT_SECONDS = 180


def generate_pose_image(image_path: str, pose_prompt: str) -> bytes:
    """AI FastAPI 서버 `/generate-pose` 를 호출해 포즈 이미지 1장(bytes)을 받는다.

    Args:
        image_path: reference 로 쓸 AI 서버 로컬 이미지 경로(캐릭터의 aiImagePath).
        pose_prompt: 포즈 프롬프트.

    Returns:
        생성된 포즈 이미지 raw bytes(PNG). 저장/URL/repository는 backend 담당.

    Raises:
        AIServerError: AI_SERVER_URL 미설정 / 연결 실패 / 비정상 응답 / 이미지 누락·디코드 실패.
    """
    if not AI_SERVER_URL or not AI_SERVER_URL.strip():
        raise AIServerError("AI_SERVER_URL is not configured")

    url = f"{AI_SERVER_URL.rstrip('/')}/generate-pose"
    try:
        response = httpx.post(
            url,
            json={"image_path": image_path, "pose_prompt": pose_prompt},
            headers=AI_REQUEST_HEADERS,
            timeout=_GENERATE_TIMEOUT_SECONDS,
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

    images_b64 = data.get("images")
    b64 = images_b64[0] if isinstance(images_b64, list) and images_b64 else data.get("image")
    if not isinstance(b64, str) or not b64:
        raise AIServerError(f"AI server response has no image (images[]/image): {url}")

    try:
        return base64.b64decode(b64)
    except (ValueError, binascii.Error, TypeError) as exc:
        raise AIServerError(f"AI server returned invalid base64 image: {url}") from exc
