"""타임라인 비즈니스 로직.

- story 단위로 scene order/duration 을 조회/저장한다.
- 멀티트랙 편집기가 아니라 스토리보드 기반(순서 재정렬 + duration 조절)이다.
- Voice/TTS, ffmpeg 렌더링은 이번 범위 아님. render plan 은 "2차 ffmpeg 가 그대로 쓸 데이터"까지만 만든다.
"""

import logging
import wave

from ..core.config import storage_path
from ..core.exceptions import (
    CueTimingValidationError,
    SceneNotFoundError,
    StoryNotFoundError,
    TimelineValidationError,
)
from ..repositories.background_repository import background_repository
from ..repositories.character_repo import character_repository
from ..repositories.story_repo import story_repository
from ..repositories.tts_audio_repository import tts_audio_repository
from ..repositories.voice_repository import voice_repository
from .image_resolve import resolve_character_display_image
from .text_overlay_service import build_text_overlays

logger = logging.getLogger(__name__)

DEFAULT_DURATION = 3.0
_TEXT_PREVIEW_MAX = 80


def _wav_duration_sec(audio_url: str | None) -> float | None:
    """/storage 의 wav 파일에서 실제 재생 길이(초)를 계산한다.

    AI /tts 가 durationSec 을 null 로 주는 동안 백엔드가 직접 길이를 구한다(자막↔음성 길이 비교/맞추기용).
    파일이 없거나 PCM wav 가 아니면 None.
    """
    if not audio_url:
        return None
    path = storage_path(audio_url)
    if not path or not path.is_file():
        return None
    try:
        with wave.open(str(path), "rb") as wf:
            rate = wf.getframerate()
            if rate:
                return round(wf.getnframes() / float(rate), 3)
    except Exception as exc:  # noqa: BLE001 - 비표준 wav 등은 None 으로 무시
        logger.warning("wav 길이 계산 실패(%s): %s", audio_url, exc)
    return None


def _duration_of(scene: dict) -> float:
    """duration 이 없거나 비정상이면 기본값(3.0)으로 보정해 읽는다."""
    d = scene.get("duration")
    return float(d) if isinstance(d, (int, float)) and d > 0 else DEFAULT_DURATION


def _text_preview(scene: dict) -> str:
    """타임라인 카드용 짧은 문장: 첫 narration → 없으면 첫 dialogue → 없으면 ''. 80자 컷."""
    items = scene.get("items") or []
    narration = next((i for i in items if i.get("type") == "narration" and i.get("text")), None)
    chosen = narration or next((i for i in items if i.get("text")), None)
    text = (chosen or {}).get("text", "") or ""
    return text[:_TEXT_PREVIEW_MAX]


def _ready_status(scene: dict) -> dict:
    items = scene.get("items") or []
    return {
        "hasBackground": scene.get("backgroundId") is not None,
        "hasCharacters": len(scene.get("characters") or []) > 0,
        "hasText": any((i.get("text") or "").strip() for i in items),
    }


