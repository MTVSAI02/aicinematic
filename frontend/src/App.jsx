import { useEffect } from 'react'
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
import ExportPage from '@/pages/export/ExportPage'
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
  // store에 스토리가 없으면 백엔드의 최신 스토리를 불러와 채운다.
  // → /story-input(제목·대본), /scene-check(씬)이 시드/이전 스토리를 그대로 보여준다.
  //   (사용자가 입력/파싱을 시작하면 storyId가 생겨 더 이상 덮어쓰지 않음)
  const storyId = useStoryStore((s) => s.storyId)
  useEffect(() => {
    if (storyId) return
    getStories()
      .then((list) => {
        if (!Array.isArray(list) || list.length === 0) return
        const latest = list[list.length - 1] // 가장 최근 스토리
        const { setStoryId, setStoryTitle, setStoryText, setScenes } =
          useStoryStore.getState()
        setStoryId(latest.storyId)
        setStoryTitle(latest.title)
        setScenes(latest.scenes)
        setStoryText(scenesToScript(latest.scenes))
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
        <Route path="/export" element={<ExportPage />} />
      </Routes>
    </BrowserRouter>
  )
}
