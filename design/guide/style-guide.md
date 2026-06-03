# AI Cinematic 스타일 가이드

## 색상 (CSS 변수)

| 변수 | 라이트 | 다크 | 용도 |
|------|--------|------|------|
| `--text` | #6b6375 | #9ca3af | 본문, 부제 |
| `--text-h` | #08060d | #f3f4f6 | 제목, 강조 텍스트 |
| `--bg` | #ffffff | #16171d | 페이지 배경 |
| `--border` | #e5e4e7 | #2e303a | 카드·인풋 테두리 |
| `--code-bg` | #f4f3ec | #1f2028 | 코드블록·샘플박스 배경 |
| `--accent` | #aa3bff | #c084fc | 주요 액션, 선택 상태 |
| `--accent-bg` | rgba(170,59,255,0.1) | rgba(192,132,252,0.15) | 강조 배경 |
| `--accent-border` | rgba(170,59,255,0.5) | rgba(192,132,252,0.5) | 강조 테두리 |
| `--danger` | #c0392b | #e05c5c | 에러, 삭제 |

> ⚠️ 색상 하드코딩 금지. CSS 변수만 사용. (--danger 계열 예외)

---

## 타이포그래피

| 요소 | 크기 | 굵기 | 용도 |
|------|------|------|------|
| h1 | 56px (모바일 36px) | 500 | 페이지 제목 |
| h2 | 24px (모바일 20px) | 500 | 섹션 제목, 패널 제목 |
| body | 18px | 400 | 본문 |
| label | 14px | 400 | 폼 레이블 |
| small | 13px | 400 | 안내 문구, 메시지 |
| xs | 12px | 400 | 뱃지, 힌트 |

---

## 간격

- 페이지 패딩: `40px 24px`
- 페이지 최대 너비: `980px`
- 섹션 간격: `32px`
- 카드 패딩: `16px`
- 컴포넌트 간격: `8px ~ 16px`

---

## 컴포넌트 규칙

### 버튼
- Primary: `background: var(--accent)`, `color: #fff`, `border-radius: 8px`
- Secondary: `border: 1px solid var(--border)`, `background: transparent`
- 비활성: `opacity: 0.4`, `cursor: not-allowed`

### 카드
- `border: 1px solid var(--border)`, `border-radius: 10px`, `padding: 16px`
- 선택 상태: `border-color: var(--accent-border)`, `box-shadow: var(--shadow)`

### 인풋 / 텍스트에리어
- `border: 1px solid var(--border)`, `border-radius: 8px`, `padding: 10px 12px`
- 포커스: `border-color: var(--accent-border)`, `outline: none`

### 뱃지
- `padding: 2px 8px`, `border-radius: 4px`
- 액센트: `background: var(--accent-bg)`, `color: var(--accent)`
- 일반: `background: var(--code-bg)`, `color: var(--text)`

### 도움말 박스 (help)
- `background: var(--accent-bg)`, `border: 1px solid var(--accent-border)`, `border-radius: 8px`
- `font-size: 13px`, `padding: 12px 14px`

### 빈 상태 (empty)
- `border: 1px dashed var(--border)`, `border-radius: 8px`
- `text-align: center`, `padding: 32px`

---

## 레이아웃 패턴

### 2컬럼 그리드
```css
display: grid;
grid-template-columns: 1fr 1fr;
gap: 24px;
```
모바일(`max-width: 760px`): `grid-template-columns: 1fr`

### 페이지 하단 네비게이션
```css
display: flex;
justify-content: space-between;
margin-top: 24px;
```

---

## 반응형 기준

| 브레이크포인트 | 적용 |
|--------------|------|
| `max-width: 1024px` | 폰트 축소 (h1: 36px, base: 16px) |
| `max-width: 760px` | 2컬럼 → 1컬럼 |
| `max-width: 600px` | 버튼/패널 세로 정렬 |