class TimelineService:
    def __init__(self, story_repo, background_repo, character_repo, tts_audio_repo, voice_repo):
        self._story_repo = story_repo
        self._background_repo = background_repo
        self._character_repo = character_repo
        self._tts_audio_repo = tts_audio_repo
        self._voice_repo = voice_repo

    def _get_story_or_404(self, story_id: str) -> dict:
        story = self._story_repo.get(story_id)
        if story is None:
            raise StoryNotFoundError()
        return story

    def _sorted_scenes(self, story: dict) -> list[dict]:
        return sorted(story.get("scenes", []), key=lambda s: s.get("order", 0))

    def _background_summary(self, scene: dict) -> dict | None:
        bg_id = scene.get("backgroundId")
        if not bg_id:
            return None
        bg = self._background_repo.get(bg_id)
        return {"backgroundId": bg_id, "imageUrl": (bg or {}).get("imageUrl")}

    def _character_summaries(self, scene: dict) -> list[dict]:
        result = []
        for ch in scene.get("characters") or []:
            char = self._character_repo.get(ch.get("characterId"))
            if char is None:
                continue  # 라이브러리에서 삭제된 캐릭터는 타임라인 요약에서 제외
            result.append(
                {
                    "characterId": char.get("characterId"),
                    "name": char.get("name"),
                    "imageUrl": resolve_character_display_image(char, ch.get("poseId")),  # 포즈 적용 시 포즈 이미지
                    "layout": ch.get("layout"),  # 합성 미리보기용 배치(씬-캐릭터 항목에 저장됨)
                }
            )
        return result

    def _voice_name(self, voice_id: str | None) -> str | None:
        if not voice_id:
            return None
        voice = self._voice_repo.get(voice_id)
        return voice.get("name") if voice else None

    def _item_tts_status(
        self, story: dict, item_type: str | None, character_id: str | None, audio_url: str | None
    ) -> str:
        """item 의 TTS 상태. audio 있으면 ready, 없으면 그 대상(나레이션/캐릭터) 잠금 상태에서 도출."""
        if audio_url:
            return "ready"
        locks = story.get("voiceLocks", {})
        state = locks.get("narration") if item_type == "narration" else (
            locks.get(character_id) if character_id else None
        )
        st = (state or {}).get("ttsStatus")
        return st if st in ("generating", "failed", "stale") else "none"

    def _build_cue_item(self, story, scene_id, overlay, audios_by_item, chars_by_name) -> dict:
        """cue 안 한 줄(sourceItem) → audio/화자/보이스 정보. itemIndex 로 tts_audio 매칭."""
        idx = overlay["sourceItemIndex"]
        item_type = overlay.get("type")
        speaker = overlay.get("speaker")
        audio = audios_by_item.get(idx)
        audio_url = audio.get("audioUrl") if audio else None

        if item_type == "narration":
            display_name = "나레이션"
            character_id = None
            character_image = None
            voice_id = story.get("narratorVoiceId")
        else:
            char = chars_by_name.get(speaker)
            display_name = speaker
            character_id = char.get("characterId") if char else None
            character_image = resolve_character_display_image(char, None) if char else None
            voice_id = char.get("voiceId") if char else None

        voice_name = (audio.get("voiceName") if audio else None) or self._voice_name(voice_id)
        return {
            "sourceItemIndex": idx,
            "type": item_type,
            "speaker": speaker,
            "displayName": display_name,
            "characterId": character_id,
            "characterImageUrl": character_image,
            "voiceId": voice_id,
            "voiceName": voice_name,
            "audioId": audio.get("audioId") if audio else None,
            "audioUrl": audio_url,
            "audioDurationSec": _wav_duration_sec(audio_url),
            "ttsStatus": self._item_tts_status(story, item_type, character_id, audio_url),
            "text": overlay.get("text"),
        }

    def _cue_timings(self, story: dict, scene: dict) -> list[dict]:
        """cue 그룹별 타이밍 + items[](줄별 TTS). 매칭: cueOrder → sourceItemIndex → tts_audio(itemIndex).

        cue 엔 cueId/cueOrder/startSec/durationSec 만. 텍스트/화자/음성은 items[] 단위.
        startSec/durationSec 는 저장값 있으면 사용, 없으면 씬 duration 균등 분할.
        """
        story_id = story.get("storyId")
        scene_id = scene.get("sceneId")
        by_cue: dict = {}
        for o in build_text_overlays(scene):
            by_cue.setdefault(o["cueOrder"], []).append(o)
        for group in by_cue.values():
            group.sort(key=lambda o: o["sourceItemIndex"])
        cue_orders = sorted(by_cue)

        stored = {ct.get("cueOrder"): ct for ct in scene.get("cueTimings") or []}
        audios_by_item = {
            a.get("itemIndex"): a for a in self._tts_audio_repo.list_by_scene(story_id, scene_id)
        }
        chars_by_name = {c.get("name"): c for c in self._character_repo.list() if c.get("name")}
        dur = _duration_of(scene)
        n = len(cue_orders)
        result = []
        for i, co in enumerate(cue_orders):
            items = [
                self._build_cue_item(story, scene_id, o, audios_by_item, chars_by_name)
                for o in by_cue[co]
            ]
            s = stored.get(co)
            if s:
                start, length = float(s.get("startSec", 0.0)), float(s.get("durationSec", 0.0))
            else:
                length = round(dur / n, 3) if n else dur
                start = round(i * length, 3)
            result.append(
                {
                    "cueId": f"{scene_id}_cue_{co:03d}",
                    "cueOrder": co,
                    "startSec": start,
                    "durationSec": length,
                    "items": items,
                }
            )
        return result

    @staticmethod
    def _scene_audio_status(cue_timings: list[dict]) -> str:
        """씬 음성 상태: failed > generating > ready(전부 audio) > none."""
        statuses = [it.get("ttsStatus") for c in cue_timings for it in c.get("items", [])]
        if not statuses:
            return "none"
        if any(s == "failed" for s in statuses):
            return "failed"
        if any(s == "generating" for s in statuses):
            return "generating"
        if all(s == "ready" for s in statuses):
            return "ready"
        return "none"

    def _scene_response(self, story: dict, scene: dict) -> dict:
        cue_timings = self._cue_timings(story, scene)
        ready = _ready_status(scene)
        audio_status = self._scene_audio_status(cue_timings)
        ready["hasAudio"] = audio_status == "ready"
        ready["audioStatus"] = audio_status
        return {
            "sceneId": scene.get("sceneId"),
            "order": scene.get("order"),
            "duration": _duration_of(scene),
            "textPreview": _text_preview(scene),
            "background": self._background_summary(scene),
            "characters": self._character_summaries(scene),
            "textOverlays": build_text_overlays(scene),
            "cueTimings": cue_timings,
            "readyStatus": ready,
        }

    # ── 조회 ──────────────────────────────────────────────
    def get_timeline(self, story_id: str) -> dict:
        story = self._get_story_or_404(story_id)
        scenes = [self._scene_response(story, s) for s in self._sorted_scenes(story)]
        total = round(sum(s["duration"] for s in scenes), 3)
        return {"storyId": story_id, "totalDuration": total, "scenes": scenes}

    # ── 저장 ──────────────────────────────────────────────
    def update_timeline(self, story_id: str, scene_updates: list) -> dict:
        """전체 scene 목록을 받아 각 scene 의 재생 길이(duration)와 cue 타이밍을 저장한다.

        - 순서(order)는 스토리 원본 그대로 유지한다(타임라인은 재배치하지 않음).
        - 요청은 story 의 모든 scene 을 정확히 한 번씩 포함해야 한다(누락/초과/중복 → 400).
        - 존재하지 않는 sceneId → 404. duration/cue 범위는 Pydantic Field(422)에서 막힘.
        - **원자적(atomic)**: 모든 scene 을 먼저 검증한 뒤 한 번에 반영한다.
          한 scene 이라도 실패하면 아무 scene 도 바뀌지 않는다(부분 반영 방지).
        """
        story = self._get_story_or_404(story_id)
        story_scenes = {s.get("sceneId"): s for s in story.get("scenes", [])}

        req_ids = [su.sceneId for su in scene_updates]
        # 존재하지 않는 sceneId
        for sid in req_ids:
            if sid not in story_scenes:
                raise SceneNotFoundError()
        # 전체 목록 정확히 1번씩 (중복/누락/초과 방지)
        if len(req_ids) != len(set(req_ids)) or set(req_ids) != set(story_scenes.keys()):
            raise TimelineValidationError()

        # 1) 검증 + 적용값 계산만 (아직 scene 에 쓰지 않음). 실패하면 여기서 raise → 반영 0건.
        planned = []  # (scene, new_duration, new_cue_timings | None)
        for su in scene_updates:
            scene = story_scenes[su.sceneId]
            new_duration = float(su.duration)
            if su.cueTimings is not None:
                new_cues = self._validate_cue_timings(scene, new_duration, su.cueTimings)
            else:
                # cueTimings 미전송: 기존 저장값을 새 duration 안으로 클램프(초과분 정리 → render-plan 일관성)
                new_cues = self._clamp_stored_cue_timings(scene, new_duration)
            planned.append((scene, new_duration, new_cues))

        # 2) 검증 통과 후 한 번에 반영. order/텍스트/배치는 안 건드림. dev_persist 로 유지.
        for scene, new_duration, new_cues in planned:
            scene["duration"] = new_duration
            if new_cues is not None:
                scene["cueTimings"] = new_cues

        return self.get_timeline(story_id)

    def _validate_cue_timings(self, scene: dict, duration: float, cue_timings: list) -> list[dict]:
        """cue 타이밍 검증 후 저장할 list 를 반환(검증 실패 시 400). startSec/durationSec 범위는 Field(422)에서."""
        valid_cues = {o["cueOrder"] for o in build_text_overlays(scene)}
        seen = set()
        for ct in cue_timings:
            if ct.cueOrder not in valid_cues:  # 그 씬에 없는 cue
                raise CueTimingValidationError()
            if ct.cueOrder in seen:  # cueTiming 은 cueOrder 당 1개
                raise CueTimingValidationError()
            seen.add(ct.cueOrder)
            if ct.startSec + ct.durationSec > duration + 1e-6:  # 씬 duration 초과 금지
                raise CueTimingValidationError()
        return [
            {"cueOrder": ct.cueOrder, "startSec": ct.startSec, "durationSec": ct.durationSec}
            for ct in cue_timings
        ]

    def _clamp_stored_cue_timings(self, scene: dict, duration: float) -> list[dict] | None:
        """duration 변경 등으로 cueTimings 미전송 시, 저장된 cue 를 새 duration 안으로 클램프.

        저장값이 없으면 None(그대로 두면 _cue_timings 가 균등분할 기본값을 파생).
        """
        stored = scene.get("cueTimings")
        if not stored:
            return None
        clamped = []
        for ct in stored:
            start = min(max(float(ct.get("startSec", 0.0)), 0.0), duration)
            dur = round(min(float(ct.get("durationSec", 0.0)), duration - start), 3)
            if dur > 0:
                clamped.append({"cueOrder": ct.get("cueOrder"), "startSec": round(start, 3), "durationSec": dur})
        return clamped

    # ── render plan (2차 ffmpeg 입력용 데이터 — 실제 렌더/파일생성 안 함) ──
    def build_render_plan(self, story_id: str) -> dict:
        story = self._get_story_or_404(story_id)
        scenes = []
        for scene in self._sorted_scenes(story):
            bg = self._background_repo.get(scene.get("backgroundId")) if scene.get("backgroundId") else None
            characters = []
            for ch in scene.get("characters") or []:
                char = self._character_repo.get(ch.get("characterId"))
                if char is None:
                    continue
                characters.append(
                    {
                        "characterId": char.get("characterId"),
                        "name": char.get("name"),
                        "imageUrl": resolve_character_display_image(char, ch.get("poseId")),  # 포즈 적용 시 포즈 이미지
                        "poseId": ch.get("poseId"),
                        "layout": ch.get("layout"),  # x/y/scale/rotation/zIndex/flipX (없으면 None)
                    }
                )
            subtitles = [
                {
                    "order": idx,
                    "type": it.get("type"),
                    "speaker": it.get("speaker"),
                    "text": it.get("text"),
                    "emotion": it.get("emotion"),
                    "emotionLabel": it.get("emotionLabel"),
                }
                for idx, it in enumerate(scene.get("items") or [], start=1)
            ]
            scenes.append(
                {
                    "sceneId": scene.get("sceneId"),
                    "order": scene.get("order"),
                    "duration": _duration_of(scene),
                    "backgroundImageUrl": (bg or {}).get("imageUrl"),
                    "characters": characters,
                    "subtitles": subtitles,
                    "textOverlays": build_text_overlays(scene),
                    "cueTimings": self._cue_timings(story, scene),
                }
            )
        total = round(sum(s["duration"] for s in scenes), 3)
        return {"storyId": story_id, "totalDuration": total, "scenes": scenes}


timeline_service = TimelineService(
    story_repository,
    background_repository,
    character_repository,
    tts_audio_repository,
    voice_repository,
)
