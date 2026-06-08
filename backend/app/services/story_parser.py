import re

# 감정 라벨(한글) → emotion 키(영문). 미지원 라벨은 기본값으로 처리한다.
# 미지원 태그 별칭(예: "짜증"→angry, "행복"→happy)을 지원하려면 여기에 줄만 추가하면 된다.
# (현재 MVP에서는 별칭을 추가하지 않음 — 정밀화/확장은 추후)
EMOTION_MAP = {
    "기본": "neutral",
    "잔잔함": "calm",

    "기쁨": "happy",
    "즐거움": "happy",

    "슬픔": "sad",
    "시무룩": "disappointed",
    "서운함": "disappointed",

    "화남": "angry",
    "무서움": "scared",

    "걱정": "worried",
    "불안": "worried",
    "초조함": "worried",

    "신남": "excited",
    "설렘": "excited",
    "기대감": "excited",

    "다정함": "friendly",
    "따뜻함": "friendly",

    "진지함": "serious",

    "호기심": "curious",
    "궁금함": "curious",

    "장난스러움": "playful",

    "퉁명스럽게": "curt",
    "퉁명함": "curt",
    "새침함": "curt",
    "도도함": "curt",

    "부끄러움": "shy",
    "신비로움": "mysterious",
}

# 타입별 기본 감정 (감정 태그가 없거나 미지원일 때)
DEFAULT_EMOTION = {
    "narration": ("calm", "잔잔함"),
    "dialogue": ("neutral", "기본"),
}

# 화자(speaker)에 이 값이 들어오면 빈 값과 동일하게 narration 으로 취급한다.
# (역할 칸에 "나레이션"이라 적어도 dialogue 가 되어 따옴표가 붙는 문제 방지 — narration 은 따옴표 없음.)
_NARRATION_SPEAKER_ALIASES = {"나레이션", "내레이션", "narration"}


def _is_narration_speaker(speaker: str) -> bool:
    """speaker 가 비었거나 나레이션 별칭이면 narration 으로 본다."""
    return (speaker or "").strip().casefold() in {"", *_NARRATION_SPEAKER_ALIASES}

# emotion 키 → 한글 라벨 (키워드 추정 결과에 라벨을 붙일 때 사용)
EMOTION_TO_LABEL = {emotion: label for label, emotion in EMOTION_MAP.items()}

# 감정 셀렉터(structured 입력 UI) 옵션 — EMOTION_MAP 그대로(별칭 전부 노출).
# ⚠️ EMOTION_TO_LABEL 같은 자동 역매핑으로 만들지 않는다(별칭 중 마지막이 대표가 되어 어색해짐).
# GET /api/stories/emotions 가 이 목록을 그대로 내려준다. label 은 유일, value 는 중복 허용(기쁨/즐거움→happy).
EMOTION_OPTIONS = [{"label": label, "value": emotion} for label, emotion in EMOTION_MAP.items()]

# 본문 키워드 → emotion 추정 (LLM 전 단계, 규칙 기반 추정).
# 명시 [감정] 태그가 "없을 때만" 동작한다. 위에서부터 먼저 매칭되는 감정을 사용한다.
# 부분 문자열 매칭이라, 너무 짧거나 일반 단어에 자주 포함되는 키워드는 오탐을 만든다.
#   (예: "울"→"서울/울산/울타리", "떨"→"떨어지다", "웃"→…)
# 그래서 1글자/모호 키워드는 빼고 더 명확한 표현만 사용한다. 정밀화는 추후 LLM.
KEYWORD_EMOTIONS = [
    ("happy", ("하하", "기뻐", "좋아", "웃음", "웃었", "웃어")),
    ("scared", ("무서워", "무서웠", "두려워", "떨었", "벌벌", "덜덜")),
    ("sad", ("슬퍼", "슬펐다", "눈물", "울었다", "울었어", "울고")),
    ("angry", ("화가", "화났", "싫어", "싫었", "짜증")),
    ("worried", ("걱정", "불안", "초조")),
    ("curious", ("궁금", "호기심")),
    ("excited", ("신나", "설레")),
    ("friendly", ("안녕", "반가워", "반가웠")),
    ("calm", ("조용히", "천천히", "별빛", "고요")),
]


def _infer_emotion_from_text(text: str) -> tuple[str, str] | None:
    """본문에서 감정 키워드를 찾아 (emotion, emotionLabel)을 추정한다. 없으면 None."""
    for emotion, keywords in KEYWORD_EMOTIONS:
        if any(kw in text for kw in keywords):
            return emotion, EMOTION_TO_LABEL[emotion]
    return None

# 줄 맨 앞의 [감정] 태그. 괄호 안에는 대괄호를 포함하지 않는다.
_EMOTION_TAG_RE = re.compile(r"^\[([^\[\]]*)\]\s*(.*)$")
# 화자: "대사" 형식 (큰따옴표 필수)
_DIALOGUE_RE = re.compile(r'^(.+?):\s*"(.+)"$')


