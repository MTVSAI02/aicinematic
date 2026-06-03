# 컴포넌트 스펙

## 페이지 목록

| 페이지 | 경로 | 상태 |
|--------|------|------|
| 홈 | `/` | ✅ 구현 완료 |
| 음성 입력 | `/voice-input` | ✅ 구현 완료 |
| 스토리 입력 | `/story-input` | ✅ 구현 완료 |
| 씬 확인 | `/scene-check` | ✅ 구현 완료 |
| 캐릭터 | `/character` | ✅ 구현 완료 |
| 보이스 | `/voice` | ✅ 구현 완료 |
| 배경 | `/background` | ✅ 구현 완료 |
| 씬 편집기 | `/scene-editor` | ✅ 구현 완료 |
| 타임라인 | `/timeline` | ✅ 구현 완료 |
| 출력 | `/export` | ✅ 구현 완료 |

---

## 공통 컴포넌트

### NavBar
- 위치: `frontend/src/components/NavBar.jsx`
- 전체 페이지 상단 고정
- 현재 경로 활성화 스타일 자동 적용

### AiConnectionCheck
- 위치: `frontend/src/components/AiConnectionCheck.jsx`
- AI 서버 연결 상태 확인 배너

---

## 캐릭터 컴포넌트
- `CharacterCard` — 캐릭터 이미지·이름 카드
- `CharacterList` — 카드 목록 그리드
- `CharacterCreateForm` — 이름 / 외형 설명 / 외형 프롬프트 입력 폼
- `CharacterEditForm` — 수정 폼

## 보이스 컴포넌트
- `VoiceCard` — 보이스 이름·타입·오디오 카드
- `VoiceLibrary` — 보이스 목록
- `VoiceCreateForm` — 보이스 생성 폼
- `VoiceTargetCard` — 연결 대상 카드 (나레이션/캐릭터)
- `VoiceTargetPanel` — 연결 대상 패널

## 배경 컴포넌트
- `BackgroundCard` — 배경 이미지 카드
- `BackgroundLibrary` — 배경 목록
- `BackgroundCandidateCard` — 후보 이미지 카드
- `BackgroundCandidateGrid` — 후보 그리드
- `BackgroundSaveForm` — 저장 폼
- `BackgroundPromptPanel` — 프롬프트 입력 패널
