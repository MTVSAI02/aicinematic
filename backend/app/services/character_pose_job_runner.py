"""캐릭터 포즈 생성 Job (비동기).

구조: Backend → 우리 AI FastAPI 서버(/generate-pose) → 외부 ComfyUI.
- 캐릭터의 aiImagePath(AI 서버 원본 경로)를 reference 로 새 포즈 이미지를 생성한다.
- 원본 캐릭터 이미지를 덮어쓰지 않는다 — storage/character_poses/ 에 새 poseId로 저장하고 캐릭터에 연결.
- jobId 즉시 반환, GET /api/jobs/{jobId} 로 폴링. 완료 시 result = CharacterPoseResponse.
- 캐릭터 존재/aiImagePath 검증은 라우터에서 동기로 끝낸 뒤(404/400) 이 Job을 시작한다.
"""

from ..core.config import CHARACTER_POSE_STORAGE_DIR, storage_url
from ..core.exceptions import CharacterNotFoundError, PoseGenerationFailedError
from ..repositories.character_repo import character_repository
from ..schemas.job import JobType
from .ai_pose_client import generate_pose_image
from .job_manager import job_manager


def create_character_pose_generation_job(
    character_id: str, ai_image_path: str, pose_prompt: str
) -> dict:
    def build_result() -> dict:
        # 1. poseId 먼저 발급(저장 X) → 생성 성공 후에만 파일/레코드 저장(orphan 방지)
        pose_id = character_repository.reserve_pose_id()

        # 2. AI 서버 /generate-pose: {image_path, pose_prompt} → 포즈 이미지 bytes
        image_bytes = generate_pose_image(ai_image_path, pose_prompt)

        # 3. 저장은 backend 담당: 원본과 분리된 character_poses/ 에 저장 → /storage URL
        CHARACTER_POSE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        pose_path = CHARACTER_POSE_STORAGE_DIR / f"{pose_id}.png"
        pose_path.write_bytes(image_bytes)
        image_url = storage_url("character_poses", f"{pose_id}.png")

        pose = {
            "poseId": pose_id,
            "characterId": character_id,
            "posePrompt": pose_prompt,
            "imageUrl": image_url,
        }
        # 4. 캐릭터에 연결(1:N). 생성 도중 캐릭터가 삭제됐으면 None → 방금 쓴 파일 정리 + Job 실패(orphan 방지).
        if character_repository.add_pose(character_id, pose) is None:
            pose_path.unlink(missing_ok=True)
            raise CharacterNotFoundError()
        return pose

    return job_manager.run_async(
        JobType.character_pose_generate.value,
        build_result,
        PoseGenerationFailedError.detail,
        "Character pose generation job started.",
    )
