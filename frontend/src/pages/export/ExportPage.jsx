import { useMemo, useState } from 'react'
import { mockCharacters, mockScenes } from '../../api/mockData'
import { TimelinePage } from '../timeline/TimelinePage'
import { AudioPanel } from './AudioPanel'
import './ExportPage.css'

const STORY_ID = 'story_001'

export function ExportPage() {
  const [scenes, setScenes] = useState(() =>
    [...mockScenes].sort((a, b) => a.order - b.order),
  )

  const characterNameById = useMemo(() => {
    return mockCharacters.reduce((result, character) => {
      result[character.id] = character.name
      return result
    }, {})
  }, [])

  function updateSceneAudio(sceneId, audio) {
    setScenes((currentScenes) =>
      currentScenes.map((scene) => {
        if (scene.id !== sceneId) return scene

        const safeDuration = Math.max(
          scene.durationSec,
          audio.audioDurationSec + 0.5,
        )

        return {
          ...scene,
          durationSec: Number(safeDuration.toFixed(1)),
          audioPath: audio.audioPath,
          audioDurationSec: audio.audioDurationSec,
        }
      }),
    )
  }

  function updateSceneDuration(sceneId, durationSec) {
    setScenes((currentScenes) =>
      currentScenes.map((scene) =>
        scene.id === sceneId ? { ...scene, durationSec } : scene,
      ),
    )
  }

  return (
    <main className="app-shell">
      <section className="hero-section">
        <p className="eyebrow">AI Cinematic · Export MVP</p>
        <h1>음성 생성과 미리듣기</h1>
        <p className="hero-copy">
          백엔드가 준비되기 전에도 B 담당 화면을 진행할 수 있도록, mock
          씬 데이터로 TTS 생성 흐름을 먼저 완성합니다.
        </p>
      </section>

      <AudioPanel
        storyId={STORY_ID}
        scenes={scenes}
        characterNameById={characterNameById}
        onSceneAudioGenerated={updateSceneAudio}
      />

      <TimelinePage
        storyId={STORY_ID}
        scenes={scenes}
        characterNameById={characterNameById}
        onSceneDurationChange={updateSceneDuration}
      />
    </main>
  )
}
