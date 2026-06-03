import { useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from '@/components/NavBar'
import HomePage from '@/pages/home/HomePage'
import StoryInputPage from '@/pages/story-input/StoryInputPage'
import SceneCheckPage from '@/pages/scene-check/SceneCheckPage'
import CharacterPage from '@/pages/character/CharacterPage'
import BackgroundPage from '@/pages/background/BackgroundPage'
import SceneEditorPage from '@/pages/scene-editor/SceneEditorPage'
import VoiceInputPage from '@/pages/voice-input/VoiceInputPage'
import VoicePage from '@/pages/voice/VoicePage'
import TimelinePage from '@/pages/timeline/TimelinePage'
import RenderPage from '@/pages/render/RenderPage'
import useStoryStore from '@/store/useStoryStore'
import { getStories } from '@/api/stories'

// 씬 items로 입력 대본을 역구성한다 (story-input textarea 표시용).
// 백엔드는 원본 script가 아니라 분해된 scenes만 저장하므로 근사 복원한다.
function scenesToScript(scenes) {
  return (scenes ?? [])
    .map((sc) =>
      (sc.items ?? [])
        .map((it) => {
          const tag = it.emotionLabel ? `[${it.emotionLabel}] ` : ''
          return it.type === 'dialogue'
            ? `${tag}${it.speaker}: "${it.text}"`
            : `${tag}${it.text}`
        })
        .join('\n'),
    )
    .join('\n\n')
}

export default function App() {
  // 초기 스토리 결정(최초 1회). persist 로 복원된 storyId 가 있으면 그것을 우선하고,
  // 없거나(빈 값) 목록에 존재하지 않으면(삭제됨) 최신 스토리로 fallback 한다.
  // scenes 는 persist 하지 않으므로 결정된 스토리 기준으로 백엔드에서 다시 채운다.
  const storyId = useStoryStore((s) => s.storyId)
  const initedRef = useRef(false)
  useEffect(() => {
    if (storyId && initedRef.current) return // 이미 초기화 끝났고 storyId 있으면 건드리지 않음
    getStories()
      .then((list) => {
        if (!Array.isArray(list) || list.length === 0) return
        const { setStoryId, setStoryTitle, setStoryText, setScenes } =
          useStoryStore.getState()
        // 복원 storyId 가 목록에 있으면 그대로, 없으면 최신으로
        const restored = storyId ? list.find((s) => s.storyId === storyId) : null
        const target = restored ?? list[list.length - 1]
        initedRef.current = true
        setStoryId(target.storyId)
        setStoryTitle(target.title)
        setScenes(target.scenes)
        setStoryText(scenesToScript(target.scenes))
      })
      .catch(() => {}) // 백엔드 미가동 등은 조용히 무시(빈 화면 유지)
  }, [storyId])

  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/voice-input" element={<VoiceInputPage />} />
        <Route path="/story-input" element={<StoryInputPage />} />
        <Route path="/scene-check" element={<SceneCheckPage />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/background" element={<BackgroundPage />} />
        <Route path="/scene-editor" element={<SceneEditorPage />} />
        <Route path="/voice" element={<VoicePage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/render" element={<RenderPage />} />
      </Routes>
    </BrowserRouter>
  )
}
