import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStories } from '@/api/stories'
import { getBackgrounds, assignBackgroundToScene } from '@/api/backgrounds'
import {
  getCharacters,
  assignCharacterToScene,
  removeCharacterFromScene,
} from '@/api/characters'
import { updateSceneSubtitles, setSceneCharacterPose } from '@/api/scenes'
import { getApiErrorMessage } from '@/utils/apiError'
import useCharacterStore from '@/store/useCharacterStore'
import useStoryStore from '@/store/useStoryStore'
import SceneStage from '@/components/scene-editor/SceneStage'
import SubtitleCuePanel from '@/components/scene-editor/SubtitleCuePanel'
import SceneCharacterPanel from '@/components/scene-editor/SceneCharacterPanel'
import styles from './SceneEditorPage.module.css'

import useSwingingSignboard from '@/hooks/useSwingingSignboard'

// 디자인 자산 임포트
import headerBg from '@design/assets/figma-icons/Base/Base_Scene_edit.png'
import characterSceneEditSvg from '@design/assets/figma-icons/character/character_Scene-edit.svg'
import navBackgroundIcon from '@design/assets/figma-icons/Nav/nav_background.svg'
import navSceneEditorIcon from '@design/assets/figma-icons/Nav/nav_scene_editor.svg'

// 자막 배경(씬 단위) 옵션 ↔ style.backgroundColor 매핑. 백엔드와 동일(불투명도 0.3 고정).
const SUBTITLE_BG_TO_CSS = {
  black: 'rgba(0, 0, 0, 0.3)',
  white: 'rgba(255, 255, 255, 0.3)',
}
// style.backgroundColor → 옵션값(none/black/white) 역매핑. 없으면 none.
function bgOptionFromStyle(bgColor) {
  if (!bgColor) return 'none'
  return bgColor.replace(/\s/g, '').startsWith('rgba(255') ? 'white' : 'black'
}

function sceneText(scene) {
  const items = scene.items ?? []
  const narration = items.find((i) => i.type === 'narration')
  return (narration ?? items[0])?.text ?? '(내용 없음)'
}

