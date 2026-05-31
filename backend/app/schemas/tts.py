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
    voiceType: str  # narrator / character
    characterId: str | None = None  # dialogue speaker→캐릭터(name 매칭) ID, 미매칭/narration이면 null
    voiceId: str | None = None  # dialogue=캐릭터 voiceId / narration=story.narratorVoiceId, 없으면 null
    audioUrl: str | None = None  # 현재 null (실제 합성은 AI 단계)

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
                "audioUrl": None,
            }
        }
    )


class TTSDeleteResponse(BaseModel):
    deleted: bool
    audioId: str
