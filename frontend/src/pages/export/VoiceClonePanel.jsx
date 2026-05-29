import { useState } from 'react'
import {
  generateClonedVoice,
  uploadVoiceSample,
} from '@/api/voiceApi'

export function VoiceClonePanel({
  characters,
  selectedCharacterId,
  onVoiceProfileSaved,
}) {
  const [characterId, setCharacterId] = useState(
    selectedCharacterId ?? characters[0]?.id ?? '',
  )
  const [referenceFile, setReferenceFile] = useState(null)
  const [referenceText, setReferenceText] = useState('')
  const [testText, setTestText] = useState('달빛 숲으로 가 보자!')
  const [statusMessage, setStatusMessage] = useState('샘플 업로드 전')
  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [testAudio, setTestAudio] = useState(null)

  const selectedCharacter = characters.find((character) => character.id === characterId)

  async function handleUploadSample() {
    setIsUploading(true)
    setStatusMessage('목소리 샘플을 저장하는 중입니다.')

    try {
      const result = await uploadVoiceSample({
        characterId,
        file: referenceFile,
        referenceText,
      })
      onVoiceProfileSaved(result.characterId, result.voiceProfile)
      setStatusMessage('클론 목소리 프로필을 저장했습니다.')
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : '목소리 샘플 저장 실패',
      )
    } finally {
      setIsUploading(false)
    }
  }

  async function handleGenerateTestVoice() {
    setIsGenerating(true)
    setStatusMessage('클론 목소리로 테스트 음성을 생성하는 중입니다.')

    try {
      const result = await generateClonedVoice({
        characterId,
        text: testText,
      })
      setTestAudio(result)
      setStatusMessage('테스트 음성 생성 완료')
    } catch (error) {
      setStatusMessage(
        error instanceof Error ? error.message : '테스트 음성 생성 실패',
      )
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <section className="voice-clone-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">R-56 · R-57</p>
          <h2>보이스 클로닝</h2>
        </div>
        <p className="panel-description">
          캐릭터에 업로드한 음성 샘플을 묶고, 이후 같은 목소리로 대사를
          재사용하는 흐름입니다.
        </p>
      </div>

      <div className="voice-profile-summary">
        <span>현재 캐릭터</span>
        <strong>{selectedCharacter?.name ?? '캐릭터 없음'}</strong>
        <span>
          목소리 모드: {selectedCharacter?.voice_profile?.mode ?? 'preset'}
        </span>
      </div>

      <div className="voice-clone-grid">
        <label>
          캐릭터
          <select
            value={characterId}
            onChange={(event) => setCharacterId(event.target.value)}
          >
            {characters.map((character) => (
              <option key={character.id} value={character.id}>
                {character.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          음성 샘플
          <input
            accept="audio/*"
            type="file"
            onChange={(event) => {
              setReferenceFile(event.target.files?.[0] ?? null)
            }}
          />
        </label>

        <label className="wide-field">
          샘플에서 말한 문장
          <textarea
            placeholder="예: 안녕, 나는 달빛 숲의 루나야."
            rows={3}
            value={referenceText}
            onChange={(event) => setReferenceText(event.target.value)}
          />
        </label>

        <label className="wide-field">
          테스트 합성 문장
          <textarea
            rows={3}
            value={testText}
            onChange={(event) => setTestText(event.target.value)}
          />
        </label>
      </div>

      <p className="voice-consent">
        본인 또는 사용 허가를 받은 음성만 업로드해 주세요.
      </p>

      <div className="voice-clone-actions">
        <button
          type="button"
          disabled={!characterId || !referenceFile || isUploading}
          onClick={handleUploadSample}
        >
          {isUploading ? '저장 중...' : '목소리 저장'}
        </button>
        <button
          type="button"
          disabled={!characterId || !testText.trim() || isGenerating}
          onClick={handleGenerateTestVoice}
        >
          {isGenerating ? '합성 중...' : '테스트 합성'}
        </button>
      </div>

      <p className="voice-status">{statusMessage}</p>

      {testAudio?.audioPath && (
        <audio className="audio-player" controls src={testAudio.audioPath}>
          이 브라우저는 오디오 재생을 지원하지 않습니다.
        </audio>
      )}
    </section>
  )
}
