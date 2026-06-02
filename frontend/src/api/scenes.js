// 씬 자막 설정(cue 그룹 + 배치) API. 공통 fetch 래퍼(utils/request.js) 사용.
// 자막은 대본(items)에서 자동 생성 → 추가/텍스트 변경 없음. 저장하는 건 줄별 cueOrder(그룹) + layout 뿐.
import { request, jsonBody } from '@/utils/request'

// PATCH /api/scenes/{sceneId}/subtitles — 자막 cue 그룹/배치 저장(전체 교체).
// payload: { storyId, overlays: [{ itemIndex, cueOrder, layout }] }
export function updateSceneSubtitles(sceneId, payload) {
  return request(`/api/scenes/${sceneId}/subtitles`, {
    ...jsonBody(payload),
    method: 'PATCH',
  })
}
