class VoiceRepository:
    """보이스 자산을 저장하는 메모리 Mock Repository.

    보이스는 캐릭터/배경처럼 재사용 가능한 라이브러리 자산이며,
    캐릭터는 voiceId로 이 자산을 참조한다.
    실제 클로닝/샘플 합성은 AI/TTS 파트가 담당하고, 여기서는 voiceId 발급/메타 저장만 한다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._voices: dict = {}
        self._counter: int = 0

    def save(self, voice_data: dict) -> dict:
        self._counter += 1
        voice_id = f"voice_mock_{self._counter:03d}"
        saved = {
            "voiceId": voice_id,
            "name": voice_data.get("name"),
            "description": voice_data.get("description"),
            "voicePrompt": voice_data.get("voicePrompt"),
            "sampleAudioUrl": voice_data.get("sampleAudioUrl"),
            # provider/model/sampleAudioUrl은 AI/TTS 파트가 클로닝 후 채운다 (생성 시 None).
            "provider": voice_data.get("provider"),
            "model": voice_data.get("model"),
            # 생성 직후엔 "pending"(AI 클로닝 대기). 실제 클로닝되면 AI 파트가 "ready"로 갱신.
            "status": voice_data.get("status") or "pending",
        }
        self._voices[voice_id] = saved
        return saved

    def list(self) -> list[dict]:
        return list(self._voices.values())

    def get(self, voice_id: str) -> dict | None:
        return self._voices.get(voice_id)

    def update(self, voice_id: str, update_data: dict) -> dict | None:
        voice = self._voices.get(voice_id)
        if not voice:
            return None
        # 사용자 메타만 수정한다. provider/model/sampleAudioUrl/status는 AI 결과 필드라 여기서 건드리지 않음.
        for field in ("description", "voicePrompt"):
            if field in update_data:
                voice[field] = update_data[field]
        if update_data.get("name") is not None:
            voice["name"] = update_data["name"]
        return voice

    def delete(self, voice_id: str) -> bool:
        if voice_id in self._voices:
            del self._voices[voice_id]
            return True
        return False


voice_repository = VoiceRepository()
