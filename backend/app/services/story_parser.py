import re


def parse_script_to_scenes(script: str) -> list[dict]:
    # 빈 줄 기준으로 블록 분리 (연속 빈 줄도 하나의 구분자로 처리)
    blocks = re.split(r"\n(?:\s*\n)+", script.strip())

    scenes = []
    for order, block in enumerate(blocks, start=1):
        items = []
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            items.append(_parse_line(line))

        if items:
            scenes.append({
                "sceneId": f"scene_{order:03d}",
                "order": order,
                "items": items,
            })

    return scenes


def _parse_line(line: str) -> dict:
    # 화자: "대사" 형식만 dialogue로 처리
    match = re.match(r'^(.+?):\s*"(.+)"$', line)
    if match:
        return {
            "type": "dialogue",
            "speaker": match.group(1).strip(),
            "text": match.group(2).strip(),
        }
    return {
        "type": "narration",
        "speaker": None,
        "text": line,
    }