export default function SceneEditorPage() {
  const navigate = useNavigate()
  const { characters, setCharacters } = useCharacterStore()

  const globalStoryId = useStoryStore((s) => s.storyId)
  const storyTitle = useStoryStore((s) => s.storyTitle)
  const { titleRef, frameHeight } = useSwingingSignboard(1129 / 1470)
  const setGlobalStoryId = useStoryStore((s) => s.setStoryId)
  const setGlobalStoryTitle = useStoryStore((s) => s.setStoryTitle)
  const setGlobalScenes = useStoryStore((s) => s.setScenes)

  const [stories, setStories] = useState([])
  const [backgrounds, setBackgrounds] = useState([])
  const [storyId, setStoryId] = useState('')
  const [sceneId, setSceneId] = useState('')
  const [pickedBackgroundId, setPickedBackgroundId] = useState('')
  const [pickedCharacterId, setPickedCharacterId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [loadError, setLoadError] = useState('')
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | error
  const [selected, setSelected] = useState(null)
  const [editMode, setEditMode] = useState('character') // 'character' | 'subtitle'
  const [activeCue, setActiveCue] = useState(null)
  const [poseForCharacterId, setPoseForCharacterId] = useState(null)
  const [showSceneList, setShowSceneList] = useState(false)

  useEffect(() => {
    Promise.all([getStories(), getBackgrounds(), getCharacters()])
      .then(([storyList, bgList, charList]) => {
        setStories(Array.isArray(storyList) ? storyList : [])
        setBackgrounds(Array.isArray(bgList) ? bgList : [])
        setCharacters(charList)
        setLoadError('')
      })
      .catch((e) => {
        setLoadError(`데이터를 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [setCharacters])

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (e.key === 'Escape') {
        setShowSceneList((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    if (storyId || stories.length === 0) return
    const useGlobal = globalStoryId && stories.some((s) => s.storyId === globalStoryId)
    const target = useGlobal ? globalStoryId : stories[stories.length - 1].storyId
    handleStoryChange(target)
  }, [stories, globalStoryId, storyId])

  const selectedStory = stories.find((s) => s.storyId === storyId)
  const scenes = selectedStory?.scenes ?? []
  const selectedScene = scenes.find((sc) => sc.sceneId === sceneId)

  const sceneBackgroundUrl = backgrounds.find(
    (b) => b.backgroundId === selectedScene?.backgroundId,
  )?.imageUrl

  // 이미지 필터를 빼서 이미지 미지정 상태에서도 이름 뱃지 점선 플레이스홀더가 뜨도록 함!
  const sceneCharacters = (selectedScene?.characters ?? [])
    .map((ch) => {
      const dbChar = characters.find((c) => c.characterId === ch.characterId)
      return {
        ...ch,
        name: dbChar?.name || '캐릭터',
        imageUrl: ch.imageUrl ?? dbChar?.imageUrl,
      }
    })

  const sceneTextOverlays = selectedScene?.textOverlays ?? []
  const cueSlots = Array.from({ length: sceneTextOverlays.length }, (_, i) => i + 1)
  const firstCue = sceneTextOverlays.length
    ? Math.min(...sceneTextOverlays.map((o) => o.cueOrder))
    : null

  function syncStoryToGlobal(sid) {
    const story = stories.find((s) => s.storyId === sid)
    if (!story) return
    setGlobalStoryId(sid)
    setGlobalStoryTitle(story.title ?? '')
    setGlobalScenes(story.scenes ?? [])
  }

  function handleStoryChange(value) {
    setStoryId(value)
    if (value) syncStoryToGlobal(value)
    setSceneId('')
    setPickedBackgroundId('')
    setPickedCharacterId('')
    setMessage('')
    setError('')
    setSelected(null)
    setEditMode('character')
    setActiveCue(null)
    setPoseForCharacterId(null)
  }

  function handleSceneSelect(sc) {
    setSceneId(sc.sceneId)
    setPickedBackgroundId(sc.backgroundId ?? '')
    setPickedCharacterId('')
    setMessage('')
    setError('')
    setSelected(null)
    setEditMode('character')
    setActiveCue(null)
    setPoseForCharacterId(null)
    // 3단 레이아웃 개편: 씬 선택 시 목록을 닫지 않고 계속 열어두어 브라우징을 원활하게 함
  }

  function enterCharacterMode() {
    setEditMode('character')
    setActiveCue(null)
    setSelected(null)
  }

  function enterSubtitleCue(cueOrder) {
    setEditMode('subtitle')
    setActiveCue(cueOrder)
  }

  async function handleConnect() {
    if (!storyId || !sceneId || !pickedBackgroundId) return
    setMessage('')
    setError('')
    try {
      await assignBackgroundToScene(sceneId, { storyId, backgroundId: pickedBackgroundId })
      const list = await getStories()
      setStories(list)
      setMessage('배경이 씬에 연결되었습니다.')
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  async function handleCharacterConnect() {
    if (!storyId || !sceneId || !pickedCharacterId) return
    setMessage('')
    setError('')
    try {
      await assignCharacterToScene(sceneId, { storyId, characterId: pickedCharacterId })
      const list = await getStories()
      setStories(list)
      setPickedCharacterId('')
      setMessage('캐릭터가 씬에 추가되었습니다.')
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  function applyLayoutToStories(charId, lay) {
    setStories((prev) =>
      prev.map((s) =>
        s.storyId !== storyId
          ? s
          : {
               ...s,
               scenes: s.scenes.map((sc) =>
                 sc.sceneId !== sceneId
                   ? sc
                   : {
                       ...sc,
                       characters: (sc.characters ?? []).map((ch) =>
                         ch.characterId === charId ? { ...ch, layout: lay } : ch,
                       ),
                     },
               ),
             },
      ),
    )
  }

  async function handleLayoutChange(characterId, layout) {
    const prevLayout = stories
      .find((s) => s.storyId === storyId)
      ?.scenes.find((sc) => sc.sceneId === sceneId)
      ?.characters?.find((ch) => ch.characterId === characterId)?.layout

    applyLayoutToStories(characterId, layout)
    setSaveStatus('saving')
    try {
      await assignCharacterToScene(sceneId, { storyId, characterId, layout })
      setSaveStatus('saved')
    } catch (e) {
      applyLayoutToStories(characterId, prevLayout)
      setSaveStatus('error')
      setError(getApiErrorMessage(e))
    }
  }

  const saveSeq = useRef(0)

  function applyOverlaysToStories(overlays) {
    setStories((prev) =>
      prev.map((s) =>
        s.storyId !== storyId
          ? s
          : {
               ...s,
               scenes: s.scenes.map((sc) =>
                 sc.sceneId !== sceneId ? sc : { ...sc, textOverlays: overlays },
               ),
             },
      ),
    )
  }

  async function persistOverlays(nextOverlays) {
    const prevOverlays = sceneTextOverlays
    applyOverlaysToStories(nextOverlays)
    setSaveStatus('saving')
    setError('')
    const seq = ++saveSeq.current
    try {
      const res = await updateSceneSubtitles(sceneId, {
        storyId,
        sceneTextColor: nextOverlays.find((o) => o.style?.color)?.style?.color ?? null,
        subtitleBackground: bgOptionFromStyle(
          nextOverlays.find((o) => o.style?.backgroundColor)?.style?.backgroundColor,
        ),
        overlays: nextOverlays.map((o) => ({
          itemIndex: o.sourceItemIndex,
          cueOrder: o.cueOrder,
          layout: o.layout,
        })),
      })
      if (seq !== saveSeq.current) return
      if (res?.textOverlays) applyOverlaysToStories(res.textOverlays)
      setSaveStatus('saved')
    } catch (e) {
      if (seq !== saveSeq.current) return
      applyOverlaysToStories(prevOverlays)
      setSaveStatus('error')
      setError(getApiErrorMessage(e))
    }
  }

  function handleTextOverlayLayoutChange(overlayId, layout) {
    const next = sceneTextOverlays.map((o) => (o.textOverlayId === overlayId ? { ...o, layout } : o))
    persistOverlays(next)
  }

  function handleSetCueGroup(overlayId, cueOrder) {
    const ov = sceneTextOverlays.find((o) => o.textOverlayId === overlayId)
    if (!ov || ov.cueOrder === cueOrder) return
    const next = sceneTextOverlays.map((o) => (o.textOverlayId === overlayId ? { ...o, cueOrder } : o))
    persistOverlays(next)
    enterSubtitleCue(cueOrder)
    setSelected({ kind: 'text', id: overlayId })
  }

  function handleSetCueAlign(cueOrder, align) {
    const next = sceneTextOverlays.map((o) =>
      o.cueOrder === cueOrder ? { ...o, layout: { ...o.layout, align } } : o,
    )
    persistOverlays(next)
  }

  function handleSetSceneColor(color) {
    const next = sceneTextOverlays.map((o) => ({ ...o, style: { ...(o.style || {}), color } }))
    persistOverlays(next)
  }

  // 씬 단위 자막 배경(none/black/white). none 이면 backgroundColor 제거(투명).
  function handleSetSceneBackground(option) {
    const css = SUBTITLE_BG_TO_CSS[option]
    const next = sceneTextOverlays.map((o) => {
      const style = { ...(o.style || {}) }
      if (css) style.backgroundColor = css
      else delete style.backgroundColor
      return { ...o, style }
    })
    persistOverlays(next)
  }

  async function handleApplyPose(characterId, poseId) {
    setError('')
    try {
      await setSceneCharacterPose(sceneId, characterId, { storyId, poseId })
      setStories(await getStories())
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  async function handleCharacterRemove(characterId) {
    setMessage('')
    setError('')
    if (poseForCharacterId === characterId) setPoseForCharacterId(null)
    try {
      await removeCharacterFromScene(sceneId, characterId, storyId)
      const list = await getStories()
      setStories(list)
      setMessage('캐릭터를 씬에서 제거했습니다.')
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  return (
    <div className={styles.page}>
      {/* ── 상단 헤더 영역 (밤하늘 배경 적용) ── */}
      <header className={styles.header} style={{ backgroundImage: `url(${headerBg})` }}>
        <div className={styles.headerLeft}>
          <div className={styles.headerSubTitle}>씬을 선택해 배경과 캐릭터를 설정하세요.</div>
          <h1 className={styles.headerTitle}>씬 편집</h1>
          <button
            type="button"
            className={styles.toggleListBtn}
            onClick={() => setShowSceneList(!showSceneList)}
            aria-expanded={showSceneList}
          >
            🎬 씬 목록 {showSceneList ? '접기' : '펼치기'}
          </button>
          <p className={styles.headerDesc}>
            자막과 cue를 배치해 이야기를 완성할 수 있어요. (단축키: Esc)
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
              src={characterSceneEditSvg} 
              alt="씬 편집 타이틀 액자" 
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

      {loadError && <p className={styles.errorText}>{loadError}</p>}

      {/* ── 편집 레이아웃 컨테이너 ── */}
      <div className={styles.editorContainer}>
        <div className={styles.contentLayout}>
          {/* 1. 좌측 씬 목록 사이드바 */}
          {showSceneList && (
            <div className={styles.leftSidebar}>
              <div className={styles.sidebarHead}>
                <span className={styles.sidebarLabel}>스토리</span>
                <div className={styles.selectWrapper}>
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
              </div>

              <div className={styles.listHeader}>씬 목록</div>

              <div className={styles.scrollArea}>
                {!storyId ? (
                  <p className={styles.muted}>스토리를 선택하세요.</p>
                ) : scenes.length === 0 ? (
                  <p className={styles.muted}>씬이 없습니다.</p>
                ) : (
                  <ul className={styles.sceneList}>
                    {scenes.map((sc) => {
                      const isSelected = sc.sceneId === sceneId
                      return (
                        <li
                          key={sc.sceneId}
                          className={`${styles.sceneCard} ${isSelected ? styles.sceneCardActive : ''}`}
                          onClick={() => handleSceneSelect(sc)}
                        >
                          <span className={styles.sceneCardPill}>씬 {sc.order}</span>
                          <p className={styles.sceneCardText}>{sceneText(sc)}</p>
                          <div className={styles.sceneCardTags}>
                            <span className={styles.sceneCardTagBg}>
                              배경: {backgrounds.find((b) => b.backgroundId === sc.backgroundId)?.name || '없음'}
                            </span>
                            <span className={styles.sceneCardTagChar}>
                              캐릭터: {sc.characters?.length || 0}명
                            </span>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* 2. 중앙 캔버스 영역 */}
          <div className={styles.centerStage}>
            {!selectedScene ? (
              <div className={styles.placeholder}>
                <img
                  src={navSceneEditorIcon}
                  alt="씬 편집 마스코트"
                  className={styles.placeholderIcon}
                />
                <h3 className={styles.placeholderTitle}>편집할 씬을 선택해주세요</h3>
                <p className={styles.placeholderDesc}>
                  좌측 목록에서 편집할 씬을 클릭하거나,<br />
                  아래 버튼을 눌러 목록을 펼치세요.
                </p>
                <button
                  type="button"
                  className={styles.panelBtn}
                  onClick={() => setShowSceneList(true)}
                  style={{ width: 'auto', padding: '10px 24px' }}
                >
                  🎬 씬 목록 열기
                </button>
              </div>
            ) : (
              <>
                <div className={styles.canvasContainer}>
                  <SceneStage
                    backgroundUrl={sceneBackgroundUrl}
                    characters={sceneCharacters}
                    textOverlays={sceneTextOverlays}
                    selected={selected}
                    onSelect={setSelected}
                    onCharacterLayoutChange={handleLayoutChange}
                    onTextOverlayLayoutChange={handleTextOverlayLayoutChange}
                    editMode={editMode}
                    activeCue={activeCue}
                  />
                </div>

                {/* 자동 저장 상태바 */}
                <p className={styles.saveStatusMuted} aria-live="polite">
                  {saveStatus === 'saving' && '위치 저장 중…'}
                  {saveStatus === 'saved' && '✓ 자동 저장됨'}
                  {saveStatus === 'error' && '⚠ 저장 실패 — 잠시 후 다시 시도해 주세요'}
                  {saveStatus === 'idle' &&
                    (editMode === 'character'
                      ? '캐릭터를 드래그·크기조절·회전하면 자동 저장됩니다 (별도 저장 버튼 없음)'
                      : '자막을 드래그·크기조절·회전하면 자동 저장됩니다. 캐릭터는 선택 잠금')}
                </p>
              </>
            )}
          </div>

          {/* 3. 우측 속성 검사기 영역 */}
          {selectedScene && (
            <div className={styles.rightInspector}>
              {/* 3-1. 배경 설정 카드 */}
              <div className={styles.inspectorCard}>
                <div className={styles.panelHeader}>
                  <img src={navBackgroundIcon} alt="" className={styles.panelIcon} />
                  <span className={styles.panelLabel}>배경 설정</span>
                </div>
                <div className={styles.panelBody}>
                  <p className={styles.panelInfoText}>
                    현재 배경: <span className={styles.highlightText}>{backgrounds.find((b) => b.backgroundId === selectedScene.backgroundId)?.name || '연결 안 됨'}</span>
                  </p>
                  {backgrounds.length === 0 ? (
                    <span className={styles.muted}>
                      저장된 배경이 없습니다.{' '}
                      <button className={styles.link} onClick={() => navigate('/background')}>
                        배경 만들기
                      </button>
                    </span>
                  ) : (
                    <div className={styles.dropdownWithBtn}>
                      <select
                        className={styles.select}
                        value={pickedBackgroundId}
                        onChange={(e) => setPickedBackgroundId(e.target.value)}
                      >
                        <option value="">배경 선택</option>
                        {backgrounds.map((b) => (
                          <option key={b.backgroundId} value={b.backgroundId}>{b.name}</option>
                        ))}
                      </select>
                      <button
                        className={styles.panelBtn}
                        onClick={handleConnect}
                        disabled={!pickedBackgroundId}
                      >
                        이 씬에 연결
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* 3-2. 편집 모드 탭 */}
              <div className={styles.inspectorTabs}>
                <button
                  className={`${styles.tabBtn} ${editMode === 'character' ? styles.tabBtnActive : ''}`}
                  onClick={enterCharacterMode}
                >
                  캐릭터 배치
                </button>
                <button
                  className={`${styles.tabBtn} ${editMode === 'subtitle' ? styles.tabBtnActive : ''}`}
                  onClick={() => enterSubtitleCue(activeCue ?? firstCue)}
                  disabled={sceneTextOverlays.length === 0}
                >
                  자막 배치
                </button>
              </div>

              {/* 3-3. 모드별 상세 속성창 */}
              <div className={styles.inspectorContent}>
                {editMode === 'character' ? (
                  <SceneCharacterPanel
                    sceneCharacters={selectedScene.characters}
                    characters={characters}
                    pickedCharacterId={pickedCharacterId}
                    onPickedCharacterChange={setPickedCharacterId}
                    onConnect={handleCharacterConnect}
                    onRemove={handleCharacterRemove}
                    poseForCharacterId={poseForCharacterId}
                    onTogglePose={(id) => setPoseForCharacterId(poseForCharacterId === id ? null : id)}
                    onApplyPose={handleApplyPose}
                    onGoCreateCharacter={() => navigate('/character')}
                  />
                ) : (
                  <SubtitleCuePanel
                    sceneOrder={selectedScene.order}
                    overlays={sceneTextOverlays}
                    cueSlots={cueSlots}
                    selected={selected}
                    editMode={editMode}
                    activeCue={activeCue}
                    onEnterCue={enterSubtitleCue}
                    onSelectOverlay={(id) => setSelected({ kind: 'text', id })}
                    onSetCueGroup={handleSetCueGroup}
                    onSetCueAlign={handleSetCueAlign}
                    sceneTextColor={sceneTextOverlays.find((o) => o.style?.color)?.style?.color ?? null}
                    onSetSceneColor={handleSetSceneColor}
                    subtitleBackground={bgOptionFromStyle(
                      sceneTextOverlays.find((o) => o.style?.backgroundColor)?.style?.backgroundColor,
                    )}
                    onSetSceneBackground={handleSetSceneBackground}
                  />
                )}
              </div>

              {message && <p className={styles.message}>{message}</p>}
              {error && <p className={styles.errorText}>{error}</p>}
            </div>
          )}
        </div>
      </div>

      {/* ── 책 외부 하단 네비게이션 ── */}
      <div className={styles.actions}>
        <button className={styles.btnSecondary} onClick={() => navigate('/background')}>
          ← 이전 단계
        </button>
        <button
          className={styles.btn}
          onClick={() => {
            if (storyId && storyId !== globalStoryId) syncStoryToGlobal(storyId)
            navigate('/timeline')
          }}
        >
          타임라인 →
        </button>
      </div>
    </div>
  )
}
