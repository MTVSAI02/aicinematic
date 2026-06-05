import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import BackgroundPromptPanel from '@/components/backgrounds/BackgroundPromptPanel'
import BackgroundLibrary from '@/components/backgrounds/BackgroundLibrary'
import styles from './BackgroundPage.module.css'

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
        // 실패를 "빈 목록"으로 숨기지 않고 에러로 표시한다.
        setLoadError(`배경 목록을 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [setBackgrounds])

  return (
    <div className={styles.page}>
      <h1>배경</h1>
      <p className={styles.cardMeta}>
        프롬프트로 배경을 생성하면 <b>1장이 만들어져 곧바로 라이브러리에 저장</b>됩니다. 저장한 배경을 특정 씬에 연결하는 것은 “씬 편집”에서 합니다.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. 프롬프트 & 배경 생성</h2>
        <BackgroundPromptPanel />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. 배경 라이브러리</h2>
        <p className={styles.cardMeta}>생성한 배경이 여기에 쌓입니다. 씬에 배경을 연결하는 것은 “씬 편집”에서 합니다.</p>
        {loadError && <p className={styles.error}>{loadError}</p>}
        <BackgroundLibrary />
      </section>

      <div className={styles.pageNav}>
        <button className={styles.btnSecondary} onClick={() => navigate('/voice')}>
          ← 보이스
        </button>
        <button className={styles.btn} onClick={() => navigate('/scene-editor')}>
          씬 편집 →
        </button>
      </div>
    </div>
  )
}
