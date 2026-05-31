class BackgroundCandidateRepository:
    """배경 생성 후보를 임시 저장하는 메모리 Mock Repository.

    후보(candidate)는 아직 라이브러리에 저장된 배경이 아니다.
    사용자가 후보 중 하나를 선택해 저장하면 Background Repository로 넘어간다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._candidates: dict = {}
        self._counter: int = 0

    def save(self, candidate_data: dict) -> dict:
        self._counter += 1
        candidate_id = f"bg_candidate_{self._counter:03d}"
        saved = {
            "candidateId": candidate_id,
            "prompt": candidate_data.get("prompt"),
            "finalPrompt": candidate_data.get("finalPrompt"),
            "negativePrompt": candidate_data.get("negativePrompt"),
            "imageUrl": candidate_data.get("imageUrl"),
        }
        self._candidates[candidate_id] = saved
        return saved

    def get(self, candidate_id: str) -> dict | None:
        return self._candidates.get(candidate_id)

    def list(self) -> list[dict]:
        return list(self._candidates.values())


background_candidate_repository = BackgroundCandidateRepository()
