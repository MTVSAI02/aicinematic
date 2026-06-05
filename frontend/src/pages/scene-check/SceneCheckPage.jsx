import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getStory } from '@/api/stories'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from './SceneCheckPage.module.css'

import titleSvg from '@design/assets/figma-icons/Scene-_Check/title.svg'
import headerBg from '@design/assets/figma-icons/Scene-_Check/BACJ.png'
import bookBg from '@design/assets/figma-images/Book.png'
import rirurChar from '@design/assets/figma-icons/RIrur.svg'

const RIRUR_POSITIONS = [
  { left: '-160px', top: '22%', transform: 'translateX(200px) scale(0.1)', activeTransform: 'translateX(-100px) scale(1) rotate(-75deg)', origin: 'center right' },
  { left: '-160px', top: '62%', transform: 'translateX(200px) scale(0.1)', activeTransform: 'translateX(-100px) scale(1) rotate(-105deg)', origin: 'center right' },
  { right: '-160px', top: '22%', transform: 'translateX(-200px) scale(0.1)', activeTransform: 'translateX(100px) scale(1) rotate(75deg)', origin: 'center left' },
  { right: '-160px', top: '62%', transform: 'translateX(-200px) scale(0.1)', activeTransform: 'translateX(100px) scale(1) rotate(105deg)', origin: 'center left' },
  { bottom: '-160px', left: '46%', transform: 'translateY(-200px) scale(0.1) rotate(180deg)', activeTransform: 'translateY(110px) scale(1) rotate(180deg)', origin: 'top center' },
]

