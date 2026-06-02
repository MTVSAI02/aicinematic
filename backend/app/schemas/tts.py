from pydantic import BaseModel, ConfigDict


class TTSSceneGenerateRequest(BaseModel):
    storyId: str
    sceneId: str


class TTSAudioResponse(BaseModel):
    audioId: str
    storyId: str
    sceneId: str
    itemIndex: int  # scene.items의 원본 index (빈 item 제외돼도 재번호 X)
    type: str  # narration / dialogue
    speaker: str | None = None
    text: str
    emotion: str
    emotionLabel: str
    emotionPrompt: str | None = None  # emotion 키 → Qwen 합성용 자연어 instruction
    voiceType: str  # narrator / character
    characterId: str | None = None  # dialogue speaker→캐릭터(name 매칭) ID, 미매칭/narration이면 null
    characterName: str | None = None  # 매칭 캐릭터 이름 (narration/미매칭이면 null)
    characterPrompt: str | None = None  # 캐릭터 말투 prompt (description→appearancePrompt→name 기반)
    voiceId: str | None = None  # dialogue=캐릭터 voiceId / narration=story.narratorVoiceId, 없으면 null
    voiceName: str | None = None
    voicePrompt: str | None = None
    # referenceAudioUrl/referenceText 는 AI payload 전용(프론트 응답 미노출)이라 schema 에 두지 않는다.
    audioUrl: str | None = None
    durationSec: float | None = None
    error: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "audioId": "audio_mock_001",
                "storyId": "story_mock_001",
                "sceneId": "scene_001",
                "itemIndex": 0,
                "type": "narration",
                "speaker": None,
                "text": "어린왕자는 조용히 별을 바라보았다.",
                "emotion": "calm",
                "emotionLabel": "잔잔함",
                "voiceType": "narrator",
                "characterId": None,
                "voiceId": None,
                "voiceName": None,
                "voicePrompt": None,
                "audioUrl": None,
                "durationSec": None,
                "error": None,
            }
        }
    )


class TTSDeleteResponse(BaseModel):
    deleted: bool
    audioId: str
