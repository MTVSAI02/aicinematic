import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useCharacterStore from '@/store/useCharacterStore'
import styles from './CharacterPage.module.css'

export default function CharacterPage() {
  const navigate = useNavigate()
  const { characters, addCharacter, selectCharacter } = useCharacterStore()
  const [name, setName] = useState('')
  const [tags, setTags] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    try {
      // TODO: POST /characters → AI character.py 호출
      // const character = await characterApi.create({ name, tags })
      // addCharacter(character)

      // 백엔드 연동 전 임시 mock
      const mockCharacter = {
        id: crypto.randomUUID(),
        name,
        tags,
        image_url: null,
        locked: false,
        voice_profile: {
          id: null,
          character_id: null,
          mode: 'preset',
          label: '기본 목소리',
          speaker: 'Sohee',
          reference_audio_url: null,
          reference_text: null,
          sample_audio_url: null,
        },
      }
      addCharacter(mockCharacter)
      setName('')
      setTags('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <h1>캐릭터</h1>

      <section className={styles.section}>
        <h2>새 캐릭터 생성</h2>
        <div className={styles.form}>
          <label className={styles.label}>
            이름
            <input
              className={styles.input}
              placeholder="어린왕자"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className={styles.label}>
            외모 태그
            <input
              className={styles.input}
              placeholder="blonde hair, small boy, blue coat, curious eyes"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
          </label>
          <button
            className={styles.btn}
            onClick={handleCreate}
            disabled={!name.trim() || loading}
          >
            {loading ? '생성 중...' : '캐릭터 생성'}
          </button>
        </div>
      </section>

      <section className={styles.section}>
        <h2>캐릭터 라이브러리</h2>
        {characters.length === 0 ? (
          <p className={styles.empty}>아직 생성된 캐릭터가 없어요.</p>
        ) : (
          <ul className={styles.grid}>
            {characters.map((c) => (
              <li
                key={c.id}
                className={styles.card}
                onClick={() => selectCharacter(c.id)}
              >
                <div className={styles.thumb}>
                  {c.image_url
                    ? <img src={c.image_url} alt={c.name} className={styles.thumbImg} />
                    : <span className={styles.thumbEmpty}>생성 중</span>
                  }
                </div>
                <span>{c.name}</span>
                {c.locked && <span className={styles.lockBadge}>🔒 락</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/scene-check')}>
          ← 씬 확인
        </button>
        <button className={styles.btn} onClick={() => navigate('/scene-editor')}>
          씬 편집 →
        </button>
      </div>
    </div>
  )
}
