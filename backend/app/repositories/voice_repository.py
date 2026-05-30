# 기본 나레이션 보이스 preset 4개 (서버 시작 시 seed).
# 고정 voiceId를 쓴다 → 재시작/생성 순서와 무관하게 같은 ID로 참조 가능.
# 실제 클로닝/샘플 음성(sampleAudioUrl)은 AI/TTS 파트가 채운다(현재 null).
DEFAULT_NARRATOR_VOICE_PRESETS: list[dict] = [
    {
        "voiceId": "voice_preset_narrator_calm_001",
        "name": "차분한 나레이션",
        "description": "잔잔하고 따뜻하게 동화를 읽어주는 목소리",
        "voicePrompt": "calm, warm, gentle narrator voice for fairy tale storytelling",
    },
    {
        "voiceId": "voice_preset_narrator_bright_001",
        "name": "밝은 나레이션",
        "description": "밝고 친근하게 이야기를 읽어주는 목소리",
        "voicePrompt": "bright, friendly, cheerful narrator voice for children story",
    },
    {
        "voiceId": "voice_preset_narrator_soft_001",
        "name": "부드러운 나레이션",
        "description": "포근하고 부드러운 분위기의 동화 구연 목소리",
        "voicePrompt": "soft, cozy, gentle storytelling voice",
    },
    {
        "voiceId": "voice_preset_narrator_serious_001",
        "name": "진지한 나레이션",
        "description": "안정감 있고 차분하게 장면을 설명하는 목소리",
        "voicePrompt": "serious, calm, stable narrator voice",
    },
]


class VoiceRepository:
    """보이스 자산을 저장하는 메모리 Mock Repository.

    보이스는 캐릭터/배경처럼 재사용 가능한 라이브러리 자산이며,
    캐릭터는 voiceId로, 스토리는 narratorVoiceId로 이 자산을 참조한다.
    실제 클로닝/샘플 합성은 AI/TTS 파트가 담당하고, 여기서는 voiceId 발급/메타 저장만 한다.
    서버 시작 시 기본 나레이션 보이스 4개(preset)를 seed로 넣는다.
    서버 재시작 시 사용자 생성 데이터는 초기화되고, preset은 다시 seed된다.
    """

    def __init__(self):
        self._voices: dict = {}
        self._counter: int = 0
        self.seed_default_narrator_voices()

    def seed_default_narrator_voices(self) -> None:
        """기본 나레이션 보이스 preset을 메모리에 넣는다. (이미 있으면 건너뜀)"""
        for preset in DEFAULT_NARRATOR_VOICE_PRESETS:
            voice_id = preset["voiceId"]
            if voice_id in self._voices:
                continue  # 중복 seed 방지 (idempotent)
            self._voices[voice_id] = {
                "voiceId": voice_id,
                "name": preset["name"],
                "description": preset["description"],
                "voicePrompt": preset["voicePrompt"],
                "voiceType": "narrator",
                "isPreset": True,
                # preset은 선택 가능한 상태로 노출. 단 미리듣기 샘플은 아직 없음(AI가 채움).
                "status": "ready",
                "sampleAudioUrl": None,
                # provider/model은 AI 내부 메타. 응답엔 노출 안 하지만 내부엔 자리 보관.
                "provider": None,
                "model": None,
            }

    def save(self, voice_data: dict) -> dict:
        self._counter += 1
        voice_id = f"voice_mock_{self._counter:03d}"
        saved = {
            "voiceId": voice_id,
            "name": voice_data.get("name"),
            "description": voice_data.get("description"),
            "voicePrompt": voice_data.get("voicePrompt"),
            # 사용자 생성 보이스 기본값: character 용도, preset 아님
            "voiceType": voice_data.get("voiceType") or "character",
            "isPreset": False,
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
