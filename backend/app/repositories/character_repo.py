from __future__ import annotations  # list() 메서드가 빌트인 list를 가려 어노테이션 평가가 깨지는 것 방지

import threading


class CharacterRepository:
    """DB 대신 메모리 dict에 캐릭터를 저장하는 Mock Repository.

    서버 재시작 시 데이터는 초기화된다.
    비동기 Job(워커 스레드)에서 ID 발급/저장이 일어날 수 있어 counter는 lock으로 보호한다.
    """

    def __init__(self):
        self._characters: dict = {}
        self._counter: int = 0
        self._pose_counter: int = 0
        self._lock = threading.Lock()

    def reserve_id(self) -> str:
        """characterId만 발급한다(저장하지 않음).

        생성(예: ComfyUI 이미지)을 먼저 시도하고 성공한 뒤 create()로 저장하기 위함.
        → 생성 실패 시 imageUrl=None인 빈 캐릭터(orphan)가 남지 않는다.
        """
        with self._lock:
            self._counter += 1
            return f"char_mock_{self._counter:03d}"

    def create(self, character_id: str, character_data: dict) -> dict:
        """예약된 characterId로 캐릭터 레코드를 저장한다."""
        saved = {
            "characterId": character_id,
            "name": character_data.get("name"),
            "appearancePrompt": character_data.get("appearancePrompt"),
            "description": character_data.get("description"),  # 저장/표시용 메타(ComfyUI prompt 미사용)
            "imageUrl": character_data.get("imageUrl"),
            "voiceId": character_data.get("voiceId"),  # 보이스 라이브러리 참조 (없으면 None)
            # AI 서버 원본 경로(포즈 생성 reference용, 내부 전용). CharacterResponse엔 노출 안 함. 없으면 None.
            "aiImagePath": character_data.get("aiImagePath"),
            # 캐릭터별 생성된 포즈 목록(1:N). 포즈 생성 Job 완료 시 append. (별도 repo 대신 레코드에 둠 → dev_persist로 유지)
            "poses": character_data.get("poses") or [],
        }
        with self._lock:
            self._characters[character_id] = saved
        return saved

    def save(self, character_data: dict) -> dict:
        """ID 발급 + 즉시 저장 (이미 만들어진 결과를 바로 저장하는 경로)."""
        return self.create(self.reserve_id(), character_data)

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._characters.values())

    def get(self, character_id: str) -> dict | None:
        return self._characters.get(character_id)

    def update(self, character_id: str, update_data: dict) -> dict | None:
        with self._lock:
            character = self._characters.get(character_id)
            if not character:
                return None
            # update_data는 라우터에서 exclude_unset으로 만든 dict이므로
            # "명시적으로 전달된 필드"만 들어 있다.
            # - name / appearancePrompt: NOT NULL 성격 → None(명시적 null)은 무시한다.
            # - description / imageUrl: nullable → 명시적 null이면 값을 초기화(None)한다.
            for field in ("name", "appearancePrompt"):
                if field in update_data and update_data[field] is not None:
                    character[field] = update_data[field]
            for field in ("description", "imageUrl"):
                if field in update_data:
                    character[field] = update_data[field]
            return character

    def set_voice(self, character_id: str, voice_id: str | None) -> dict | None:
        """캐릭터에 voiceId를 연결/해제한다. (None이면 해제)"""
        with self._lock:
            character = self._characters.get(character_id)
            if not character:
                return None
            character["voiceId"] = voice_id
            return character

    def detach_voice(self, voice_id: str) -> int:
        """해당 voiceId를 참조하던 모든 캐릭터의 voiceId를 None으로 만든다. (보이스 삭제 시)"""
        count = 0
        with self._lock:
            for character in self._characters.values():
                if character.get("voiceId") == voice_id:
                    character["voiceId"] = None
                    count += 1
        return count

    def delete(self, character_id: str) -> bool:
        with self._lock:
            if character_id in self._characters:
                del self._characters[character_id]
                return True
            return False

    # ── 포즈 (캐릭터 1:N) ─────────────────────────────────────
    def reserve_pose_id(self) -> str:
        """poseId만 발급한다(저장 X). 생성 성공 후 add_pose로 저장."""
        with self._lock:
            self._pose_counter += 1
            return f"pose_mock_{self._pose_counter:03d}"

    def add_pose(self, character_id: str, pose: dict) -> dict | None:
        """캐릭터의 poses 목록에 포즈를 추가한다. 캐릭터 없으면 None."""
        with self._lock:
            character = self._characters.get(character_id)
            if not character:
                return None
            character.setdefault("poses", []).append(pose)
            return pose

    def list_poses(self, character_id: str) -> list | None:
        """캐릭터의 포즈 목록. 캐릭터 없으면 None(빈 목록과 구분)."""
        with self._lock:
            character = self._characters.get(character_id)
            if character is None:
                return None
            return list(character.get("poses") or [])


character_repository = CharacterRepository()
