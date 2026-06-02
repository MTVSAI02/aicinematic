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

  const { characters, setCharacters } = useCharacterStore()

  // 전역 store: 선택한 스토리를 /timeline·/render 가 같이 바라보도록 동기화한다.
  // (로컬 setStoryId 와 이름이 겹쳐 alias 로 가져온다)
  const globalStoryId = useStoryStore((s) => s.storyId)
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
  // 캐릭터 배치 자동 저장 상태 (저장 버튼이 없으므로 사용자에게 저장 여부를 보여준다)
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | error
  // 스테이지 선택 모델: 캐릭터/자막 공통. { kind: 'character' | 'text', id } | null
  const [selected, setSelected] = useState(null)
  // 편집 모드 분리: 'character'(기본) | 'subtitle'. activeCue = 자막 모드에서 편집 중인 cue 그룹.
  const [editMode, setEditMode] = useState('character')
  const [activeCue, setActiveCue] = useState(null)
  // 캐릭터 패널에서 포즈 생성 UI를 펼친 캐릭터(없으면 null). 스테이지/배치 로직과 독립.
  const [poseForCharacterId, setPoseForCharacterId] = useState(null)

  useEffect(() => {
    Promise.all([getStories(), getBackgrounds(), getCharacters()])
      .then(([storyList, bgList, charList]) => {
        setStories(Array.isArray(storyList) ? storyList : [])
        setBackgrounds(Array.isArray(bgList) ? bgList : [])
        setCharacters(charList)
        setLoadError('')
      })
      .catch((e) => {
        // 실패를 "스토리/배경 없음"으로 숨기지 않고 에러로 표시한다.
        setLoadError(`데이터를 불러오지 못했습니다. ${getApiErrorMessage(e)}`)
      })
  }, [setCharacters])

  // 진입/새로고침 후 초기 선택 시드: 로컬 storyId 가 비어 있을 때만.
  // 1순위 전역(persist) storyId 가 목록에 있으면 그걸, 없거나 비면 최신으로 fallback.
  // handleStoryChange 를 그대로 써서 로컬·전역·scenes 가 같은 story 로 정렬되게 한다(fallback 도 전역에 반영됨).
  useEffect(() => {
    if (storyId || stories.length === 0) return
    const useGlobal = globalStoryId && stories.some((s) => s.storyId === globalStoryId)
    const target = useGlobal ? globalStoryId : stories[stories.length - 1].storyId
    handleStoryChange(target)
    // handleStoryChange 는 매 렌더 새로 생성되는 클로저라 deps 에서 의도적으로 제외(아래 값들로 충분)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stories, globalStoryId, storyId])

  const selectedStory = stories.find((s) => s.storyId === storyId)
  const scenes = selectedStory?.scenes ?? []
  const selectedScene = scenes.find((sc) => sc.sceneId === sceneId)

  // 합성 미리보기용: 선택 씬의 배경 imageUrl + 연결 캐릭터(이미지 포함, 이미지 없는 건 제외)
  const sceneBackgroundUrl = backgrounds.find(
    (b) => b.backgroundId === selectedScene?.backgroundId,
  )?.imageUrl
  // 표시 이미지는 백엔드가 해석해 ch.imageUrl 로 내려준다(poseId 있으면 포즈, 없으면 원본).
  // 혹시 비어 있으면 store의 원본으로 보강.
  const sceneCharacters = (selectedScene?.characters ?? [])
    .map((ch) => ({
      ...ch,
      imageUrl: ch.imageUrl ?? characters.find((c) => c.characterId === ch.characterId)?.imageUrl,
    }))
    .filter((ch) => ch.imageUrl)
  // 자막: 백엔드가 items+설정으로 조립한 결과를 그대로 사용(단일 소스). 프론트는 렌더 + 변경만 전송.
  const sceneTextOverlays = selectedScene?.textOverlays ?? []
  // 배정 가능한 cue 슬롯(고정): 1..N (N = 자막 수). 기본은 각 줄이 자기 cue.
  const cueSlots = Array.from({ length: sceneTextOverlays.length }, (_, i) => i + 1)
  const firstCue = sceneTextOverlays.length
    ? Math.min(...sceneTextOverlays.map((o) => o.cueOrder))
    : null

  // 선택한 스토리를 전역 store(storyId/title/scenes)에 반영 → /timeline·/render 가 같은 스토리를 봄.
  function syncStoryToGlobal(sid) {
    const story = stories.find((s) => s.storyId === sid)
    if (!story) return
    setGlobalStoryId(sid)
    setGlobalStoryTitle(story.title ?? '')
    setGlobalScenes(story.scenes ?? [])
  }

  function handleStoryChange(value) {
    setStoryId(value)
    if (value) syncStoryToGlobal(value) // 선택 즉시 전역 반영(빈 선택은 무시)
    setSceneId('')
    // 스토리가 바뀌면 이전 씬에서 고른 선택값을 비운다(다른 씬에 잘못 연결 방지)
    setPickedBackgroundId('')
    setPickedCharacterId('')
    setMessage('')
    setError('')
    setSelected(null)
    setEditMode('character')
    setActiveCue(null)
    setPoseForCharacterId(null)
  }

  // 씬을 선택하면 배경은 현재 연결값으로 prefill, 캐릭터 추가폼은 비운다(다중이라 목록은 따로 표시).
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
  }

  // 모드 전환 헬퍼
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
      // 갱신: 스토리 다시 불러와 scene.backgroundId 반영
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
      const list = await getStories() // scene.characters 목록 갱신
      setStories(list)
      setPickedCharacterId('') // 추가 폼 초기화 (연달아 다른 캐릭터 추가 가능)
      setMessage('캐릭터가 씬에 추가되었습니다.')
    } catch (e) {
      setError(getApiErrorMessage(e))
    }
  }

  // 드래그/리사이즈 종료 시 호출: 화면 즉시 반영(스냅백 방지) + layout 저장
  // stories 상태에서 특정 캐릭터의 layout 만 교체 (optimistic 적용 / 실패 시 rollback 공용)
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
    // 실패 시 되돌릴 이전 layout 캡처
    const prevLayout = stories
      .find((s) => s.storyId === storyId)
      ?.scenes.find((sc) => sc.sceneId === sceneId)
      ?.characters?.find((ch) => ch.characterId === characterId)?.layout

    applyLayoutToStories(characterId, layout) // optimistic
    setSaveStatus('saving')
    try {
      await assignCharacterToScene(sceneId, { storyId, characterId, layout })
      setSaveStatus('saved')
    } catch (e) {
      applyLayoutToStories(characterId, prevLayout) // 저장 실패 → 이전 위치로 복구
      setSaveStatus('error')
      setError(getApiErrorMessage(e))
    }
  }

  // ── 자막 설정(cue 그룹 + 배치) 저장 ───────────────────────────
  // 자막은 백엔드가 단일 소스로 조립 → 프론트는 textOverlays 목록을 패치해 보낸다. 저장은 cueOrder/layout만.
  const saveSeq = useRef(0) // 빠른 연속 조작에서 최신 요청만 반영(stale 응답/rollback 방지)

  // 선택 씬의 textOverlays 목록만 교체 (optimistic / rollback / 서버 동기화 공용)
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

  // 패치된 자막 목록 전체 저장(cueOrder/layout만). 최신 요청만 반영, 실패 시 직전 목록으로 rollback.
  async function persistOverlays(nextOverlays) {
    const prevOverlays = sceneTextOverlays
    applyOverlaysToStories(nextOverlays) // optimistic
    setSaveStatus('saving')
    setError('')
    const seq = ++saveSeq.current
    try {
      const res = await updateSceneSubtitles(sceneId, {
        storyId,
        overlays: nextOverlays.map((o) => ({
          itemIndex: o.sourceItemIndex,
          cueOrder: o.cueOrder,
          layout: o.layout,
        })),
      })
      if (seq !== saveSeq.current) return // 더 최신 요청이 진행 중 → 이 응답 버림
      if (res?.textOverlays) applyOverlaysToStories(res.textOverlays) // 서버 기준 동기화
      setSaveStatus('saved')
    } catch (e) {
      if (seq !== saveSeq.current) return
      applyOverlaysToStories(prevOverlays) // 실패 → 직전 목록으로 복구
      setSaveStatus('error')
      setError(getApiErrorMessage(e))
    }
  }

  // 드래그/리사이즈/회전 종료 → 해당 자막 layout 갱신(cueOrder 유지)
  function handleTextOverlayLayoutChange(overlayId, layout) {
    const next = sceneTextOverlays.map((o) => (o.textOverlayId === overlayId ? { ...o, layout } : o))
    persistOverlays(next)
  }

  // 자막을 다른 cue 그룹에 묶기(cueOrder 변경, layout 유지). cue 번호 자체는 고정 슬롯.
  function handleSetCueGroup(overlayId, cueOrder) {
    const ov = sceneTextOverlays.find((o) => o.textOverlayId === overlayId)
    if (!ov || ov.cueOrder === cueOrder) return
    const next = sceneTextOverlays.map((o) => (o.textOverlayId === overlayId ? { ...o, cueOrder } : o))
    persistOverlays(next)
    enterSubtitleCue(cueOrder) // 옮긴 cue 로 따라가서 그 그룹을 편집 중으로
    setSelected({ kind: 'text', id: overlayId })
  }

  // 포즈 적용/해제(씬 단위). poseId=null이면 기본 이미지로. 표시 imageUrl은 story 응답이 해석해 주므로 stories만 갱신.
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
                  onClick={() => handleSceneSelect(sc)}
                >
                  <span className={styles.sceneOrder}>씬 {sc.order}</span>
                  <p className={styles.sceneText}>{sceneText(sc)}</p>
                  {sc.backgroundId && (
                    <span className={styles.bgBadge}>배경: {sc.backgroundId}</span>
                  )}
                  {sc.characters?.length > 0 && (
                    <span className={styles.bgBadge}>캐릭터 {sc.characters.length}명</span>
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
              {/* 편집 모드 토글 + 현재 상태 */}
              <div className={styles.modeBar}>
                <div className={styles.modeBtns}>
                  <button
                    className={`${styles.modeBtn} ${editMode === 'character' ? styles.modeBtnActive : ''}`}
                    onClick={enterCharacterMode}
                  >
                    캐릭터 배치
                  </button>
                  <button
                    className={`${styles.modeBtn} ${editMode === 'subtitle' ? styles.modeBtnActive : ''}`}
                    onClick={() => enterSubtitleCue(activeCue ?? firstCue)}
                    disabled={sceneTextOverlays.length === 0}
                  >
                    자막 배치
                  </button>
                </div>
                <span className={styles.muted}>
                  현재 모드: {editMode === 'character' ? '캐릭터 배치' : '자막 배치'}
                  {editMode === 'subtitle' && activeCue != null && ` · 편집 중: 씬 ${selectedScene.order}-${activeCue}`}
                </span>
              </div>

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
              <p
                className={styles.muted}
                style={{ fontSize: 12, marginTop: 6, minHeight: 18 }}
                aria-live="polite"
              >
                {saveStatus === 'saving' && '위치 저장 중…'}
                {saveStatus === 'saved' && '✓ 자동 저장됨'}
                {saveStatus === 'error' && '⚠ 저장 실패 — 잠시 후 다시 시도해 주세요'}
                {saveStatus === 'idle' &&
                  (editMode === 'character'
                    ? '캐릭터를 드래그·크기조절·회전하면 자동 저장됩니다 (별도 저장 버튼 없음)'
                    : '자막을 드래그·크기조절·회전하면 자동 저장됩니다. 배경·캐릭터는 참고용(선택 잠금)')}
              </p>
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
                />
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
        <button
          className={styles.btn}
          onClick={() => {
            // 안전장치: 선택 시점 반영이 누락됐어도 이동 전에 전역 storyId 를 현재 선택으로 맞춘다.
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
