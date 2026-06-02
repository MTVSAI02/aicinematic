import CharacterPosePanel from '@/components/characters/CharacterPosePanel'
import styles from '@/pages/scene-editor/SceneEditorPage.module.css'

// 씬 편집의 캐릭터 패널: 연결된 캐릭터 목록(+포즈 토글/적용, 제거) + 캐릭터 추가.
// 배치(드래그/크기/회전)는 스테이지에서, 여기선 연결/포즈/추가만 다룬다.
export default function SceneCharacterPanel({
  sceneCharacters, // selectedScene.characters
  characters, // 라이브러리 store (이름 표시용)
  pickedCharacterId,
  onPickedCharacterChange,
  onConnect,
  onRemove,
  poseForCharacterId,
  onTogglePose,
  onApplyPose,
  onGoCreateCharacter,
}) {
  return (
    <div className={styles.bgPanel}>
      <span className={styles.panelLabel}>캐릭터 (씬당 여러 명)</span>

      {/* 연결된 캐릭터 목록 + 포즈/제거 */}
      {sceneCharacters?.length > 0 ? (
        sceneCharacters.map((sc) => {
          const name =
            characters.find((c) => c.characterId === sc.characterId)?.name ?? sc.characterId
          const poseOpen = poseForCharacterId === sc.characterId
          return (
            <div key={sc.characterId} className={styles.connectedChar}>
              <span className={styles.muted}>
                • {name}{' '}
                <button className={styles.link} onClick={() => onTogglePose(sc.characterId)}>
                  {poseOpen ? '포즈 닫기' : '포즈'}
                </button>{' '}
                <button className={styles.link} onClick={() => onRemove(sc.characterId)}>
                  제거
                </button>
              </span>
              {poseOpen && (
                <CharacterPosePanel
                  characterId={sc.characterId}
                  currentPoseId={sc.poseId ?? null}
                  onApplyPose={(poseId) => onApplyPose(sc.characterId, poseId)}
                />
              )}
            </div>
          )
        })
      ) : (
        <span className={styles.muted}>연결된 캐릭터 없음</span>
      )}

      {/* 캐릭터 추가 */}
      {characters.length === 0 ? (
        <span className={styles.muted}>
          저장된 캐릭터가 없습니다.{' '}
          <button className={styles.link} onClick={onGoCreateCharacter}>
            캐릭터 만들기
          </button>
        </span>
      ) : (
        <>
          <select
            className={styles.select}
            value={pickedCharacterId}
            onChange={(e) => onPickedCharacterChange(e.target.value)}
          >
            <option value="">추가할 캐릭터 선택</option>
            {characters.map((c) => (
              <option key={c.characterId} value={c.characterId}>{c.name}</option>
            ))}
          </select>
          <button className={styles.panelBtn} onClick={onConnect} disabled={!pickedCharacterId}>
            이 씬에 캐릭터 추가
          </button>
        </>
      )}
    </div>
  )
}
