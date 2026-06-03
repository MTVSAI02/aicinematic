"""⚠️ 임시 개발용 JSON 스냅샷 (SEED_DEV=1).

in-memory repo(스토리/캐릭터/배경)를 `storage/dev_state.json`에 저장/복원해
**백엔드를 재시작해도** 데이터(및 scene-editor에서 만든 씬-캐릭터/배경 연결)가 유지되게 한다.

- startup: 스냅샷이 있으면 복원, 없으면 dev_seed로 기본값 시드 후 스냅샷 생성
- 변경 요청(POST/PATCH/PUT/DELETE)마다 스냅샷 저장 → kill 로 죽여도 최신 상태 유지
- 스냅샷 파일은 storage/ 안이라 gitignore 대상(커밋 안 됨)
- 초기화하려면 `storage/dev_state.json` 삭제 후 재시작
- 실제 DB/영구 저장이 들어오면 이 파일과 main.py 호출부를 제거한다.

repo의 내부 dict(_*)에 직접 접근하지만, 임시 개발 전용 코드이므로 repo에 영구 API는 추가하지 않는다.
"""

import json

from .config import STORAGE_ROOT
from ..repositories.background_repository import background_repository as _bg
from ..repositories.character_repo import character_repository as _char
from ..repositories.story_repo import story_repository as _story
from ..repositories.tts_audio_repository import tts_audio_repository as _tts

# ⚠️ DB 전환 진행 중: voices 는 PostgreSQL 로 이전됨 → 스냅샷 대상에서 제외.
#    (characters/backgrounds/stories/tts_audios 는 아직 in-memory → 여기서 유지. 구 스냅샷의 voices 키는 무시.)

_SNAPSHOT = STORAGE_ROOT / "dev_state.json"


def save_snapshot() -> None:
    """아직 in-memory 인 repo 상태(레코드 + counter)를 JSON으로 덤프한다. (voices 제외 — DB)"""
    data = {
        "characters": _char._characters,
        "characters_counter": _char._counter,
        "backgrounds": _bg._backgrounds,
        "backgrounds_counter": _bg._counter,
        "stories": _story._stories,
        "stories_counter": _story._counter,
        "tts_audios": _tts._audios,
        "tts_audios_counter": _tts._counter,
    }
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    _SNAPSHOT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_snapshot() -> bool:
    """스냅샷이 있으면 in-memory repo에 복원한다. 복원하면 True. (voices 는 DB라 무시)"""
    if not _SNAPSHOT.is_file():
        return False
    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    _char._characters = data.get("characters", {})
    _char._counter = data.get("characters_counter", 0)
    _bg._backgrounds = data.get("backgrounds", {})
    _bg._counter = data.get("backgrounds_counter", 0)
    _story._stories = data.get("stories", {})
    _story._counter = data.get("stories_counter", 0)
    if "tts_audios" in data:
        _tts._audios = data.get("tts_audios", {})
        _tts._counter = data.get("tts_audios_counter", 0)
    return True
