import { useState } from 'react'
import useVoiceStore from '@/store/useVoiceStore'
import { createVoice } from '@/api/voices'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from '@/pages/voice/VoicePage.module.css'

// 새 보이스 생성 폼. name/description/voicePrompt 만 받는다.
// provider/model/sampleAudioUrl 은 AI 결과 필드라 입력 UI 를 두지 않는다.
// 생성된 보이스는 백엔드 기본값상 voiceType="character" (내 보이스 섹션에 추가됨).
export default function VoiceCreateForm() {
  const addVoice = useVoiceStore((s) => s.addVoice)
  const setMessage = useVoiceStore((s) => s.setMessage)
  const setError = useVoiceStore((s) => s.setError)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [voicePrompt, setVoicePrompt] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const created = await createVoice({
        name: name.trim(),
        description: description.trim() || null,
        voicePrompt: voicePrompt.trim() || null,
      })
      addVoice(created)
      setMessage(`보이스 “${created.name}”을(를) 생성했습니다.`)
      setName('')
      setDescription('')
      setVoicePrompt('')
    } catch (err) {
      setMessage(null)
      setError(getApiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label className={styles.label}>
        이름
        <input
          className={styles.input}
          value={name}
          placeholder="예: 따뜻한 소년 목소리"
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={styles.label}>
        설명
        <input
          className={styles.input}
          value={description}
          placeholder="밝고 호기심 많은 톤"
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <label className={styles.label}>
        보이스 프롬프트
        <textarea
          className={styles.textarea}
          value={voicePrompt}
          placeholder="warm curious boy voice"
          onChange={(e) => setVoicePrompt(e.target.value)}
        />
      </label>
      <button className={styles.btn} type="submit" disabled={!name.trim() || submitting}>
        {submitting ? '생성 중…' : '보이스 생성'}
      </button>
      <p className={styles.hint}>
        생성한 보이스는 “캐릭터용”으로 만들어집니다. 실제 음성·미리듣기 샘플은 AI 단계에서 채워집니다.
      </p>
    </form>
  )
}
