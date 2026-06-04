import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getEmotions, parseStory } from '@/api/stories'
import styles from './StoryInputPage.module.css'

// 작성 중 데이터는 DB에 저장하지 않고 이 컴포넌트 state 에서만 다룬다.
// 제출(씬 분해하기) 시에만 structured payload 로 백엔드에 새 story 를 생성한다.

const DEFAULT_EMOTION_LABEL = '잔잔함' // 새 item 기본 감정(= calm)
// 감정 옵션은 GET /api/stories/emotions 에서 받아온다(하드코딩 금지).
// API 실패 시 select 가 비지 않도록 최소 시드만 둔다.
const EMOTION_SEED = [{ label: DEFAULT_EMOTION_LABEL, value: 'calm' }]

let _uid = 0
const uid = () => (_uid += 1)

const makeItem = () => ({ id: uid(), emotionLabel: DEFAULT_EMOTION_LABEL, speaker: '', text: '' })
const makeScene = () => ({ id: uid(), items: [makeItem()] })
const initialScenes = () => [makeScene()]

export default function StoryInputPage() {
  const navigate = useNavigate()
  const { setStoryId, setStoryTitle, setScenes } = useStoryStore()

  const [title, setTitle] = useState('')
  const [scenes, setLocalScenes] = useState(initialScenes)
  const [emotions, setEmotions] = useState(EMOTION_SEED)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showCancel, setShowCancel] = useState(false)
  const titleInputRef = useRef(null)

  // 감정 옵션 로드(실패해도 시드로 동작)
  useEffect(() => {
    getEmotions()
      .then((list) => {
        if (Array.isArray(list) && list.length) setEmotions(list)
      })
      .catch(() => {})
  }, [])

  // ── scene/item state 조작(모두 프론트 state 에서만) ──
  const addScene = () => setLocalScenes((prev) => [...prev, makeScene()])

  const removeScene = (sceneId) =>
    setLocalScenes((prev) => (prev.length > 1 ? prev.filter((s) => s.id !== sceneId) : prev))

  const addItem = (sceneId) =>
    setLocalScenes((prev) =>
      prev.map((s) => (s.id === sceneId ? { ...s, items: [...s.items, makeItem()] } : s)),
    )

  const removeItem = (sceneId, itemId) =>
    setLocalScenes((prev) =>
      prev.map((s) =>
        s.id === sceneId && s.items.length > 1
          ? { ...s, items: s.items.filter((it) => it.id !== itemId) }
          : s,
      ),
    )

  const updateItem = (sceneId, itemId, field, value) =>
    setLocalScenes((prev) =>
      prev.map((s) =>
        s.id === sceneId
          ? {
              ...s,
              items: s.items.map((it) => (it.id === itemId ? { ...it, [field]: value } : it)),
            }
          : s,
      ),
    )

  // ── 취소/초기화 ──
  const isDirty =
    title.trim() !== '' ||
    scenes.length > 1 ||
    scenes.some(
      (s) => s.items.length > 1 || s.items.some((it) => it.text.trim() || it.speaker.trim()),
    )

  const resetAll = () => {
    setTitle('')
    setLocalScenes(initialScenes())
    setError(null)
  }

  const handleCancelClick = () => {
    if (isDirty) setShowCancel(true)
    else resetAll()
  }

  const confirmCancel = () => {
    resetAll()
    setShowCancel(false)
  }

  // ── 제출(validation 통과 시에만 DB 생성) ──
  const allTextsFilled = scenes.every((s) => s.items.every((it) => it.text.trim() !== ''))
  const canSubmit = !!title.trim() && scenes.length >= 1 && allTextsFilled && !loading

  async function handleSubmit() {
    if (!canSubmit) return
    setLoading(true)
    setError(null)
    try {
      const payload = {
        title: title.trim(),
        inputMode: 'structured',
        scenes: scenes.map((s, i) => ({
          sceneOrder: i + 1,
          items: s.items.map((it) => ({
            emotion: emotions.find((e) => e.label === it.emotionLabel)?.value,
            emotionLabel: it.emotionLabel,
            speaker: it.speaker.trim(),
            text: it.text.trim(),
          })),
        })),
      }
      const result = await parseStory(payload)
      setStoryId(result.storyId)
      setStoryTitle(result.title)
      setScenes(result.scenes)
      navigate(`/scene-check?storyId=${encodeURIComponent(result.storyId)}`)
    } catch {
      setError('스토리 저장에 실패했습니다. 백엔드 서버가 실행 중인지 확인해 주세요.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <h1>스토리 입력</h1>
      <p className={styles.guide}>
        씬과 대사를 직접 추가해 주세요. 감정을 고르고, <b>역할이 비어 있으면 나레이션</b>, 입력하면 그
        인물의 대사로 처리됩니다. 따옴표나 <code>화자: "대사"</code> 문법은 입력하지 않아도 됩니다.
      </p>

      <label className={styles.field}>
        제목
        <input
          ref={titleInputRef}
          className={styles.titleInput}
          placeholder="예: 어린 왕자"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={60}
        />
      </label>

      <div className={styles.scenes}>
        {scenes.map((scene, sIdx) => (
          <div className={styles.sceneCard} key={scene.id}>
            <div className={styles.sceneHeader}>
              <span className={styles.scenePill}>Scene {String(sIdx + 1).padStart(2, '0')}</span>
              <button
                type="button"
                className={styles.sceneDelBtn}
                onClick={() => removeScene(scene.id)}
                disabled={scenes.length <= 1}
                title={scenes.length <= 1 ? '씬은 최소 1개 필요합니다' : '씬 삭제'}
              >
                씬 삭제 ×
              </button>
            </div>

            {scene.items.map((item) => (
              <div className={styles.itemRow} key={item.id}>
                <select
                  className={styles.emotionSelect}
                  value={item.emotionLabel}
                  onChange={(e) => updateItem(scene.id, item.id, 'emotionLabel', e.target.value)}
                  aria-label="감정 선택"
                >
                  {/* 현재 값이 옵션에 없으면(로딩 전) 보이도록 보강 */}
                  {!emotions.some((e) => e.label === item.emotionLabel) && (
                    <option value={item.emotionLabel}>{item.emotionLabel}</option>
                  )}
                  {emotions.map((e) => (
                    <option key={e.label} value={e.label}>
                      {e.label}
                    </option>
                  ))}
                </select>

                <input
                  className={styles.roleInput}
                  placeholder="역할 (비우면 나레이션)"
                  value={item.speaker}
                  onChange={(e) => updateItem(scene.id, item.id, 'speaker', e.target.value)}
                  maxLength={40}
                />

                <input
                  className={styles.textInput}
                  placeholder="텍스트를 입력해주세요..."
                  value={item.text}
                  onChange={(e) => updateItem(scene.id, item.id, 'text', e.target.value)}
                />

                <button
                  type="button"
                  className={styles.itemDelBtn}
                  onClick={() => removeItem(scene.id, item.id)}
                  disabled={scene.items.length <= 1}
                  title={scene.items.length <= 1 ? '대사는 최소 1개 필요합니다' : '대사 삭제'}
                  aria-label="대사 삭제"
                >
                  ×
                </button>
              </div>
            ))}

            <div className={styles.sceneActions}>
              <button type="button" className={styles.addItemBtn} onClick={() => addItem(scene.id)}>
                대사 추가하기 +
              </button>
            </div>
          </div>
        ))}
      </div>

      <button type="button" className={styles.addSceneBtn} onClick={addScene}>
        씬 추가하기 +
      </button>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.actions}>
        <button type="button" className={styles.cancelBtn} onClick={handleCancelClick}>
          초기화
        </button>
        <button
          type="button"
          className={styles.submitBtn}
          onClick={handleSubmit}
          disabled={!canSubmit}
        >
          {loading ? '저장 중...' : '씬 분해하기'}
        </button>
      </div>

      {!loading && !title.trim() && (
        <p className={styles.hint}>제목을 입력하고 모든 텍스트를 채우면 씬 분해하기가 활성화됩니다.</p>
      )}

      {showCancel && (
        <div className={styles.modalOverlay} onClick={() => setShowCancel(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <p className={styles.modalTitle}>작성 중인 스토리를 취소할까요?</p>
            <p className={styles.modalDesc}>입력한 내용은 저장되지 않습니다.</p>
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.modalKeepBtn}
                onClick={() => setShowCancel(false)}
              >
                계속 작성하기
              </button>
              <button type="button" className={styles.modalConfirmBtn} onClick={confirmCancel}>
                취소하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