export default function SceneCheckPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { scenes, storyId, storyTitle, setScenes, setStoryId, setStoryTitle } = useStoryStore()

  const effectiveStoryId = searchParams.get('storyId') || storyId
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rirurPos, setRirurPos] = useState(null)
  const [rirurVisible, setRirurVisible] = useState(false)

  const titleRef = useRef(null)

  useEffect(() => {
    if (scenes.length > 0 || !effectiveStoryId) return
    setLoading(true)
    setError('')
    getStory(effectiveStoryId)
      .then((story) => {
        setStoryId(story.storyId)
        setStoryTitle(story.title)
        setScenes(story.scenes)
      })
      .catch((e) => setError(getApiErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [effectiveStoryId, scenes.length, setScenes, setStoryId, setStoryTitle])

  useEffect(() => {
    let timer
    const scheduleNextPop = () => {
      const delay = Math.random() * 4000 + 4000
      timer = setTimeout(() => {
        setRirurPos((prev) => {
          let next
          do { next = Math.floor(Math.random() * RIRUR_POSITIONS.length) }
          while (next === prev && RIRUR_POSITIONS.length > 1)
          return next
        })
        setRirurVisible(true)
      }, delay)
    }
    if (!rirurVisible) scheduleNextPop()
    return () => clearTimeout(timer)
  }, [rirurVisible])

  function handleRirurClick() {
    setRirurVisible(false)
    setTimeout(() => setRirurPos(null), 400)
  }

  // 팻말 마우스 & 터치 드래그 & 탄성 흔들림 물리 연산
  useEffect(() => {
    const el = titleRef.current
    if (!el) return

    let angle = 0
    let velocity = 0

    let isDragging = false
    let lastX = 0
    let lastTime = Date.now()

    let time = 0
    let frameId

    const springK = 0.15      // 복원력 계수
    const damping = 0.92      // 감쇠 계수

    const updatePhysics = () => {
      time += 16.67
      
      // 평상시 미세하게 둥실거리는 효과
      const floatAngle = Math.sin(time * 0.001) * 1.5

      if (!isDragging) {
        // 복원력과 댐핑 적용한 시계추 진자 물리
        const acceleration = -springK * angle
        velocity += acceleration
        velocity *= damping
        angle += velocity * 0.08
      }

      // 끈 상단 회전축 기준으로 transform 회전만 적용 (하늘에 끈이 고정되게 함)
      el.style.transform = `rotate(${angle + floatAngle}deg)`

      frameId = requestAnimationFrame(updatePhysics)
    }

    const handleStart = (clientX) => {
      isDragging = true
      lastX = clientX
      lastTime = Date.now()
      el.style.cursor = 'grabbing'
    }

    const handleMove = (clientX) => {
      if (!isDragging) return
      const now = Date.now()
      const dt = now - lastTime

      const deltaX = clientX - lastX
      
      // 마우스 X 변화량을 진자 각도 변화량으로 변환 (끈 길이가 450px이므로 각도 변화율 완화)
      angle += deltaX * 0.08

      // 회전각 한계선 제한
      if (angle > 20) angle = 20
      if (angle < -20) angle = -20

      if (dt > 0) {
        const targetVelocity = (deltaX / dt) * 4
        velocity = velocity * 0.3 + targetVelocity * 0.7
      }

      lastX = clientX
      lastTime = now
    }

    const handleEnd = () => {
      if (isDragging) {
        isDragging = false
        el.style.cursor = 'grab'
      }
    }

    const onMouseDown = (e) => {
      e.preventDefault()
      handleStart(e.clientX)
    }
    const onMouseMove = (e) => {
      handleMove(e.clientX)
    }
    const onMouseUp = () => {
      handleEnd()
    }

    const onTouchStart = (e) => {
      if (e.touches.length > 0) {
        handleStart(e.touches[0].clientX)
      }
    }
    const onTouchMove = (e) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX)
      }
    }
    const onTouchEnd = () => {
      handleEnd()
    }

    el.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('touchend', onTouchEnd)

    frameId = requestAnimationFrame(updatePhysics)
    el.style.cursor = 'grab'
    el.style.transformOrigin = '50% -450px' // 끈의 꼭대기(헤더 위쪽 고정점)를 회전축으로 설정하여 끈이 끊기지 않게 함

    return () => {
      cancelAnimationFrame(frameId)
      if (el) {
        el.removeEventListener('mousedown', onMouseDown)
        el.removeEventListener('touchstart', onTouchStart)
      }
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('touchend', onTouchEnd)
    }
  }, [])

  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 (밤하늘 배경 BACJ.png 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>파싱된 씬을 확인하고 수정하세요.</div>
          <h1 className={styles.headerTitle}>동화<br />씬 확인 · 수정</h1>
          <p className={styles.headerDesc}>
            다시 입력을 누르면 다시<br />
            입력 할 수 있어요!
          </p>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.titleFrame} ref={titleRef}>
            <img src={titleSvg} alt="씬 확인 타이틀 액자" className={styles.titleFrameImg} />
            <span className={styles.titleFrameText}>
              {storyTitle || '제목 없음'}
            </span>
          </div>
        </div>
      </header>

      {/* ── 책 컨테이너 (책 배경 복구) ── */}
      <div className={styles.bookContainer}>
        <img src={bookBg} alt="책 배경" className={styles.bookBackground} />

        {rirurPos !== null && (
          <img
            src={rirurChar}
            alt="리룰 캐릭터"
            className={styles.rirurCharacter}
            onClick={handleRirurClick}
            style={{
              top: RIRUR_POSITIONS[rirurPos].top || 'auto',
              bottom: RIRUR_POSITIONS[rirurPos].bottom || 'auto',
              left: RIRUR_POSITIONS[rirurPos].left || 'auto',
              right: RIRUR_POSITIONS[rirurPos].right || 'auto',
              transform: rirurVisible ? RIRUR_POSITIONS[rirurPos].activeTransform : RIRUR_POSITIONS[rirurPos].transform,
              transformOrigin: RIRUR_POSITIONS[rirurPos].origin,
              opacity: rirurVisible ? 1 : 0,
            }}
          />
        )}

        <div className={styles.bookContentOverlay}>
          <div className={styles.scrollArea}>
            {/* 로딩 */}
            {loading && <p className={styles.guide}>씬을 불러오는 중...</p>}

            {/* 스토리 없음 */}
            {!loading && scenes.length === 0 && (
              <div className={styles.empty}>
                <p>{error || '스토리를 먼저 입력해주세요.'}</p>
              </div>
            )}

            {/* 씬 목록 */}
            {!loading && scenes.length > 0 && (
              <>
                {/* 스토리 제목 박스 (피그마 목업 상단 중앙 둥근 텍스트 박스) */}
                <div className={styles.storyTitleBox}>
                  {storyTitle || '제목 없음'}
                </div>

                <ul className={styles.list}>
                  {scenes.map((scene) => (
                    <li key={scene.sceneId} className={styles.card}>
                      <span className={styles.scenePill}>Scene {String(scene.order).padStart(2, '0')}</span>
                      <div className={styles.itemsList}>
                        {scene.items.map((item, i) => (
                          <div key={i} className={styles.itemRow}>
                            {/* 감정 라벨 (있을 때만 노출) */}
                            {item.emotionLabel && (
                              <span className={styles.emotionTag}>
                                {item.emotionLabel}
                              </span>
                            )}
                            
                            {/* 역할 라벨 */}
                            <span className={styles.roleTag}>
                                {item.type === 'dialogue' ? item.speaker : '나레이션'}
                            </span>
                            
                            {/* 대사 내용 말풍선 */}
                            <div className={styles.textBubble}>
                              {item.text}
                            </div>
                          </div>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          {/* 하단 고정 버튼 (flex 레이아웃을 통해 겹치지 않고 하단 고정) */}
          <div className={styles.fixedActions}>
            <button className={styles.btnSecondary} onClick={() => navigate('/story-input')}>
              ← 다시 입력
            </button>
            <button className={styles.btnPrimary} onClick={() => navigate('/character')}>
              캐릭터 설정 →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
