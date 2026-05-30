import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useCharacterStore from '@/store/useCharacterStore'
import * as characterApi from '@/api/characters'
import AiConnectionCheck from '@/components/AiConnectionCheck'
import CharacterCreateForm from '@/components/characters/CharacterCreateForm'
import CharacterList from '@/components/characters/CharacterList'
import styles from './CharacterPage.module.css'

export default function CharacterPage() {
  const navigate = useNavigate()
  const setCharacters = useCharacterStore((s) => s.setCharacters)

  // 페이지 진입 시 백엔드 캐릭터 목록으로 store 동기화 (최종 저장소는 백엔드)
  useEffect(() => {
    characterApi
      .getCharacters()
      .then(setCharacters)
      .catch(() => {
        // 초기 목록 로딩 실패는 빈 목록으로 처리 (생성/연결확인에서 에러가 드러남)
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
        <CharacterList />
      </section>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-check')}>
          ← 씬 확인
        </button>
        <button className={styles.btn} onClick={() => navigate('/background')}>
          배경 →
        </button>
      </div>
    </div>
  )
}
