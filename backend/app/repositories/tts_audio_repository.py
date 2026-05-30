class InMemoryTTSAudioRepository:
    """TTS mock audio 결과를 저장하는 메모리 Mock Repository.

    실제 음성 파일은 없고(audioUrl=None), 메타데이터만 보관한다.
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
