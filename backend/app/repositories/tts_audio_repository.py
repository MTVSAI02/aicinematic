class InMemoryTTSAudioRepository:
    """TTS audio 결과를 저장하는 메모리 Repository.

    mock 단계에서는 audioUrl=None 메타데이터만 보관하고,
    AI/TTS 연동 시 audioId 기준으로 audioUrl/durationSec/error를 갱신한다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._audios: dict = {}
        self._counter: int = 0

    def create_many(self, audios: list[dict]) -> list[dict]:
        """audio 목록을 저장하면서 audioId를 발급한다. 저장된(=audioId 포함) 목록을 반환한다."""
        saved = []
        for audio in audios:
            self._counter += 1
            audio_id = f"audio_mock_{self._counter:03d}"
            record = {**audio, "audioId": audio_id}
            self._audios[audio_id] = record
            saved.append(record)
        return saved

    def list_by_scene(self, story_id: str, scene_id: str) -> list[dict]:
        return [
            a
            for a in self._audios.values()
            if a.get("storyId") == story_id and a.get("sceneId") == scene_id
        ]

    def get(self, audio_id: str) -> dict | None:
        return self._audios.get(audio_id)

    def apply_ai_result(self, audios: list[dict]) -> list[dict]:
        """AI/TTS 응답을 audioId 기준으로 저장 레코드에 반영한다."""
        updated = []
        for audio in audios:
            audio_id = audio.get("audioId")
            if not audio_id or audio_id not in self._audios:
                continue

            record = self._audios[audio_id]
            record["audioUrl"] = audio.get("audioUrl")
            record["durationSec"] = audio.get("durationSec")
            record["error"] = audio.get("error")
            updated.append(record)
        return updated

    def delete(self, audio_id: str) -> bool:
        if audio_id in self._audios:
            del self._audios[audio_id]
            return True
        return False

    def delete_by_scene(self, story_id: str, scene_id: str) -> int:
        """특정 story+scene의 기존 audio를 모두 삭제하고 삭제 개수를 반환한다. (재생성 교체용)"""
        targets = [a["audioId"] for a in self.list_by_scene(story_id, scene_id)]
        for audio_id in targets:
            del self._audios[audio_id]
        return len(targets)


tts_audio_repository = InMemoryTTSAudioRepository()
