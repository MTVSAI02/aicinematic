import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import { getApiErrorMessage } from '@/utils/apiError'
import AiConnectionCheck from '@/components/AiConnectionCheck'
import CharacterCreateForm from '@/components/characters/CharacterCreateForm'
import CharacterList from '@/components/characters/CharacterList'
import styles from './CharacterPage.module.css'

export default function CharacterPage() {
  const navigate = useNavigate()
  const setCharacters = useCharacterStore((s) => s.setCharacters)
  const [loadError, setLoadError] = useState('')

  // 페이지 진입 시 백엔드 캐릭터 목록으로 store 동기화 (최종 저장소는 백엔드)
  useEffect(() => {
    characterApi
      .getCharacters()
      .then((list) => {
        setCharacters(list)
        setLoadError('')
      })
      .catch((e) => {
        // 실패를 "빈 목록"으로 숨기지 않고 에러로 표시 (데이터 없음 vs 서버 오류 구분)
        setLoadError(`캐릭터 목록을 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [setCharacters])

  return (
    <div className={styles.page}>
      <h1>캐릭터</h1>

      {/* 임시: AI(ComfyUI) 연결 확인 — 실제 연동 시 삭제 (TEMP_AI_CONNECTION_TEST.md) */}
      <AiConnectionCheck />

      <section className={styles.section}>
        <h2>새 캐릭터 생성</h2>
        <CharacterCreateForm />
      </section>

      <section className={styles.section}>
        <h2>캐릭터 라이브러리</h2>
        {loadError && <p className={styles.error}>{loadError}</p>}
        <CharacterList />
      </section>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-check')}>
          ← 씬 확인
        </button>
        <button className={styles.btn} onClick={() => navigate('/voice')}>
          보이스 →
        </button>
      </div>
    </div>
  )
}
