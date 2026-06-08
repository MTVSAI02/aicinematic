import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import { mediaUrl } from '@/utils/mediaUrl'
import BackgroundPromptPanel from '@/components/backgrounds/BackgroundPromptPanel'
import BackgroundLibrary from '@/components/backgrounds/BackgroundLibrary'
import styles from './BackgroundPage.module.css'

import useStoryStore from '@/store/useStoryStore'
import useSwingingSignboard from '@/hooks/useSwingingSignboard'

// 디자인 에셋 임포트
import headerBg from '@design/assets/figma-icons/Base/Base_Background.png'
import characterBackgroundSvg from '@design/assets/figma-icons/character/character_background.svg'
import yarnIcon from '@design/assets/figma-icons/Nav/nav_voice.svg'

export default function BackgroundPage() {
  const navigate = useNavigate()
  const setBackgrounds = useBackgroundStore((s) => s.setBackgrounds)
  const detailModalBackground = useBackgroundStore((s) => s.detailModalBackground)
  const setDetailModalBackground = useBackgroundStore((s) => s.setDetailModalBackground)
  const selectedBackgroundId = useBackgroundStore((s) => s.selectedBackgroundId)
  const setSelectedBackgroundId = useBackgroundStore((s) => s.setSelectedBackgroundId)
  const [loadError, setLoadError] = useState('')
  const storyTitle = useStoryStore((s) => s.storyTitle)
  const { titleRef, frameHeight } = useSwingingSignboard(1169 / 1538)

  // 페이지 진입 시 저장된 배경 목록으로 store 동기화
  useEffect(() => {
    backgroundApi
      .getBackgrounds()
      .then((list) => {
        setBackgrounds(list)
        setLoadError('')
      })
      .catch((e) => {
        setLoadError(`배경 목록을 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [setBackgrounds])

  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 (밤하늘 배경 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>장면에 어울리는 배경을 생성하거나,</div>
          <h1 className={styles.headerTitle}>멋진 동화 속<br />배경 그리기</h1>
          <p className={styles.headerDesc}>
            스토리와 씬을 선택하면 같은 그림체의<br />
            예쁘고 멋진 배경이 나와요.<br />
            똑같은 비율과 똑같은 그림체의 배경으로 나와요.
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
              src={characterBackgroundSvg} 
              alt="배경 설정 타이틀 액자" 
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
            
            {/* 1. 프롬프트 & 배경 생성 */}
            <section className={styles.section}>
              <h2 className={styles.stepTitle}>
                <span className={styles.stepBadge}>1</span>프롬프트 & 배경 생성
              </h2>
              <BackgroundPromptPanel />
            </section>

            {/* 2. 배경 라이브러리 */}
            <section className={styles.section}>
              <h2 className={styles.stepTitle}>
                <span className={styles.stepBadge}>2</span>배경 라이브러리
              </h2>
              <p className={styles.stepDesc}>생성된 배경이 여기에 저장됩니다. 선택한 배경을 연결하는 것은 "씬 편집"에서 합니다.</p>
              {loadError && <p className={styles.error}>{loadError}</p>}
              <BackgroundLibrary />
            </section>

            {/* 알아두세요 (Notice Section) */}
            <div className={styles.noticeSection}>
              <div className={styles.noticeIconWrapper}>
                <img src={yarnIcon} alt="실타래 아이콘" className={styles.noticeIcon} />
              </div>
              <div className={styles.noticeText}>
                <h3 className={styles.noticeTitle}>알아두세요</h3>
                <p className={styles.noticeDesc}>생성한 배경은 MP4 영상과 TTS 음성을 합성할 때 자동으로 저장돼요.</p>
                <p className={styles.noticeHighlight}>* "씬 편집"에서 장면에 연결하여 사용할 수 있어요.</p>
              </div>
            </div>

          </div>
          {/* ── 하단 네비게이션 고정 영역 ── */}
          <div className={styles.fixedPageNav}>
            <button className={styles.btnSecondary} onClick={() => navigate('/voice')}>
              ← 이전 단계
            </button>
            <button className={styles.btnPrimary} onClick={() => navigate('/scene-editor')}>
              다음 단계 →
            </button>
          </div>
        </div>
      </div>

      {/* ── 배경 상세 미리보기 모달 (최상위 배치로 중앙 정렬 보장) ── */}
      {detailModalBackground && (
        <div className={styles.modalOverlay} onClick={() => setDetailModalBackground(null)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <button type="button" className={styles.closeBtn} onClick={() => setDetailModalBackground(null)}>
              ×
            </button>
            <div className={styles.modalBody}>
              <div className={styles.modalLeft}>
                {detailModalBackground.imageUrl ? (
                  <img
                    src={mediaUrl(detailModalBackground.imageUrl)}
                    alt={detailModalBackground.name}
                    className={styles.modalImg}
                  />
                ) : (
                  <span className={styles.thumbEmpty}>이미지 준비 중</span>
                )}
              </div>
              <div className={styles.modalRight}>
                <h3 className={styles.modalName}>{detailModalBackground.name}</h3>
                <div className={styles.modalPromptSection}>
                  <h4 className={styles.modalPromptLabel}>프롬프트 상세 정보</h4>
                  <p className={styles.modalPromptText}>{detailModalBackground.prompt}</p>
                </div>
                <button
                  type="button"
                  className={styles.modalSelectBtn}
                  onClick={() => {
                    const isSelected = detailModalBackground.backgroundId === selectedBackgroundId
                    setSelectedBackgroundId(isSelected ? null : detailModalBackground.backgroundId)
                    setDetailModalBackground(null)
                  }}
                >
                  {detailModalBackground.backgroundId === selectedBackgroundId
                    ? '선택 해제하기'
                    : '이 배경 선택하기'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

