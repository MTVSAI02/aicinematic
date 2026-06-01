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
    storyId, sceneId, promptInput, negativePrompt, sourceText,
    promptSuffix, loading, error,
    setPromptInput, setPromptSuffix, setNegativePrompt,
    setSourceText, setCandidates, setCurrentJobId, setSelectedCandidateId,
    setLoading, setError, resetCandidates,
  } = useBackgroundStore()

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
      setNegativePrompt(res.negativePrompt)
    } catch (e) {
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    if (!promptInput.trim() || loading) return
    setError(null)
    setLoading(true)
    resetCandidates()
    try {
      // 주의: finalPrompt 가 아니라 promptInput 만 보낸다. count 도 보내지 않는다.
      // 비동기: 즉시 jobId 반환 → completed/failed 까지 폴링
      const job = await backgroundApi.generateBackground({
        prompt: promptInput.trim(),
        negativePrompt: negativePrompt || undefined,
      })
      setCurrentJobId(job.jobId)

      const finished = await pollJob(job.jobId)
      setCandidates(finished.result?.candidates ?? [])
      setSelectedCandidateId(null)
    } catch (e) {
      setError(getApiErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const canSuggest = !!storyId.trim() && !!sceneId.trim() && !loading
  const canGenerate = !!promptInput.trim() && !loading

  return (
    <div className={styles.form}>
      {/* 사용법 안내: 씬 선택은 선택사항, 핵심은 배경 프롬프트 */}
      <p className={styles.help}>
        <strong>배경 프롬프트만 있으면 후보를 만들 수 있어요.</strong> 아래 “배경 프롬프트”에 원하는 배경을
        직접 적고 <strong>[배경 후보 생성]</strong>을 누르면 됩니다.
        <br />
        어떤 배경을 넣을지 막막하면, <strong>(선택)</strong> 스토리·씬을 골라 그 장면에 어울리는 프롬프트를
        자동으로 추천받을 수 있어요. <strong>스토리·씬 선택은 필수가 아닙니다.</strong>
      </p>

      {/* (선택) 씬 기반 추천 */}
      <p className={styles.stepLabel}>① (선택) 씬에서 프롬프트 추천받기</p>
      <p className={styles.hint}>
        스토리와 씬을 고르면 그 장면 내용으로 배경 프롬프트가 아래에 자동으로 채워집니다.
        건너뛰고 바로 직접 입력해도 됩니다.
      </p>
      <StorySceneSelect />
      <button className={styles.btnSecondary} onClick={handleSuggest} disabled={!canSuggest}>
        씬에서 배경 프롬프트 추천받기
      </button>

      {sourceText && (
        <p className={styles.validation}>참고 문장: {sourceText}</p>
      )}

      <p className={styles.divider}>— 또는 직접 입력 —</p>

      {/* 프롬프트 입력/수정 (실제로 생성에 쓰이는 값) */}
      <p className={styles.stepLabel}>② 배경 프롬프트 (필수)</p>
      <p className={styles.hint}>
        이 내용으로 후보가 생성됩니다. 추천받은 문장을 수정해도 되고, 처음부터 직접 써도 됩니다.
      </p>
      <label className={styles.label}>
        <textarea
          className={styles.textarea}
          placeholder="예) 별빛이 비치는 조용한 사막, 따뜻한 동화풍 배경"
          value={promptInput}
          onChange={(e) => setPromptInput(e.target.value)}
        />
      </label>

      {finalPromptPreview && (
        <div className={styles.label}>
          finalPrompt 미리보기 (현재 프롬프트 기준 · 전송되지 않음 · 실제 조립은 백엔드)
          <div className={styles.preview}>{finalPromptPreview}</div>
        </div>
      )}
      {negativePrompt && (
        <p className={styles.cardMeta}>negativePrompt: {negativePrompt}</p>
      )}

      <button className={styles.btn} onClick={handleGenerate} disabled={!canGenerate}>
        {loading ? '처리 중...' : '배경 후보 생성'}
      </button>

      {!promptInput.trim() && !loading && (
        <p className={styles.validation}>배경 프롬프트를 입력하거나 추천을 받아주세요.</p>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}
