import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './HomePage.module.css'
import { getStories } from '@/api/stories'

import homeLogoAnim from '@design/assets/figma-icons/Home/Home_logo_anim.svg'
import homeBook from '@design/assets/figma-icons/Home/Home_book.svg'

export default function HomePage() {
  const navigate = useNavigate()
  const logoRef = useRef(null)
  const [stories, setStories] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    getStories()
      .then((list) => {
        setStories(list ?? [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const el = logoRef.current
    if (!el) return

    // 좌우 흔들림 (X축) 변수
    let angle = 0
    let velocity = 0

    // 위아래 탄성 (Y축) 변수
    // 인트로 연출을 위해 초기 Y 오프셋을 -250px(화면 위쪽 뷰포트 바깥)로 설정
    let yOffset = -250
    let yVelocity = 0

    let isDragging = false
    let isIntro = true // 인트로 낙하 연출 중인지 여부
    let lastX = 0
    let lastY = 0
    let lastTime = Date.now()

    // 둥둥 뜨는 효과용 시간 누적 변수
    let time = 0
    let frameId

    // 물리 상수 정의
    const springK = 0.16     // X축 좌우 복원력 계수
    const damping = 0.91      // X축 좌우 감쇠 계수

    // 인트로 및 수직 탄성에 쓰이는 물리상수
    const ySpringK = 0.18    // Y축 복원 스프링 (살짝 더 쫀득하게 복원되도록 0.18 설정)
    const yDamping = 0.88     // Y축 복원 감쇠력

    const updatePhysics = () => {
      time += 16.67 // 약 60fps 흐름 모사

      // 둥둥 뜨는 효과 (더 크게 움직이며 더 느리게 둥실거리도록 조정: 진폭 8px, 속도 약 2배 감축)
      // 인트로 낙하 중에는 둥실거림을 적용하지 않거나 서서히 섞어줌
      const floatY = isIntro ? 0 : Math.sin(time * 0.0012) * 8

      if (isIntro) {
        // 인트로 낙하 연출: 중력 스프링 공식으로 위에서 뚝 떨어져 바운싱 안착 (갱신 비율을 0.04로 낮춰 2배 느리고 부드럽게)
        const yAcceleration = -ySpringK * yOffset
        yVelocity += yAcceleration
        yVelocity *= yDamping
        yOffset += yVelocity * 0.04

        // Y축 바운스 움직임이 충분히 잦아들면 인트로 종료 후 기본 상태 전환
        if (Math.abs(yOffset) < 0.5 && Math.abs(yVelocity) < 0.05) {
          yOffset = 0
          yVelocity = 0
          isIntro = false
        }
      } else if (!isDragging) {
        // 1. X축 회전 물리 연산
        const acceleration = -springK * angle
        velocity += acceleration
        velocity *= damping
        angle += velocity * 0.08

        // 2. Y축 탄성 물리 연산 (드래그 해제 후 수직 튕김)
        const yAcceleration = -ySpringK * yOffset
        yVelocity += yAcceleration
        yVelocity *= yDamping
        yOffset += yVelocity * 0.08
      } else {
        yVelocity = 0
      }

      // 수치 안정화
      if (!isDragging && !isIntro) {
        if (Math.abs(angle) < 0.01 && Math.abs(velocity) < 0.001) angle = 0
        if (Math.abs(yOffset) < 0.01 && Math.abs(yVelocity) < 0.001) yOffset = 0
      }

      // 회전(rotate) 및 위아래 오프셋(translateY) 최종 렌더링 매핑
      el.style.transform = `translateY(${floatY + yOffset}px) rotate(${angle}deg)`

      frameId = requestAnimationFrame(updatePhysics)
    }

    const handleMouseDown = (e) => {
      if (isIntro) return // 인트로 동작 중에는 드래그 인터랙션 차단
      e.preventDefault()
      isDragging = true
      lastX = e.clientX
      lastY = e.clientY
      lastTime = Date.now()
      el.style.cursor = 'grabbing'
    }

    const handleMouseMove = (e) => {
      if (isIntro) return // 인트로 동작 중에는 오버 효과 차단
      const now = Date.now()
      const dt = now - lastTime

      if (isDragging) {
        // X축 드래그 (회전)
        const deltaX = e.clientX - lastX
        angle += deltaX * 0.07

        // Y축 드래그 (세로 늘어남)
        const deltaY = e.clientY - lastY
        yOffset += deltaY * 0.35

        // 회전 각도 및 수직 오프셋 상하한선 타이트하게 제한
        if (angle > 18) angle = 18
        if (angle < -18) angle = -18

        if (yOffset > 25) yOffset = 25
        if (yOffset < -10) yOffset = -10

        if (dt > 0) {
          // 릴리즈 시 부드러운 평활 필터링
          const targetVelocity = (deltaX / dt) * 3.5
          velocity = velocity * 0.4 + targetVelocity * 0.6

          const targetYVelocity = (deltaY / dt) * 5
          yVelocity = yVelocity * 0.4 + targetYVelocity * 0.6
        }

        lastX = e.clientX
        lastY = e.clientY
        lastTime = now
      } else {
        // 마우스 호버 살랑임 효과 (X/Y축 대칭)
        const deltaX = e.clientX - lastX
        const deltaY = e.clientY - lastY

        if (Math.abs(deltaX) > 2) {
          velocity += deltaX * 0.005
        }
        if (Math.abs(deltaY) > 2) {
          yVelocity += deltaY * 0.015
        }

        lastX = e.clientX
        lastY = e.clientY
      }
    }

    const handleMouseUp = () => {
      if (isDragging) {
        isDragging = false
        el.style.cursor = 'grab'
      }
    }

    const handleMouseLeaveWindow = () => {
      if (isDragging) {
        isDragging = false
        el.style.cursor = 'grab'
      }
    }

    el.addEventListener('mousedown', handleMouseDown)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('mouseleave', handleMouseLeaveWindow)

    frameId = requestAnimationFrame(updatePhysics)

    // 초기 마우스 상태 및 회전축 정의
    el.style.cursor = 'grab'
    el.style.transformOrigin = '50% 0%'

    return () => {
      cancelAnimationFrame(frameId)
      if (el) {
        el.removeEventListener('mousedown', handleMouseDown)
      }
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('mouseleave', handleMouseLeaveWindow)
    }
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.centerSection}>
        <img
          ref={logoRef}
          src={homeLogoAnim}
          alt="몽실책방 타이틀 보드"
          className={styles.titleLogo}
        />
        <p className={styles.sub}>스토리를 입력하면 동화 영상이 완성돼요.</p>
        <button className={styles.cta} onClick={() => navigate('/voice-input')}>
          <span className={styles.starIcon}>✨</span> 새 프로젝트 시작
        </button>
      </div>

      {loading ? (
        <div className={styles.loading}>불러오는 중…</div>
      ) : stories.length === 0 ? (
        <section className={styles.emptySection}>
          <div className={styles.emptyCard}>
            <img src={homeBook} alt="빈 책장" className={styles.bookImage} />
            <h3 className={styles.emptyTitle}>책장이 비었네요.</h3>
            <p className={styles.emptySub}>새 프로젝트를 시작해 동화 영상을 만들어보세요!</p>
          </div>
        </section>
      ) : (
        <section className={styles.bookshelfSection}>
          <div className={styles.bookshelfContainer}>
            <h2 className={styles.bookshelfTitle}>나의 책방</h2>

            <div className={styles.bookshelfRow}>
              {stories.length > 5 && (
                <button 
                  type="button" 
                  className={`${styles.navBtn} ${styles.leftBtn}`}
                  onClick={() => setCurrentIndex((prev) => Math.max(prev - 1, 0))}
                  disabled={currentIndex === 0}
                  aria-label="이전 책"
                >
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor" 
                    strokeWidth="3" 
                    style={{ width: '14px', height: '14px', display: 'block' }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                  </svg>
                </button>
              )}
              
              <div className={styles.bookshelfViewport}>
                <div 
                  className={styles.bookshelfTrack}
                  style={{
                    transform: `translateX(-${currentIndex * 150}px)`
                  }}
                >
                  {stories.map((story, index) => {
                    // 책 표지 파스텔 톤 순환
                    const coverColors = [
                      'linear-gradient(135deg, #FFDEE9, #E9D5FF)', // 파스텔 핑크 + 라벤더
                      'linear-gradient(135deg, #E2D4F8, #ACE0F9)', // 라벤더 + 파스텔 하늘
                      'linear-gradient(135deg, #E0F2FE, #BAE6FD)', // 파스텔 하늘
                      'linear-gradient(135deg, #FFE4E6, #FBCFE8)', // 파스텔 핑크
                      'linear-gradient(135deg, #DDD6FE, #F3E8FF)', // 라벤더
                    ]
                    const bg = coverColors[index % coverColors.length]
                    return (
                      <div 
                        key={story.storyId} 
                        className={styles.bookCard}
                        onClick={() => navigate(`/scene-check?storyId=${story.storyId}`)}
                        title={`${story.title} 이어서 편집하기`}
                      >
                        <div className={styles.bookCover} style={{ background: bg }}>
                          <div className={styles.bookSpine} />
                          <div className={styles.bookTitle}>{story.title || '제목 없음'}</div>
                          <div className={styles.bookAuthor}>몽실 작가</div>
                        </div>
                        <div className={styles.bookInfo}>
                          <h4 className={styles.bookName}>{story.title || '제목 없음'}</h4>
                          <span className={styles.bookBtn}>이어서 만들기 →</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
              
              {stories.length > 5 && (
                <button 
                  type="button" 
                  className={`${styles.navBtn} ${styles.rightBtn}`}
                  onClick={() => setCurrentIndex((prev) => Math.min(prev + 1, stories.length - 5))}
                  disabled={currentIndex >= stories.length - 5}
                  aria-label="다음 책"
                >
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor" 
                    strokeWidth="3" 
                    style={{ width: '14px', height: '14px', display: 'block' }}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
