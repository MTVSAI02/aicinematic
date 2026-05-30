import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import BackgroundPromptPanel from '@/components/backgrounds/BackgroundPromptPanel'
import BackgroundCandidateGrid from '@/components/backgrounds/BackgroundCandidateGrid'
import BackgroundSaveForm from '@/components/backgrounds/BackgroundSaveForm'
import BackgroundLibrary from '@/components/backgrounds/BackgroundLibrary'
import AiConnectionCheck from '@/components/AiConnectionCheck'
import { getBackgroundComfyHealth } from '@/api/ai'
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
        배경은 후보를 생성한 뒤 1장을 골라 라이브러리에 저장합니다. 저장한 배경을 특정 씬에 연결하는 것은 “씬 편집”에서 합니다.
      </p>

      {/* 임시: 배경 전용 경로(프론트→백→AI 배경 모듈→ComfyUI 읽기전용) 연결 확인.
          실제 연동 시 삭제 — TEMP_AI_CONNECTION_TEST.md */}
      <AiConnectionCheck
        check={getBackgroundComfyHealth}
        label="배경 AI 서버 연결 확인"
        okText="배경 AI 서버 연결됨 ✅"
      />

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. 프롬프트 & 후보 생성</h2>
        <BackgroundPromptPanel />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. 생성된 후보</h2>
        <BackgroundCandidateGrid />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3. 선택한 후보 저장</h2>
        <BackgroundSaveForm />
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>4. 배경 라이브러리</h2>
        <p className={styles.cardMeta}>씬에 배경을 연결하는 것은 “씬 편집”에서 합니다.</p>
        {loadError && <p className={styles.error}>{loadError}</p>}
        <BackgroundLibrary />
      </section>

      <div className={styles.pageNav}>
        <button className={styles.btnSecondary} onClick={() => navigate('/character')}>
          ← 캐릭터
        </button>
        <button className={styles.btn} onClick={() => navigate('/scene-editor')}>
          씬 편집 →
        </button>
      </div>
    </div>
  )
}
