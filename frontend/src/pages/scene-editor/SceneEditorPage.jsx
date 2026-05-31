import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStories } from '@/api/stories'
import { getBackgrounds, assignBackgroundToScene } from '@/api/backgrounds'
import { getApiErrorMessage } from '@/utils/apiError'
import styles from './SceneEditorPage.module.css'

// 씬 편집(skeleton). 현재는 "씬 ↔ 배경 연결"만 실제 동작한다.
// (배경 라이브러리 생성/저장은 배경 페이지 담당, 씬에 배정은 여기 담당)
// 합성 미리보기 / 캐릭터 배정은 추후.
function sceneText(scene) {
  const items = scene.items ?? []
  const narration = items.find((i) => i.type === 'narration')
  return (narration ?? items[0])?.text ?? '(내용 없음)'
}

export default function SceneEditorPage() {
  const navigate = useNavigate()

  const [stories, setStories] = useState([])
  const [backgrounds, setBackgrounds] = useState([])
  const [storyId, setStoryId] = useState('')
  const [sceneId, setSceneId] = useState('')
  const [pickedBackgroundId, setPickedBackgroundId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    Promise.all([getStories(), getBackgrounds()])
      .then(([storyList, bgList]) => {
        setStories(storyList)
        setBackgrounds(bgList)
        setLoadError('')
      })
      .catch((e) => {
        // 실패를 "스토리/배경 없음"으로 숨기지 않고 에러로 표시한다.
        setLoadError(`데이터를 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [])

  const selectedStory = stories.find((s) => s.storyId === storyId)
  const scenes = selectedStory?.scenes ?? []
  const selectedScene = scenes.find((sc) => sc.sceneId === sceneId)

  function handleStoryChange(value) {
    setStoryId(value)
    setSceneId('')
    setMessage('')
    setError('')
  }

  async function handleConnect() {
    if (!storyId || !sceneId || !pickedBackgroundId) return
    setMessage('')
    setError('')
    try {
      await assignBackgroundToScene(sceneId, { storyId, backgroundId: pickedBackgroundId })
      // 갱신: 스토리 다시 불러와 scene.backgroundId 반영
      const list = await getStories()
      setStories(list)
      setMessage('배경이 씬에 연결되었습니다.')
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  return (
    <div className={styles.page}>
      <h1>씬 편집</h1>
      <p className={styles.guide}>씬을 선택해 배경과 캐릭터를 설정하세요.</p>
      {loadError && <p className={styles.errorText}>{loadError}</p>}

      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHead}>
            스토리
            <select
              className={styles.select}
              value={storyId}
              onChange={(e) => handleStoryChange(e.target.value)}
            >
              <option value="">스토리 선택</option>
              {stories.map((s) => (
                <option key={s.storyId} value={s.storyId}>{s.title}</option>
              ))}
            </select>
          </div>

          {!storyId ? (
            <p className={`${styles.muted} ${styles.pad}`}>스토리를 선택하세요.</p>
          ) : scenes.length === 0 ? (
            <p className={`${styles.muted} ${styles.pad}`}>씬이 없습니다.</p>
          ) : (
            <ul className={styles.sceneList}>
              {scenes.map((sc) => (
                <li
                  key={sc.sceneId}
                  className={`${styles.sceneItem} ${sc.sceneId === sceneId ? styles.sceneItemActive : ''}`}
                  onClick={() => { setSceneId(sc.sceneId); setMessage(''); setError('') }}
                >
                  <span className={styles.sceneOrder}>씬 {sc.order}</span>
                  <p className={styles.sceneText}>{sceneText(sc)}</p>
                  {sc.backgroundId && (
                    <span className={styles.bgBadge}>배경: {sc.backgroundId}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </aside>

        <main className={styles.canvas}>
          {!selectedScene ? (
            <div className={styles.placeholder}>씬을 선택하면 편집 영역이 표시돼요.</div>
          ) : (
            <>
              <div className={styles.placeholder}>
                씬 {selectedScene.order} — 합성 미리보기 (준비 중)
              </div>
              <div className={styles.panel}>
                <div className={styles.bgPanel}>
                  <span className={styles.panelLabel}>배경</span>
                  <span className={styles.muted}>
                    현재: {selectedScene.backgroundId ?? '연결 안 됨'}
                  </span>
                  {backgrounds.length === 0 ? (
                    <span className={styles.muted}>
                      저장된 배경이 없습니다.{' '}
                      <button className={styles.link} onClick={() => navigate('/background')}>
                        배경 만들기
                      </button>
                    </span>
                  ) : (
                    <>
                      <select
                        className={styles.select}
                        value={pickedBackgroundId}
                        onChange={(e) => setPickedBackgroundId(e.target.value)}
                      >
                        <option value="">라이브러리에서 배경 선택</option>
                        {backgrounds.map((b) => (
                          <option key={b.backgroundId} value={b.backgroundId}>{b.name}</option>
                        ))}
                      </select>
                      <button
                        className={styles.panelBtn}
                        onClick={handleConnect}
                        disabled={!pickedBackgroundId}
                      >
                        이 씬에 배경 연결
                      </button>
                    </>
                  )}
                </div>

                <div className={styles.panelItem}>
                  <span className={styles.panelLabel}>캐릭터</span>
                  <button className={styles.panelBtn}>캐릭터 합성</button>
                </div>
              </div>
              {message && <p className={styles.message}>{message}</p>}
              {error && <p className={styles.errorText}>{error}</p>}
            </>
          )}
        </main>
      </div>

      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/background')}>
          ← 배경
        </button>
        <button className={styles.btn} onClick={() => navigate('/timeline')}>
          타임라인 →
        </button>
      </div>
    </div>
  )
}
