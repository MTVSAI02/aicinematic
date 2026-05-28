import { SceneTimelineCard } from './SceneTimelineCard'
import './TimelinePage.css'

export function TimelinePage({
  storyId,
  scenes,
  characterNameById,
  onSceneDurationChange,
}) {
  const totalDurationSec = scenes.reduce(
    (total, scene) => total + scene.durationSec,
    0,
  )
  const generatedVoiceCount = scenes.filter((scene) => scene.audioPath).length

  return (
    <section className="panel timeline-panel">
      <div className="panel-header timeline-header">
        <div>
          <p className="eyebrow">R-44 · R-46</p>
          <h2>타임라인</h2>
        </div>
        <div className="timeline-summary" aria-label="타임라인 요약">
          <span>총 {totalDurationSec.toFixed(1)}초</span>
          <span>
            음성 {generatedVoiceCount}/{scenes.length}
          </span>
        </div>
      </div>

      <div className="timeline-rail" aria-label="씬 타임라인">
        {scenes.map((scene) => (
          <SceneTimelineCard
            key={scene.id}
            storyId={storyId}
            scene={scene}
            characterNameById={characterNameById}
            onSceneDurationChange={onSceneDurationChange}
          />
        ))}
      </div>
    </section>
  )
}
