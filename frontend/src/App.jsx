import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from '@/components/NavBar'
import HomePage from '@/pages/home/HomePage'
import StoryInputPage from '@/pages/story-input/StoryInputPage'
import SceneCheckPage from '@/pages/scene-check/SceneCheckPage'
import CharacterPage from '@/pages/character/CharacterPage'
import BackgroundPage from '@/pages/background/BackgroundPage'
import SceneEditorPage from '@/pages/scene-editor/SceneEditorPage'
import VoicePage from '@/pages/voice/VoicePage'
import TimelinePage from '@/pages/timeline/TimelinePage'
import ExportPage from '@/pages/export/ExportPage'

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
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
