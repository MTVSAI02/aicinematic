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

# emotion 키 → 한글 라벨 (키워드 추정 결과에 라벨을 붙일 때 사용)
EMOTION_TO_LABEL = {emotion: label for label, emotion in EMOTION_MAP.items()}

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
    dialogue = _DIALOGUE_RE.match(line)
    if dialogue:
        item = {
            "type": "dialogue",
            "speaker": dialogue.group(1).strip(),
            "text": dialogue.group(2).strip(),
        }
    else:
        item = {
            "type": "narration",
            "speaker": None,
            "text": line,
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
