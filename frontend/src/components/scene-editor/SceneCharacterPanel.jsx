import CharacterPosePanel from '@/components/characters/CharacterPosePanel'
import styles from '@/pages/scene-editor/SceneEditorPage.module.css'
import navCharacterIcon from '@design/assets/figma-icons/Nav/nav_character.svg'

// 씬 편집의 캐릭터 패널: 연결된 캐릭터 목록(+포즈 토글/적용, 제거) + 캐릭터 추가.
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
  if (poseForCharacterId) {
    const activeChar = sceneCharacters?.find((sc) => sc.characterId === poseForCharacterId)
    const dbChar = characters.find((c) => c.characterId === poseForCharacterId)
    const name = dbChar?.name || '캐릭터'

    return (
      <div className={styles.bgPanel}>
        <div className={styles.panelHeader}>
          <button
            type="button"
            className={styles.backBtn}
            onClick={() => onTogglePose(poseForCharacterId)}
            title="캐릭터 목록으로 돌아가기"
          >
            ← 목록
          </button>
          <span className={styles.panelLabel}>{name} 설정</span>
        </div>

        <div className={styles.panelBody} style={{ overflowY: 'auto' }}>
          <CharacterPosePanel
            characterId={poseForCharacterId}
            currentPoseId={activeChar?.poseId ?? null}
            onApplyPose={(poseId) => onApplyPose(poseForCharacterId, poseId)}
          />

          <hr className={styles.divider} />

          <button
            type="button"
            className={styles.removeBtn}
            onClick={() => {
              onRemove(poseForCharacterId)
              onTogglePose(poseForCharacterId) // 제거 후 목록으로 복귀
            }}
          >
            이 씬에서 캐릭터 제거
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.bgPanel}>
      <div className={styles.panelHeader}>
        <img src={navCharacterIcon} alt="" className={styles.panelIcon} />
        <span className={styles.panelLabel}>캐릭터 설정</span>
      </div>

      <div className={styles.panelBody}>
        <p className={styles.panelInfoText}>
          배치된 캐릭터 ({sceneCharacters?.length || 0}명)
        </p>

        {/* 연결된 캐릭터 목록 */}
        <div className={styles.charListContainer}>
          {sceneCharacters?.length > 0 ? (
            sceneCharacters.map((sc) => {
              const name =
                characters.find((c) => c.characterId === sc.characterId)?.name ?? sc.characterId
              return (
                <div key={sc.characterId} className={styles.connectedChar}>
                  <div className={styles.connectedCharRow}>
                    <span className={styles.charNameText}>• {name}</span>
                    <div className={styles.charActionGroup}>
                      <button className={styles.link} onClick={() => onTogglePose(sc.characterId)}>
                        포즈 설정 →
                      </button>
                      <button className={styles.link} onClick={() => onRemove(sc.characterId)}>
                        제거
                      </button>
                    </div>
                  </div>
                </div>
              )
            })
          ) : (
            <span className={styles.muted}>연결된 캐릭터가 없습니다.</span>
          )}
        </div>

        {/* 캐릭터 추가 */}
        <div className={styles.addButtonSection}>
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
      </div>
    </div>
  )
}
