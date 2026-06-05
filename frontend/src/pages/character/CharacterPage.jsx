import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import CharacterCreateForm from '@/components/characters/CharacterCreateForm'
import CharacterList from '@/components/characters/CharacterList'
import styles from './CharacterPage.module.css'

// 디자인 에셋 임포트
import characterMascot from '@design/assets/figma-icons/Nav/nav_character.svg'

export default function CharacterPage() {
  const navigate = useNavigate()
  const setCharacters = useCharacterStore((s) => s.setCharacters)
  const [loadError, setLoadError] = useState('')

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
      {/* ── 상단 헤더 영역 (마스코트 배치) ── */}
      <header className={styles.header}>
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
          <img src={characterMascot} alt="캐릭터 마스코트" className={styles.headerMascot} />
        </div>
      </header>

      {/* ── 내용 컨테이너 (Glassmorphism Card) ── */}
      <div className={styles.bookContainer}>
        <div className={styles.bookContentOverlay}>
          <div className={styles.scrollArea}>
            <CharacterCreateForm />
          </div>
        </div>

        {/* 하단 북마크 리본 데코레이션 */}
        <div className={styles.bookmarkRibbon}>
          <span className={styles.bookmarkStar}>★</span>
        </div>
      </div>

      {/* ── 캐릭터 라이브러리 섹션 (카드 하단 배치) ── */}
      <section className={styles.librarySection}>
        <h2 className={styles.libraryTitle}>캐릭터 라이브러리</h2>
        {loadError && <p className={styles.error}>{loadError}</p>}
        <CharacterList />
      </section>

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
  )
}

