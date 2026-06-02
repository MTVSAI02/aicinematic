// 브라우저 미리보기 재생용 순수 계산 유틸(렌더링 X — 시간→씬→cue 매핑만).
// 실제 mp4/ffmpeg/오디오 없음. 타임라인 데이터(duration, cueTimings)만으로 "지금 무엇을 보여줄지" 계산한다.

const durOf = (s) => (typeof s?.duration === 'number' && s.duration > 0 ? s.duration : 3)

// 각 씬의 시작 오프셋(누적합)과 전체 길이.  씬 i 는 [starts[i], starts[i]+duration) 구간을 차지한다.
export function sceneOffsets(scenes) {
  let acc = 0
  const starts = scenes.map((s) => {
    const start = acc
    acc += durOf(s)
    return start
  })
  return { starts, total: acc }
}

// globalTime 이 속한 씬 index. 범위를 벗어나면 양 끝으로 클램프.
export function sceneIndexAt(scenes, starts, t) {
  if (scenes.length === 0) return -1
  for (let i = scenes.length - 1; i >= 0; i--) {
    if (t >= starts[i]) return i
  }
  return 0
}

// 씬 안의 로컬 시간 기준으로 "지금 보여야 하는" cueOrder 집합.
// cue.startSec <= localTime < cue.startSec + cue.durationSec
export function visibleCueOrders(scene, localTime) {
  const set = new Set()
  for (const c of scene?.cueTimings ?? []) {
    if (localTime >= c.startSec && localTime < c.startSec + c.durationSec) set.add(c.cueOrder)
  }
  return set
}

// globalTime → 현재 재생 상태 한 번에 계산.
export function resolvePlayback(scenes, starts, total, globalTime) {
  const t = Math.max(0, Math.min(globalTime, total))
  const index = sceneIndexAt(scenes, starts, Math.min(t, Math.max(0, total - 1e-6)))
  if (index < 0) return null
  const scene = scenes[index]
  const localTime = t - starts[index]
  return {
    index,
    scene,
    localTime,
    duration: durOf(scene),
    visibleCueOrders: visibleCueOrders(scene, localTime),
  }
}
