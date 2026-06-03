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

# ⚠️ DB 전환 거의 완료: voices·characters·backgrounds·stories·tts_audios 모두 PostgreSQL 로 이전됨.
#    더 이상 in-memory 스냅샷 대상이 없다 → save/load 는 no-op(파일은 마이그레이션 소스로만 보존).
#    (이 파일과 호출부는 dev_persist 완전 제거 단계에서 삭제 예정.)

_SNAPSHOT = STORAGE_ROOT / "dev_state.json"


def save_snapshot() -> None:
    """no-op. (모든 도메인 DB 이전 — 스냅샷할 in-memory 상태 없음. dev_state.json 은 덮어쓰지 않음.)"""
    return None


def load_snapshot() -> bool:
    """스냅샷 파일 존재 여부만 반환한다(있으면 dev_seed 기본 시드를 건너뛰는 신호). 복원 동작은 없음."""
    return _SNAPSHOT.is_file()


def migrate_devstate_characters_to_db() -> int:
    """dev_state.json 의 characters 를 같은 ID로 DB 에 1회 이관(idempotent).

    in-memory 스토리(scene.characters)의 characterId 참조를 보존하기 위함.
    voiceId 가 DB voices 에 없으면 None 으로(존재하지 않는 보이스 FK 위반 방지).
    """
    if not _SNAPSHOT.is_file():
        return 0
    from ..repositories.character_repo import character_repository as _char_db
    from ..repositories.voice_repository import voice_repository as _voice_db

    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    migrated = 0
    for cid, ch in (data.get("characters") or {}).items():
        if _char_db.get(cid) is not None:
            continue
        vid = ch.get("voiceId")
        if vid and _voice_db.get(vid) is None:
            vid = None  # DB 에 없는 보이스 참조 → 끊고 이관(나중에 재연결)
        _char_db.create(cid, {**ch, "voiceId": vid, "legacyId": cid})
        migrated += 1
    return migrated


def migrate_devstate_backgrounds_to_db() -> int:
    """dev_state.json 의 backgrounds 를 같은 ID로 DB 에 1회 이관(idempotent).

    in-memory 스토리(scene.backgroundId)의 참조 보존용.
    """
    if not _SNAPSHOT.is_file():
        return 0
    from ..repositories.background_repository import background_repository as _bg_db

    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    migrated = 0
    for bid, bg in (data.get("backgrounds") or {}).items():
        if _bg_db.get(bid) is not None:
            continue
        _bg_db.create(bid, {**bg, "legacyId": bid})
        migrated += 1
    return migrated


def migrate_devstate_stories_to_db() -> int:
    """dev_state.json 의 stories(+scenes+scene_characters+lastRender)를 같은 ID로 DB 에 1회 이관.

    FK 가드: narratorVoiceId / scene.backgroundId / scene.characters[].characterId / poseId 가
    DB 에 없으면 None 처리하거나 제외해 무결성 위반을 막는다. (idempotent — 이미 있으면 건너뜀)
    """
    if not _SNAPSHOT.is_file():
        return 0
    from ..repositories.story_repo import story_repository as _story_db
    from ..repositories.voice_repository import voice_repository as _voice_db
    from ..repositories.character_repo import character_repository as _char_db
    from ..repositories.background_repository import background_repository as _bg_db

    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    migrated = 0
    for sid, story in (data.get("stories") or {}).items():
        if _story_db.get(sid) is not None:
            continue

        narrator_id = story.get("narratorVoiceId")
        if narrator_id and _voice_db.get(narrator_id) is None:
            narrator_id = None

        scenes = []
        for sc in story.get("scenes") or []:
            bg_id = sc.get("backgroundId")
            if bg_id and _bg_db.get(bg_id) is None:
                bg_id = None
            chars = []
            for ch in sc.get("characters") or []:
                char = _char_db.get(ch.get("characterId"))
                if char is None:
                    continue  # DB 에 없는 캐릭터 참조 → 제외(FK)
                pose_id = ch.get("poseId")
                if pose_id and not any(p.get("poseId") == pose_id for p in char.get("poses") or []):
                    pose_id = None
                chars.append({**ch, "poseId": pose_id})
            scenes.append({**sc, "backgroundId": bg_id, "characters": chars})

        _story_db.save({
            "storyId": sid,
            "legacyId": sid,
            "title": story.get("title"),
            "narratorVoiceId": narrator_id,
            "voiceLocks": story.get("voiceLocks") or {},
            "scenes": scenes,
        })
        last = story.get("lastRender")
        if last and last.get("videoUrl"):
            _story_db.set_last_render(sid, last)
        migrated += 1
    return migrated


def migrate_devstate_tts_to_db() -> int:
    """dev_state.json 의 tts_audios 를 같은 audioId 로 DB 에 1회 이관(idempotent).

    sceneId(scene_001)→scenes.id(ULID) 해소, voiceId 가 DB 에 없으면 None(FK 가드).
    story/scene 이 DB 에 없으면(해소 불가) 건너뜀. (스토리 이관 뒤 호출)
    """
    if not _SNAPSHOT.is_file():
        return 0
    from ..repositories.tts_audio_repository import tts_audio_repository as _tts_db
    from ..repositories.story_repo import story_repository as _story_db
    from ..repositories.voice_repository import voice_repository as _voice_db

    data = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    migrated = 0
    for aid, a in (data.get("tts_audios") or {}).items():
        if _tts_db.get(aid) is not None:
            continue
        scene_pk = _story_db.resolve_scene_pk(a.get("storyId"), a.get("sceneId"))
        if scene_pk is None:
            continue
        vid = a.get("voiceId")
        if vid and _voice_db.get(vid) is None:
            vid = None
        _tts_db.create_one_fixed(aid, {**a, "voiceId": vid}, scene_pk)
        migrated += 1
    return migrated
