import threading


class BackgroundRepository:
    """사용자가 저장한 배경 라이브러리를 관리하는 메모리 Mock Repository.

    Background는 특정 씬의 소유물이 아니라 여러 스토리/씬에서 재사용하는 자산이다.
    FastAPI 동시 요청에서 ID 발급/수정이 겹칠 수 있어 lock으로 보호한다.
    서버 재시작 시 데이터는 초기화된다.
    """

    def __init__(self):
        self._backgrounds: dict = {}
        self._counter: int = 0
        self._lock = threading.Lock()

    def reserve_id(self) -> str:
        """backgroundId만 발급한다(저장 X). 이미지 파일명을 먼저 정해 복사하기 위함."""
        with self._lock:
            self._counter += 1
            return f"bg_mock_{self._counter:03d}"

    def create(self, background_id: str, background_data: dict) -> dict:
        """예약된 backgroundId로 배경 레코드를 저장한다."""
        saved = {
            "backgroundId": background_id,
            "name": background_data.get("name"),
            "prompt": background_data.get("prompt"),
            "finalPrompt": background_data.get("finalPrompt"),
            "imageUrl": background_data.get("imageUrl"),
        }
        with self._lock:
            self._backgrounds[background_id] = saved
        return saved

    def save(self, background_data: dict) -> dict:
        """ID 발급 + 즉시 저장."""
        return self.create(self.reserve_id(), background_data)

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._backgrounds.values())

    def get(self, background_id: str) -> dict | None:
        return self._backgrounds.get(background_id)

    def update(self, background_id: str, update_data: dict) -> dict | None:
        with self._lock:
            background = self._backgrounds.get(background_id)
            if not background:
                return None
            # MVP: name만 수정 가능. 전달된(None이 아닌) name만 반영한다.
            if update_data.get("name") is not None:
                background["name"] = update_data["name"]
            return background

    def delete(self, background_id: str) -> bool:
        with self._lock:
            if background_id in self._backgrounds:
                del self._backgrounds[background_id]
                return True
            return False


background_repository = BackgroundRepository()
