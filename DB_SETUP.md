# DB_SETUP.md — 백엔드 PostgreSQL 로컬 셋업 (팀원용)

백엔드는 **PostgreSQL** 을 쓴다. 아래 순서대로 하면 누구나 동일한 DB를 띄우고 스키마까지 만들 수 있다.
**Docker 이미지를 주고받을 필요 없다** — 컨테이너는 compose 로, 스키마는 `alembic upgrade head` 로 재현한다.

---

## 0. 준비물
- **Docker Desktop** (실행 중이어야 함) — https://www.docker.com/products/docker-desktop
- 레포 클론 + 백엔드 의존성 설치(`uv sync` 등)
- (DB 확인용) **DBeaver** — 4번 참고

---

## 1. DB 컨테이너 띄우기

둘 중 **하나만** 하면 된다. (둘 다 결과는 동일 — 같은 이미지/계정/포트/볼륨)

### 1-A. compose 버전 (레포 루트에서) — 권장
```bash
docker compose up -d
```
- `docker-compose.yml` 기준으로 `pgvector/pgvector:pg16` 컨테이너(`aicinematic-pg`)가 `localhost:5432` 에 뜬다.
- 상태 확인: `docker compose ps` (healthy 뜨면 OK)
- 중지: `docker compose down` (데이터 유지) / 완전 초기화: `docker compose down -v`

### 1-B. CLI(`docker run`) 버전 — Docker Desktop(GUI) 없이
> Docker Desktop 없이 **Docker Engine(CLI)만** 있어도 된다. (Linux 는 기본 제공, macOS 는 `colima`/`OrbStack`, Windows 는 WSL2 docker 등으로 엔진만 띄우면 됨.) compose 파일도 필요 없다.

**최초 1회 — 컨테이너 생성+기동:**
```bash
docker run -d \
  --name aicinematic-pg \
  -e POSTGRES_DB=aicinematic \
  -e POSTGRES_USER=aicinematic \
  -e POSTGRES_PASSWORD=aicinematic_dev_pw \
  -p 5432:5432 \
  -v aicinematic_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg16
```
**한 줄 버전 (Windows/Mac/Linux 공통 — 줄바꿈 문제 없음, 그대로 복붙):**
```bash
docker run -d --name aicinematic-pg -e POSTGRES_DB=aicinematic -e POSTGRES_USER=aicinematic -e POSTGRES_PASSWORD=aicinematic_dev_pw -p 5432:5432 -v aicinematic_pgdata:/var/lib/postgresql/data --restart unless-stopped pgvector/pgvector:pg16
```

> **OS별 차이는 docker 명령이 아니라 "여러 줄 잇기" 문자뿐이다.** 위 멀티라인 예시의 `\` 는 Mac/Linux 용이고,
> Windows PowerShell 은 백틱(`` ` ``), Windows CMD 는 `^` 를 쓴다. 헷갈리면 **위 한 줄 버전**을 쓰면 된다.
> (`docker run/compose/ps/stop` 명령 자체와 `uv run ...` 은 모든 OS 동일.)

**이후 운영:**
```bash
docker ps                    # 상태 확인
docker stop aicinematic-pg   # 중지(데이터 유지)
docker start aicinematic-pg  # 다시 기동
docker rm -f aicinematic-pg                    # 컨테이너 삭제(볼륨=데이터는 유지)
docker rm -f aicinematic-pg && docker volume rm aicinematic_pgdata   # 완전 초기화(데이터 삭제)
```
> 같은 이름(`aicinematic-pg`)이 이미 있으면 `docker run` 이 "name in use" 로 실패한다 →
> `docker start aicinematic-pg` 로 기동하거나, 지우고(`docker rm -f`) 다시 run.

---

## 2. backend/.env 설정

`backend/.env` 파일에 아래 줄이 있어야 한다 (`.env` 는 gitignore 라 각자 만든다):

```env
DATABASE_URL=postgresql+psycopg://aicinematic:aicinematic_dev_pw@localhost:5432/aicinematic
```
> compose 의 POSTGRES_USER / PASSWORD / DB 와 값이 일치해야 한다. (id `aicinematic`, pw `aicinematic_dev_pw`, db `aicinematic`)

---

## 3. 스키마 생성 (★ 서버 켜기 전에 필수)

```bash
cd backend
uv run alembic upgrade head
```
- 모든 테이블(voices/characters/backgrounds/stories/scenes/scene_characters/tts_audios/render_results/jobs/users)
  + 트리거가 생성된다. **데이터는 0행**(자동 시드 없음).
- 확인: `uv run alembic current` → 최신 리비전이 나오면 OK.

> ⚠️ 이걸 안 하면 서버 부팅 시 `relation "..." does not exist` 로 죽는다. **새 PC / DB 초기화 / git pull 후엔 항상 먼저 실행.**

이후 백엔드 실행:
```bash
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
> 부팅 직후 **DB는 완전히 빈 상태**다(자동 시드 없음). 보이스/스토리/캐릭터 등 모든 데이터는 화면(API)에서 만든다.

---

## 4. DBeaver 로 DB 확인

1. `Database` → `New Database Connection` → **PostgreSQL** 선택
2. Main 탭 입력:
   ```
   Host:     localhost
   Port:     5432
   Database: aicinematic
   Username: aicinematic
   Password: 
   ```
   (Save password 체크)
3. `Test Connection` → 처음이면 **PostgreSQL 드라이버 Download** 팝업 → Download → `Connected` 확인
4. `Finish`
5. 좌측 트리: `aicinematic` → Databases → aicinematic → Schemas → **public → Tables** 에서 테이블 확인
   - 테이블 더블클릭 → **Data 탭** 에서 행 조회
   - `SQL Editor` 에서 직접 쿼리: 예) `select * from voices;` (처음엔 0행 — 데이터 만들면 채워짐)

---

## 5. 자주 쓰는 명령 / 트러블슈팅

| 상황 | 명령 |
|------|------|
| DB 기동 | `docker compose up -d` |
| DB 중지(데이터 유지) | `docker compose down` |
| **DB 완전 초기화**(데이터 삭제) | `docker compose down -v` → `docker compose up -d` → `alembic upgrade head` |
| 컨테이너 상태 | `docker compose ps` |
| psql 직접 접속(컨테이너 내부) | `docker exec -it aicinematic-pg psql -U aicinematic -d aicinematic` |

- **포트 5432 충돌**(로컬에 다른 PostgreSQL): compose 의 ports 를 `"5433:5432"` 로 바꾸고 `.env` 의 URL 도 `localhost:5433` 로.
- **`relation "..." does not exist`**: `alembic upgrade head` 안 돌린 것 → 3번 실행.
- **모델 바꿨는데 DB에 반영 안 됨**: 모델(`app/db/models.py`)만 고치면 안 되고 `uv run alembic revision --autogenerate -m "설명"` → `alembic upgrade head` 까지 해야 한다.

---

## 요약 (3줄)
```bash
docker compose up -d                       # 1) DB 컨테이너
# backend/.env 에 DATABASE_URL 추가
cd backend && uv run alembic upgrade head  # 2) 스키마 생성
uv run uvicorn backend.app.main:app --reload  # 3) 서버
```
