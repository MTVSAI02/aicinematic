"""도메인별 prefix + ULID 문자열 ID 생성/검증.

- 숫자 PK 안 씀. 모든 테이블 PK = "{prefix}{ULID}" (예: char_01HZX8K9...).
- ULID 는 시간순 정렬 → text PK 라도 인덱스 단편화가 적다(랜덤 UUIDv4 회피).
- ID 생성은 앱/repository 레이어에서(이 모듈). DB default 아님.
- preset voice 등 시스템 고정 ID 는 이 규칙 밖에서 직접 지정한다.
"""

from ulid import ULID

# 도메인 → prefix. (검증·생성 단일 출처)
PREFIX: dict[str, str] = {
    "user": "user_",
    "job": "job_",
    "notification": "notif_",
    "story": "story_",
    "scene": "scene_",
    "scene_character": "scenechar_",
    "character": "char_",
    "pose": "pose_",
    "background": "bg_",
    "voice": "voice_",
    "tts_audio": "audio_",
    "render": "render_",
}


def new_id(domain: str) -> str:
    """'{prefix}{ULID}' 형태의 새 ID. 알 수 없는 도메인이면 KeyError."""
    return f"{PREFIX[domain]}{ULID()}"


def assert_prefix(value: str, domain: str) -> str:
    """value 가 해당 도메인 prefix 로 시작하는지 검증(다른 도메인 ID 오용 방지). 통과하면 그대로 반환."""
    prefix = PREFIX[domain]
    if not (value or "").startswith(prefix):
        raise ValueError(f"id '{value}' 는 '{prefix}' 로 시작해야 합니다 (domain={domain}).")
    return value
