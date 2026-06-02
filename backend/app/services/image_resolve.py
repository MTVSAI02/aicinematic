"""씬에서 보여줄 캐릭터 이미지 해석(공용).

규칙: poseId 있으면 그 포즈 imageUrl, 없으면 원본 character.imageUrl.
(원본은 그대로 두고 씬 단위 override만 적용 — 스토리/타임라인/렌더가 동일 규칙을 쓴다.)
"""


def resolve_character_display_image(character: dict | None, pose_id: str | None) -> str | None:
    if pose_id and character:
        for p in character.get("poses") or []:
            if p.get("poseId") == pose_id:
                return p.get("imageUrl")
    return (character or {}).get("imageUrl")
