import threading


class BackgroundCandidateRepository:
    """배경 생성 후보를 임시 저장하는 메모리 Mock Repository.

    후보(candidate)는 아직 라이브러리에 저장된 배경이 아니다.
    사용자가 후보 중 하나를 선택해 저장하면 Background Repository로 넘어간다.
    비동기 Job(워커 스레드)에서 생성되므로 counter는 lock으로 보호한다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._candidates: dict = {}
        self._counter: int = 0
        self._lock = threading.Lock()

    def reserve_id(self) -> str:
        """candidateId만 발급한다(저장 X). 이미지 파일명을 먼저 정하고 저장하기 위함."""
        with self._lock:
            self._counter += 1
            return f"bg_candidate_{self._counter:03d}"

    def create(self, candidate_id: str, candidate_data: dict) -> dict:
        """예약된 candidateId로 후보 레코드를 저장한다. (negativePrompt는 다루지 않음)"""
        saved = {
            "candidateId": candidate_id,
            "prompt": candidate_data.get("prompt"),
            "finalPrompt": candidate_data.get("finalPrompt"),
            "imageUrl": candidate_data.get("imageUrl"),
        }
        with self._lock:
            self._candidates[candidate_id] = saved
        return saved

    def save(self, candidate_data: dict) -> dict:
        """ID 발급 + 즉시 저장."""
        return self.create(self.reserve_id(), candidate_data)

    def get(self, candidate_id: str) -> dict | None:
        return self._candidates.get(candidate_id)

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._candidates.values())


background_candidate_repository = BackgroundCandidateRepository()
