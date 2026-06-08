import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getEmotions, parseStory } from '@/api/stories'
import styles from './StoryInputPage.module.css'

import useSwingingSignboard from '@/hooks/useSwingingSignboard'
import headerBg from '@design/assets/figma-icons/Base/Base_Stoty_input.png'
import characterStoryInputSvg from '@design/assets/figma-icons/character/character_story_input.svg'

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
  const { titleRef, frameHeight } = useSwingingSignboard(1088 / 1470)
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



  // 취소 확인 알림용 초기화
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
      {/* ── 상단 헤더 영역 (밤하늘 배경 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>이번엔 동화 속으로 들어가볼까요?</div>
          <h1 className={styles.headerTitle}>동화<br />스토리 만들기</h1>
          <p className={styles.headerDesc}>
            내레이션과 대사를 입력하세요<br />
            자동으로 씬 분할과 대사형식으로<br />
            스토리가 나누어집니다.
          </p>
        </div>
        <div className={styles.headerRight}>
          <div 
            className={styles.titleFrame} 
            ref={titleRef}
            style={{
              display: 'block',
              width: '100%',
              height: frameHeight ? `${frameHeight}px` : 'auto',
              position: 'relative'
            }}
          >
            <img 
              src={characterStoryInputSvg} 
              alt="스토리 입력 타이틀 액자" 
              className={styles.titleFrameImg} 
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
            />
          </div>
        </div>
      </header>

      {/* ── 내용 컨테이너 ── */}
      <div className={styles.bookContainer}>



        <div className={styles.bookContentOverlay}>
          <div className={styles.formScrollArea}>
            {/* 제목 입력 섹션 */}
            <div className={styles.fieldSection}>
              <h2 className={styles.fieldLabel}>제목</h2>
              <input
                ref={titleInputRef}
                className={styles.titleInput}
                placeholder="예: 어린 왕자"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={60}
              />
            </div>

            {/* 씬 리스트 */}
            <div className={styles.scenes}>
              {scenes.map((scene, sIdx) => (
                <div className={styles.sceneCard} key={scene.id}>
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

                  <div className={styles.itemsList}>
                    {scene.items.map((item) => (
                      <div className={styles.itemRow} key={item.id}>
                        {/* 감정 선택 커스텀 셀렉트 */}
                        <div className={styles.selectWrapper}>
                          <select
                            className={styles.emotionSelect}
                            value={item.emotionLabel}
                            onChange={(e) => updateItem(scene.id, item.id, 'emotionLabel', e.target.value)}
                            aria-label="감정 선택"
                          >
                            {!emotions.some((e) => e.label === item.emotionLabel) && (
                              <option value={item.emotionLabel}>{item.emotionLabel}</option>
                            )}
                            {emotions.map((e) => (
                              <option key={e.label} value={e.label}>
                                {e.label}
                              </option>
                            ))}
                          </select>
                          <span className={styles.arrowIcon}>∨</span>
                        </div>

                        {/* 역할 입력 */}
                        <input
                          className={styles.roleInput}
                          placeholder="역할"
                          value={item.speaker}
                          onChange={(e) => updateItem(scene.id, item.id, 'speaker', e.target.value)}
                          maxLength={40}
                        />

                        {/* 대사/내용 입력 */}
                        <input
                          className={styles.textInput}
                          placeholder="스토리를 입력해주세요..."
                          value={item.text}
                          onChange={(e) => updateItem(scene.id, item.id, 'text', e.target.value)}
                        />

                        {/* 대사 삭제 버튼 */}
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
                  </div>

                  <div className={styles.sceneActions}>
                    <button type="button" className={styles.addItemBtn} onClick={() => addItem(scene.id)}>
                      대사 추가하기 +
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* 씬 추가하기 버튼 */}
            <button type="button" className={styles.addSceneBtn} onClick={addScene}>
              씬 추가하기 +
            </button>

            {error && <p className={styles.error}>{error}</p>}
          </div>

          {/* ── 하단 액션 네비게이션 (Book 내지 우측 하단 고정) ── */}
          <div className={styles.fixedPageNav}>
            <div className={styles.pageNav}>
              <button type="button" className={styles.btnSecondary} onClick={handleCancelClick}>
                초기화
              </button>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                {loading ? '저장 중...' : '씬 분해하기 →'}
              </button>
            </div>

            {!loading && !title.trim() && (
              <p className={styles.hint}>제목을 입력하고 모든 텍스트를 채우면 씬 분해하기가 활성화됩니다.</p>
            )}
          </div>
        </div>
      </div>

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
