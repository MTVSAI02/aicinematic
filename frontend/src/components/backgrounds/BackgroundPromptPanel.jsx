import { useEffect, useRef, useState } from 'react'
import useBackgroundStore from '@/store/useBackgroundStore'
import * as backgroundApi from '@/api/backgrounds'
import { pollJob } from '@/utils/pollJob'
import { getApiErrorMessage } from '@/utils/apiError'
import StorySceneSelect from './StorySceneSelect'
import styles from '@/pages/background/BackgroundPage.module.css'

// finalPrompt = "{suggestedPrompt}, {suffix}" 이므로, 둘을 비교해 suffix(배경 규칙)만 추출한다.
// 백엔드 suffix 문자열을 프론트에 하드코딩하지 않기 위함.
function extractSuffix(suggestedPrompt, finalPrompt) {
  const prefix = `${suggestedPrompt}, `
  return finalPrompt.startsWith(prefix) ? finalPrompt.slice(prefix.length) : ''
}

export default function BackgroundPromptPanel() {
  const {
    storyId, sceneId, promptInput, sourceText,
    promptSuffix, loading, error,
    setPromptInput, setPromptSuffix,
    setSourceText, setCurrentJobId, setBackgrounds,
    setLoading, setError,
  } = useBackgroundStore()

  // 언마운트 시 진행 중 폴링 취소 (페이지 이동 후 늦게 끝난 Job이 store를 갱신하는 것 방지)
  const abortRef = useRef(null)
  useEffect(() => () => abortRef.current?.abort(), [])

  const [savedMessage, setSavedMessage] = useState('')
  const [name, setName] = useState('') // 배경 제목(필수)

  // finalPrompt 미리보기는 항상 현재 promptInput 기준으로 실시간 계산한다 (stale 방지).
  // suffix(배경 규칙)는 추천 응답에서 추출해 보관한 값. 추천을 안 받았으면 미리보기는 표시하지 않는다.
  const finalPromptPreview =
    promptInput.trim() && promptSuffix ? `${promptInput.trim()}, ${promptSuffix}` : ''

  async function handleSuggest() {
    if (!storyId.trim() || !sceneId.trim()) return
    setError(null)
    setLoading(true)
    try {
      const res = await backgroundApi.suggestBackgroundPrompt({
        storyId: storyId.trim(),
        sceneId: sceneId.trim(),
      })
      setSourceText(res.sourceText)
      setPromptInput(res.suggestedPrompt)        // 사용자가 수정할 원본 프롬프트
      // 백엔드가 붙인 suffix(배경 규칙)를 추출해 보관 → 미리보기는 promptInput 기준 실시간 계산
      setPromptSuffix(extractSuffix(res.suggestedPrompt, res.finalPrompt))
    } catch (e) {
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    if (!name.trim() || !promptInput.trim() || loading) return
    setError(null)
    setSavedMessage('')
    setLoading(true)
    try {
      // 제목(name) + prompt 전송(finalPrompt 조립은 백엔드). 비동기: 즉시 jobId → completed/failed 폴링.
      const job = await backgroundApi.generateBackground({
        name: name.trim(),
        prompt: promptInput.trim(),
      })
      setCurrentJobId(job.jobId)

      abortRef.current = new AbortController()
      await pollJob(job.jobId, { signal: abortRef.current.signal })
      // 1장 생성 즉시 백엔드가 라이브러리에 저장(name=제목) → 목록 갱신(아래 라이브러리에 바로 표시)
      const list = await backgroundApi.getBackgrounds()
      setBackgrounds(list)
      setName('')
      setSavedMessage('배경이 생성되어 라이브러리에 저장되었습니다.')
    } catch (e) {
      if (e.aborted) return // 언마운트 취소 → 무시
      if (e.timedOut) {
        setError('배경 생성이 오래 걸리고 있어요. 잠시 후 라이브러리를 새로고침해 확인해주세요.')
      } else {
        setError(getApiErrorMessage(e))
      }
    } finally {
      setLoading(false)
    }
  }

  const canSuggest = !!storyId.trim() && !!sceneId.trim() && !loading
  const canGenerate = !!name.trim() && !!promptInput.trim() && !loading

  return (
    <div className={styles.form}>
      
      {/* 씬 기반 추천 드롭다운 */}
      <StorySceneSelect />
      
      <div className={styles.centerBtnRow}>
        <button className={styles.recommendBtn} onClick={handleSuggest} disabled={!canSuggest}>
          🪄 씬에서 배경 프롬프트 추천받기
        </button>
      </div>

      {sourceText && (
        <p className={styles.validation}>참고 문장: {sourceText}</p>
      )}

      {/* 배경 제목 (필수) */}
      <div className={styles.fieldSection}>
        <label className={styles.fieldLabel}>배경 제목</label>
        <input
          className={styles.titleInput}
          placeholder="예) 별빛 사막"
          value={name}
          maxLength={40}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      {/* 프롬프트 입력/수정 */}
      <div className={styles.fieldSection}>
        <label className={styles.fieldLabel}>배경 프롬프트</label>
        <div className={styles.textareaWrapper}>
          <textarea
            className={styles.textarea}
            placeholder="예) 별빛이 비치는 조용한 숲속, 따뜻한 동화풍 배경"
            value={promptInput}
            maxLength={500}
            onChange={(e) => setPromptInput(e.target.value)}
          />
          <span className={styles.charCounter}>{promptInput.length} / 500</span>
        </div>
      </div>

      <div className={styles.centerBtnRow}>
        <button className={styles.generateBtn} onClick={handleGenerate} disabled={!canGenerate || loading}>
          {loading ? (
            <>
              <span className={styles.spinner} /> 생성 중...
            </>
          ) : (
            '✨ 배경 생성'
          )}
        </button>
      </div>

      {!loading && (!name.trim() || !promptInput.trim()) && (
        <p className={styles.validation}>
          {!name.trim() ? '배경 제목을 입력해주세요.' : '배경 프롬프트를 입력하거나 추천을 받아주세요.'}
        </p>
      )}
      {savedMessage && <p className={styles.status}>{savedMessage}</p>}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}
