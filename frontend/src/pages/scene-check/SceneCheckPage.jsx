import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useStoryStore from '@/store/useStoryStore'
import { getStory } from '@/api/stories'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from './SceneCheckPage.module.css'

import titleSvg from '@design/assets/figma-icons/Scene-_Check/title.svg'
import headerBg from '@design/assets/figma-icons/Scene-_Check/BACJ.png'



import useSwingingSignboard from '@/hooks/useSwingingSignboard'

export default function SceneCheckPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { scenes, storyId, storyTitle, setScenes, setStoryId, setStoryTitle } = useStoryStore()

  const effectiveStoryId = searchParams.get('storyId') || storyId
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { titleRef, frameHeight } = useSwingingSignboard(2533 / 2672)

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


  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 (밤하늘 배경 BACJ.png 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>파싱된 씬을 확인하고 수정하세요.</div>
          <h1 className={styles.headerTitle}>동화<br />씬 확인 · 수정</h1>
          <p className={styles.headerDesc}>
            이전 스토리 입력에서 작성한 스토리를 볼 수 있어요<br />
            만약 수정을 원한다면,<br />
            다시 입력을 누르면 다시 입력 할 수 있어요.
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
              src={titleSvg} 
              alt="씬 확인 타이틀 액자" 
              className={styles.titleFrameImg} 
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
            />
            <span 
              className={styles.titleFrameText}
              style={{
                position: 'absolute',
                top: '79%', /* 팻말 내 노란색/흰색 영역 정중앙 정렬 */
                left: '50%',
                transform: 'translate(-50%, -50%)'
              }}
            >
              {storyTitle || '제목 없음'}
            </span>
          </div>
        </div>
      </header>

      {/* ── 내용 컨테이너 ── */}
      <div className={styles.bookContainer}>



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
