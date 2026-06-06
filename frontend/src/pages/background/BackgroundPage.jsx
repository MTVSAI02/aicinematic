import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import BackgroundPromptPanel from '@/components/backgrounds/BackgroundPromptPanel'
import BackgroundLibrary from '@/components/backgrounds/BackgroundLibrary'
import styles from './BackgroundPage.module.css'

// 디자인 에셋 임포트
import headerBg from '@design/assets/figma-icons/Scene-_Check/BACJ.png'
import navBackgroundMascot from '@design/assets/figma-icons/Nav/nav_background.svg'
import yarnIcon from '@design/assets/figma-icons/Nav/nav_voice.svg'

export default function BackgroundPage() {
  const navigate = useNavigate()
  const setBackgrounds = useBackgroundStore((s) => s.setBackgrounds)
  const [loadError, setLoadError] = useState('')

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
      {/* ── 상단 헤더 (밤하늘 배경 BACJ.png 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>장면에 어울리는 배경을 생성하거나,</div>
          <h1 className={styles.headerTitle}>배경</h1>
          <p className={styles.headerDesc}>
            스토리와 씬을 선택하면 추천 배경 프롬프트를<br />
            받을 수 있어요.
          </p>
        </div>
        <div className={styles.headerRight}>
          <img src={navBackgroundMascot} alt="배경 마스코트" className={styles.headerMascot} />
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
      </div>
    </div>
  )
}

