from ..core.exceptions import CharacterNotFoundError, NoFieldsToUpdateError
from ..repositories.character_repo import character_repository


class CharacterService:
    """캐릭터 라이브러리 비즈니스 로직.

    라우터가 repository를 직접 다루지 않도록 CRUD를 이 서비스가 담당한다.
    존재하지 않는 대상 등 비즈니스 예외는 커스텀 예외로 발생시키고,
    HTTP 변환은 글로벌 exception handler가 담당한다.
    """

    def __init__(self, character_repo):
        self._character_repo = character_repo

    def create_character(self, character_data: dict) -> dict:
        """이미 만들어진 캐릭터 결과를 직접 저장한다."""
        return self._character_repo.save(character_data)

    def list_characters(self) -> list[dict]:
        return self._character_repo.list()

    def get_character(self, character_id: str) -> dict:
        character = self._character_repo.get(character_id)
        if character is None:
            raise CharacterNotFoundError()
        return character

    def update_character(self, character_id: str, update_data: dict) -> dict:
        if not update_data:
            raise NoFieldsToUpdateError()
        updated = self._character_repo.update(character_id, update_data)
        if updated is None:
            raise CharacterNotFoundError()
        return updated

    def delete_character(self, character_id: str) -> None:
        deleted = self._character_repo.delete(character_id)
        if not deleted:
            raise CharacterNotFoundError()


character_service = CharacterService(character_repository)
