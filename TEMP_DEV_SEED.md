# ⚠️ 임시 개발 시드/스냅샷 (SEED_DEV) — 제거 체크리스트

ComfyUI / 외부 AI 서버 없이 **scene-editor 흐름을 테스트**하기 위해 임시로 넣은 코드다.
storage 폴더에 직접 넣어둔 이미지로 캐릭터/배경/가라 스토리를 시드하고, JSON 스냅샷으로
백엔드 재시작에도 유지되게 한다.

**실제 생성(AI 서버) / 영구 저장(DB)이 안정화되면 아래를 전부 제거한다.**

---

## 왜 임시인가
- 백엔드 저장소가 in-memory(mock)이라 재시작 시 데이터가 사라진다.
- ComfyUI/AI 서버가 없을 때도 scene-editor에서 캐릭터·배경·씬을 연결해보기 위해,
  미리 준비한 이미지로 레코드를 시드하고 `storage/dev_state.json`에 스냅샷한다.

## 동작 방식 (참고)
- `SEED_DEV=1` 일 때만 동작 (`backend/.env` 또는 환경변수).
- startup: 스냅샷 있으면 복원, 없으면 dev_seed로 기본값 시드 후 스냅샷 생성.
- 변경 요청(POST/PATCH/PUT/DELETE)마다 스냅샷 저장 → kill 해도 최신 상태 유지.
- 끄기: `backend/.env`의 `SEED_DEV` 제거(또는 미설정)로 즉시 비활성.
- 초기화: `backend/app/storage/dev_state.json` 삭제 후 재시작.

---

## 🗑️ 삭제 대상 체크리스트

### 1) 새로 추가한 파일 — 통째로 삭제
- [ ] `backend/app/core/dev_seed.py`
- [ ] `backend/app/core/dev_persist.py`

### 2) 기존 파일에서 추가분만 되돌리기
- [ ] `backend/app/main.py`
  - `root()` 아래의 **`# ── ⚠️ 임시 개발 시드/스냅샷 (SEED_DEV=1) ──` 블록 전체** 제거
    (`if os.getenv("SEED_DEV") == "1":` ~ `_dev_persist_middleware` 까지)
- [ ] `backend/.env` (gitignore, 로컬)
  - `SEED_DEV=1` 줄 + 그 주석 제거
- [ ] `frontend/src/App.jsx`
  - 앱 로드 시 최신 스토리를 store에 채우는 `useEffect` + `scenesToScript()` 헬퍼 제거
  - 그와 함께 추가된 import 제거: `useEffect`, `useStoryStore`, `getStories`
  - ⚠️ **판단 필요**: 이 훅은 "마지막 스토리 자동 불러오기" UX이기도 하다.
    시드 데모용으로만 넣은 것이므로 기본은 제거. (resume 기능으로 유지하고 싶으면 남겨도 됨)

### 3) 생성/테스트 산출물 정리 (storage, gitignore — 커밋 안 됨)
- [ ] `backend/app/storage/dev_state.json` (스냅샷)
- [ ] 시드용으로 직접 넣어둔 테스트 이미지 (필요 없으면)
  - `backend/app/storage/characters/little_prince.png`
  - `backend/app/storage/characters/fennec_fox.png`
  - `backend/app/storage/backgrounds/library/background1.png`

---

## 유지 (이번 시드와 무관한 정상 기능 — 지우지 말 것)
- `frontend/src/api/stories.js` 의 `getStory()` — scene-check 새로고침 재수화용(정상 기능)
- `frontend/src/pages/scene-check/SceneCheckPage.jsx`, `story-input/StoryInputPage.jsx` 의 storyId fetch 로직
- `backend/app/core/config.py` 의 `BACKGROUND_LIBRARY_STORAGE_DIR` 및 배경 저장(복사) 로직
- `frontend` 의 배경 후보 카드 제거(`removeCandidate`) 등

> 위 "유지" 항목들은 별도 기능으로 이미 커밋된 것이며, SEED_DEV 스캐폴딩이 아니다.

---

## 제거 후 확인
- [ ] `SEED_DEV` 없이 `uv run uvicorn backend.app.main:app --port 8000` 정상 기동
- [ ] `import app.main` 에러 없음 (dev_seed/dev_persist import 잔존 없음)
- [ ] `frontend` `npm run build` 통과 (App.jsx import 깨짐 없음)
- [ ] `git grep -n "SEED_DEV\|dev_seed\|dev_persist\|scenesToScript"` → 잔존 참조 없음
