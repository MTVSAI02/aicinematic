class StoryRepository:
    def __init__(self):
        self._stories: dict = {}
        self._counter: int = 0

    def save(self, story_data: dict) -> dict:
        self._counter += 1
        story_id = f"story_mock_{self._counter:03d}"
        # narratorVoiceId 기본 None (나레이션 보이스 미연결)
        # voiceLocks: 대상별(나레이션/캐릭터) 잠금 상태 { targetId: {lockStatus, ttsStatus} }.
        #   targetId = "narration" 또는 characterId. 없는 대상은 unlocked/idle 로 간주한다.
        saved = {
            "narratorVoiceId": None,
            "voiceLocks": {},
            **story_data,
            "storyId": story_id,
        }
        self._stories[story_id] = saved
        return saved

    def lock_voice_target(self, story_id: str, target_id: str) -> int | None:
        """대상을 잠그고(locked/generating) generationToken 을 1 증가시켜 반환한다.

        백그라운드 TTS job 은 이 토큰을 캡처했다가 완료 시 apply_target_tts_status 로
        "여전히 locked + 같은 토큰"일 때만 결과를 반영한다(잠금 해제/재잠금 race 방어).
        """
        story = self._stories.get(story_id)
        if story is None:
            return None
        locks = story.setdefault("voiceLocks", {})
        gen = (locks.get(target_id, {}).get("gen") or 0) + 1
        locks[target_id] = {"lockStatus": "locked", "ttsStatus": "generating", "gen": gen}
        return gen

    def apply_target_tts_status(
        self, story_id: str, target_id: str, tts_status: str, expected_gen: int
    ) -> bool:
        """job 결과 반영: 현재 lockStatus==locked 이고 gen==expected_gen 일 때만 ttsStatus 갱신.

        그 사이 잠금 해제/재잠금이 있었으면(상태·토큰 불일치) 무시한다. 반영하면 True.
        """
        story = self._stories.get(story_id)
        if story is None:
            return False
        cur = story.get("voiceLocks", {}).get(target_id)
        if not cur or cur.get("lockStatus") != "locked" or (cur.get("gen") or 0) != expected_gen:
            return False
        cur["ttsStatus"] = tts_status
        return True

    def unlock_voice_target(self, story_id: str, target_id: str) -> dict | None:
        """대상 잠금 해제(unlocked/stale). gen 은 유지 — 진행 중 job 은 lockStatus 불일치로 무시됨."""
        story = self._stories.get(story_id)
        if story is None:
            return None
        locks = story.setdefault("voiceLocks", {})
        gen = locks.get(target_id, {}).get("gen") or 0
        locks[target_id] = {"lockStatus": "unlocked", "ttsStatus": "stale", "gen": gen}
        return story

    def get_voice_locks(self, story_id: str) -> dict:
        story = self._stories.get(story_id)
        return (story or {}).get("voiceLocks", {})

    def get(self, story_id: str) -> dict | None:
        return self._stories.get(story_id)

    def list(self) -> list[dict]:
        return list(self._stories.values())

    def set_last_render(self, story_id: str, last_render: dict | None) -> dict | None:
        """story.lastRender(최신 렌더 결과)를 저장/해제한다. 없는 story면 None.

        스토리당 최신 렌더 1개만 기억한다(새 렌더가 덮어씀).
        """
        story = self._stories.get(story_id)
        if story is None:
            return None
        story["lastRender"] = last_render
        return story

    def set_narrator_voice(self, story_id: str, voice_id: str | None) -> dict | None:
        """story.narratorVoiceId를 설정/해제한다. 없는 story면 None 반환."""
        story = self._stories.get(story_id)
        if story is None:
            return None
        story["narratorVoiceId"] = voice_id
        return story

    def detach_narrator_voice(self, voice_id: str) -> None:
        """주어진 voiceId를 나레이터로 쓰던 모든 story의 narratorVoiceId를 null로.

        (보이스 삭제 캐스케이드용 — character_repo.detach_voice와 대칭)
        """
        for story in self._stories.values():
            if story.get("narratorVoiceId") == voice_id:
                story["narratorVoiceId"] = None


story_repository = StoryRepository()
