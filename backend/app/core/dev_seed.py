"""⚠️ 임시 개발용 시드 (SEED_DEV=1).

ComfyUI/AI 서버 없이 scene-editor 흐름을 테스트하기 위해, storage 폴더에 직접 넣어둔
이미지로 캐릭터/배경/가라 스토리 레코드를 만든다.

- main.py startup이 dev_persist 스냅샷(storage/dev_state.json)을 먼저 시도하고,
  스냅샷이 없을 때만 이 기본값 시드를 실행한다.
  즉 첫 실행 → 이 시드 → dev_state.json 생성, 이후 재시작 → 스냅샷에서 복원(시드 안 함).
- 따라서 scene-editor 연결/배치 등 모든 변경은 dev_state.json 으로 **백엔드 재시작에도 유지**된다.
  (초기화하려면 storage/dev_state.json 삭제 후 재시작 → 다시 이 기본값으로 시드)
- 실제 생성 흐름이 안정화되면 이 파일과 main.py의 호출부를 제거한다. (TEMP_DEV_SEED.md)
"""

from .config import (
    BACKGROUND_LIBRARY_STORAGE_DIR,
    CHARACTER_STORAGE_DIR,
    storage_url,
)
from ..repositories.background_repository import background_repository
from ..repositories.character_repo import character_repository
from ..services.story_service import story_service

# storage에 직접 넣어둔 파일 기준. 파일이 없으면 그 항목은 건너뛴다.
_CHARACTERS = [
    {
        "file": "little_prince.png",
        "name": "어린왕자",
        "appearancePrompt": "golden blond hair, green coat, small scarf, gentle eyes, storybook character",
        "description": "작은 별에서 온 호기심 많고 다정한 소년",
    },
    {
        "file": "fennec_fox.png",
        "name": "여우",
        "appearancePrompt": "small orange fox, soft fluffy fur, gentle eyes, storybook animal",
        "description": "어린왕자와 친구가 되는 따뜻한 작은 여우",
    },
]

_BACKGROUNDS = [
    {
        "file": "background1.png",
        "name": "사막과 노을 배경",
        "prompt": "조용한 사막, 노을",
        "finalPrompt": "조용한 사막, 노을, storybook background, background only, no characters",
    },
]

_STORY = {
    "title": "어린 왕자 (테스트)",
    "script": (
        "[잔잔함] 어린왕자는 작은 별 위에 앉아 노을을 바라보고 있었다.\n"
        "하늘은 금빛과 보라빛으로 천천히 물들고 있었다.\n\n"
        '[다정함] 어린왕자: "안녕, 너는 어디에서 왔니?"\n\n'
        "작은 여우는 모래 언덕 뒤에서 조심스럽게 걸어 나왔다.\n\n"
        '[기쁨] 여우: "나는 친구를 찾고 있었어."\n\n'
        "두 친구는 별빛이 떠오르는 사막을 함께 걸어갔다."
    ),
}


def seed_dev_data() -> None:
    """in-memory repo에 테스트용 캐릭터/배경/스토리를 채운다.

    이미 시드되어 있으면(같은 프로세스에서 중복 호출) 다시 만들지 않는다.
    파일이 실제로 storage에 있어야만 해당 레코드를 만든다.
    """
    if not (character_repository.list() or background_repository.list()):
        for c in _CHARACTERS:
            if not (CHARACTER_STORAGE_DIR / c["file"]).is_file():
                continue
            cid = character_repository.reserve_id()
            character_repository.create(
                cid,
                {
                    "name": c["name"],
                    "appearancePrompt": c["appearancePrompt"],
                    "description": c["description"],
                    "imageUrl": storage_url("characters", c["file"]),
                },
            )

        for b in _BACKGROUNDS:
            if not (BACKGROUND_LIBRARY_STORAGE_DIR / b["file"]).is_file():
                continue
            bid = background_repository.reserve_id()
            background_repository.create(
                bid,
                {
                    "name": b["name"],
                    "prompt": b["prompt"],
                    "finalPrompt": b["finalPrompt"],
                    "imageUrl": storage_url("backgrounds", "library", b["file"]),
                },
            )

    # 가라 스토리(씬 자동 생성) — scene-editor에서 스토리/씬을 고를 수 있게.
    if not story_service.list_stories():
        story_service.parse_and_save(_STORY["title"], _STORY["script"])