def parse_script_to_scenes(script: str) -> list[dict]:
    # 빈 줄 기준으로 블록 분리 (연속 빈 줄도 하나의 구분자로 처리)
    blocks = re.split(r"\n(?:\s*\n)+", script.strip())

    scenes = []
    for order, block in enumerate(blocks, start=1):
        items = []
        for raw_line in block.splitlines():
            item = _parse_line(raw_line.strip())
            if item is not None:
                items.append(item)

        if items:
            scenes.append({
                "sceneId": f"scene_{order:03d}",
                "order": order,  # 스토리 원본 순서. 이후 변경하지 않는다.
                "duration": 3.0,  # 타임라인 재생 길이(초). 기본 3.0, 1.0~30.0 범위로 조절.
                "backgroundId": None,
                "items": items,
                "subtitleSettings": {},  # item별 자막 설정(cueOrder+layout). 자막 자체는 items에서 자동 생성.
            })

    return scenes


def _parse_line(line: str) -> dict | None:
    """한 줄을 item dict로 파싱한다. 본문이 비면 None(스킵)."""
    if not line:
        return None

    # 1. 맨 앞 [감정] 태그 추출 후 제거 (지원 여부와 무관하게 제거)
    emotion_label = None
    tag_match = _EMOTION_TAG_RE.match(line)
    if tag_match:
        emotion_label = tag_match.group(1).strip()  # 라벨 앞뒤 공백 허용
        line = tag_match.group(2).strip()

    # 감정 태그를 떼고 나서 본문이 비면 item을 만들지 않고 스킵한다. (예: "[화남]")
    if not line:
        return None

    # 2. dialogue / narration 판정
    #    화자: "대사" 형식이라도 화자가 비거나 "나레이션" 별칭이면 narration(따옴표 없음)으로 본다.
    dialogue = _DIALOGUE_RE.match(line)
    if dialogue and not _is_narration_speaker(dialogue.group(1)):
        item = {
            "type": "dialogue",
            "speaker": dialogue.group(1).strip(),
            "text": dialogue.group(2).strip(),
        }
    else:
        item = {
            "type": "narration",
            "speaker": None,
            # dialogue 형식이었으면 따옴표 안 본문만 사용, 아니면 줄 전체.
            "text": dialogue.group(2).strip() if dialogue else line,
        }

    # 3. emotion 결정 (우선순위)
    #    a. 지원하는 [감정] 태그 → 매핑 적용 (명시 우선)
    #    b. 미지원 [감정] 태그 → 기본 emotion 키, 단 사용자가 입력한 라벨은 보존
    #    c. 태그 없음 → 본문 키워드 추정, 못 정하면 타입별 기본값
    if emotion_label and emotion_label in EMOTION_MAP:
        item["emotion"] = EMOTION_MAP[emotion_label]
        item["emotionLabel"] = emotion_label
    elif emotion_label:  # 미지원 태그: 키는 기본값(파싱 실패 방지), 라벨은 입력 그대로
        item["emotion"] = DEFAULT_EMOTION[item["type"]][0]
        item["emotionLabel"] = emotion_label
    else:  # 태그 없음
        inferred = _infer_emotion_from_text(item["text"])
        item["emotion"], item["emotionLabel"] = inferred or DEFAULT_EMOTION[item["type"]]

    return item


def _build_scene(order: int, items: list[dict]) -> dict:
    """내부 scene dict 1개 생성. raw/structured 가 동일한 모양을 쓰도록 단일화."""
    return {
        "sceneId": f"scene_{order:03d}",
        "order": order,  # 스토리 원본 순서. 이후 변경하지 않는다.
        "duration": 3.0,
        "backgroundId": None,
        "items": items,
        "subtitleSettings": {},
    }


def parse_structured_story(scenes: list[dict]) -> list[dict]:
    """구조화 입력(scenes/items) → 내부 scene dict 리스트.

    raw 파서(parse_script_to_scenes)와 **동일한 출력 모양**을 만든다(저장 계층 그대로 재사용).
    - sceneOrder 순서대로 1..N 으로 order 재정렬(중간 삭제로 생긴 공백 정리).
    - speaker 비면 narration / 있으면 dialogue.
    - emotion 코드는 emotionLabel(EMOTION_MAP) 우선 → 제공된 emotion → 타입 기본값.
    - 빈 text 는 ValueError (스키마에서 먼저 막지만 방어적으로 한 번 더).
    """
    result: list[dict] = []
    for order, scene in enumerate(scenes, start=1):
        items: list[dict] = []
        for raw in scene.get("items", []):
            text = (raw.get("text") or "").strip()
            if not text:
                raise ValueError("빈 대사/나레이션은 저장할 수 없습니다.")
            speaker = (raw.get("speaker") or "").strip()
            # 역할이 비거나 "나레이션" 별칭이면 narration(따옴표 없음)으로 정규화.
            if _is_narration_speaker(speaker):
                speaker = ""
            label = (raw.get("emotionLabel") or "").strip()
            item_type = "dialogue" if speaker else "narration"
            emotion = EMOTION_MAP.get(label) or raw.get("emotion") or DEFAULT_EMOTION[item_type][0]
            items.append({
                "type": item_type,
                "speaker": speaker or None,
                "text": text,
                "emotion": emotion,
                "emotionLabel": label or DEFAULT_EMOTION[item_type][1],
            })
        if not items:
            raise ValueError("씬에는 최소 1개의 항목이 필요합니다.")
        result.append(_build_scene(order, items))
    return result


def parse_story(payload: dict) -> list[dict]:
    """inputMode 에 따라 raw / structured 파서로 분기한다(기본 raw)."""
    if payload.get("inputMode") == "structured":
        return parse_structured_story(payload.get("scenes") or [])
    return parse_script_to_scenes(payload.get("script") or "")
