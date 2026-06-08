import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import CharacterCreateForm from '@/components/characters/CharacterCreateForm'
import CharacterList from '@/components/characters/CharacterList'
import CharacterPoseSection from '@/components/characters/CharacterPoseSection'
import styles from './CharacterPage.module.css'

import useStoryStore from '@/store/useStoryStore'
import useSwingingSignboard from '@/hooks/useSwingingSignboard'
import headerBg from '@design/assets/figma-icons/Base/Base_Character.png'
import characterCharacterSvg from '@design/assets/figma-icons/character/character_character.svg'

export default function CharacterPage() {
  const navigate = useNavigate()
  const setCharacters = useCharacterStore((s) => s.setCharacters)
  const detailModalCharacter = useCharacterStore((s) => s.detailModalCharacter)
  const setDetailModalCharacter = useCharacterStore((s) => s.setDetailModalCharacter)
  const lightboxPose = useCharacterStore((s) => s.lightboxPose)
  const setLightboxPose = useCharacterStore((s) => s.setLightboxPose)
  const selectCharacter = useCharacterStore((s) => s.selectCharacter)
  const selectedCharacterId = useCharacterStore((s) => s.selectedCharacterId)

  const [loadError, setLoadError] = useState('')
  const storyTitle = useStoryStore((s) => s.storyTitle)
  const { titleRef, frameHeight } = useSwingingSignboard(1125 / 1470)

  useEffect(() => {
    characterApi
      .getCharacters()
      .then((list) => {
        setCharacters(list)
        setLoadError('')
      })
      .catch((error) => {
        setLoadError(`캐릭터 목록을 불러오지 못했습니다. ${getApiErrorMessage(error)}`)
      })
  }, [setCharacters])

  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 영역 (밤하늘 배경 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>동화 속 캐릭터를 설명해주세요</div>
          <h1 className={styles.headerTitle}>동화 속<br />캐릭터 만들기</h1>
          <p className={styles.headerDesc}>
            캐릭터의 이름을 입력하고<br />
            캐릭터의 외형을 소개해 주세요<br />
            그럼 AI가 예쁘고 멋진 캐릭터를 만들어줘요
          </p>
        </div>
        <div className={styles.headerRight}>
          <div 
            className={styles.titleFrame} 
            ref={titleRef}
            style={{
              display: 'block',
              width: '100%',
              height: frameHeight ? `${frameHeight}px` : 'auto',
              position: 'relative'
            }}
          >
            <img 
              src={characterCharacterSvg} 
              alt="캐릭터 설정 타이틀 액자" 
              className={styles.titleFrameImg} 
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
            />
          </div>
        </div>
      </header>

      {/* ── 내용 컨테이너 (Glassmorphism Card) ── */}
      <div className={styles.bookContainer}>
        <div className={styles.bookContentOverlay}>
          <div className={styles.scrollArea}>
            <CharacterCreateForm />

            {/* ── 캐릭터 라이브러리 섹션 (카드 안쪽 배치) ── */}
            <section className={styles.librarySection}>
              <h2 className={styles.libraryTitle}>캐릭터 라이브러리</h2>
              {loadError && <p className={styles.error}>{loadError}</p>}
              <CharacterList />
            </section>

            {/* ── 캐릭터 포즈 생성 섹션 ── */}
            <CharacterPoseSection />
          </div>
          {/* ── 하단 네비게이션 고정 영역 ── */}
          <div className={styles.fixedPageNav}>
            <button className={styles.btnSecondary} onClick={() => navigate('/scene-check')}>
              ← 이전 단계
            </button>
            <button className={styles.btnPrimary} onClick={() => navigate('/voice')}>
              다음 단계 →
            </button>
          </div>
        </div>

      </div>

      {/* ── 캐릭터 상세 정보 모달 (최상위 배치로 중앙 정렬 보장) ── */}
      {detailModalCharacter && (
        <div className={styles.modalOverlay} onClick={() => setDetailModalCharacter(null)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <button type="button" className={styles.closeBtn} onClick={() => setDetailModalCharacter(null)}>
              ×
            </button>
            <div className={styles.modalBody}>
              <div className={styles.modalLeft}>
                {detailModalCharacter.imageUrl ? (
                  <img src={mediaUrl(detailModalCharacter.imageUrl)} alt={detailModalCharacter.name} className={styles.modalImg} />
                ) : (
                  <span className={styles.thumbEmpty}>이미지 준비 중</span>
                )}
              </div>
              <div className={styles.modalRight}>
                <h3 className={styles.modalName}>{detailModalCharacter.name}</h3>
                <div className={styles.modalPromptSection}>
                  <h4 className={styles.modalPromptLabel}>프롬프트 상세 정보</h4>
                  <p className={styles.modalPromptText}>{detailModalCharacter.appearancePrompt}</p>
                </div>
                <button
                  type="button"
                  className={styles.modalSelectBtn}
                  onClick={() => {
                    const isSelected = detailModalCharacter.characterId === selectedCharacterId
                    selectCharacter(isSelected ? null : detailModalCharacter.characterId)
                    setDetailModalCharacter(null)
                  }}
                >
                  {detailModalCharacter.characterId === selectedCharacterId ? '선택 해제하기' : '이 캐릭터 선택하기'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 캐릭터 포즈 크게 보기 라이트박스 모달 ── */}
      {lightboxPose && (
        <div className={styles.lightboxOverlay} onClick={() => setLightboxPose(null)}>
          <div className={styles.lightboxContent} onClick={(e) => e.stopPropagation()}>
            <button type="button" className={styles.lightboxCloseBtn} onClick={() => setLightboxPose(null)}>
              ×
            </button>
            <img src={mediaUrl(lightboxPose.imageUrl)} alt={lightboxPose.posePrompt} className={styles.lightboxImg} />
            <p className={styles.lightboxPrompt}>{lightboxPose.posePrompt}</p>
          </div>
        </div>
      )}
    </div>
  )
}
