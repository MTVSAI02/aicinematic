# AI Cinematic — Design System

> 이 문서는 프론트엔드 개발 시 디자인 일관성을 유지하기 위한 단일 참조 문서입니다.
> 새 컴포넌트를 만들 때 이 문서의 토큰과 패턴을 그대로 사용하세요.

---

## 1. 컬러 토큰

`src/index.css`의 CSS 변수를 항상 사용합니다. 색상 하드코딩 금지.

### Light / Dark 공통 구조

| 변수 | 용도 |
|------|------|
| `var(--bg)` | 페이지 배경 |
| `var(--text)` | 본문 텍스트 (흐린 색) |
| `var(--text-h)` | 제목·강조 텍스트 (진한 색) |
| `var(--border)` | 선, 구분선, 카드 테두리 |
| `var(--code-bg)` | 코드 블록, 비어있는 영역 배경, textarea |
| `var(--accent)` | 브랜드 컬러 (보라), CTA 버튼, 활성 탭 |
| `var(--accent-bg)` | accent 연한 배경 (뱃지, hover) |
| `var(--accent-border)` | accent 테두리 (focus ring 등) |
| `var(--social-bg)` | 소셜 버튼처럼 반투명한 배경 |
| `var(--shadow)` | 카드 hover 그림자 |

### Light 값

```
--text:         #6b6375
--text-h:       #08060d
--bg:           #fff
--border:       #e5e4e7
--code-bg:      #f4f3ec
--accent:       #aa3bff
--accent-bg:    rgba(170, 59, 255, 0.1)
--accent-border:rgba(170, 59, 255, 0.5)
```

### Dark 값 (`prefers-color-scheme: dark` 자동 적용)

```
--text:         #9ca3af
--text-h:       #f3f4f6
--bg:           #16171d
--border:       #2e303a
--code-bg:      #1f2028
--accent:       #c084fc
--accent-bg:    rgba(192, 132, 252, 0.15)
--accent-border:rgba(192, 132, 252, 0.5)
```

---

## 2. 타이포그래피

### 폰트 변수

| 변수 | 적용 대상 |
|------|-----------|
| `var(--sans)` | 기본 본문 (`system-ui, Segoe UI, Roboto`) |
| `var(--heading)` | 제목 (동일 스택) |
| `var(--mono)` | 코드, 대본 입력, 태그 |

### 크기 체계

| 요소 | 크기 | 비고 |
|------|------|------|
| `h1` | 56px (모바일 36px) | `font-weight: 500`, `letter-spacing: -1.68px` |
| `h2` | 24px (모바일 20px) | `font-weight: 500`, `letter-spacing: -0.24px` |
| 본문 기본 | 18px (모바일 16px) | `line-height: 145%` |
| 카드 본문 | 15px | |
| 보조 텍스트·레이블 | 13–14px | `color: var(--text)` |
| 뱃지·태그 | 11–12px | |

---

## 3. 스페이싱

8px 단위 그리드를 기준으로 합니다.

| 용도 | 값 |
|------|----|
| 페이지 패딩 (상하) | `40–48px` |
| 페이지 패딩 (좌우) | `24px` |
| 섹션 간격 | `40px` |
| 카드 내부 패딩 | `16px` |
| 요소 간 gap | `8px / 12px / 16px / 24px` |
| 버튼 패딩 | `10px 24px` (기본) / `6px 14px` (소형) |

---

## 4. 컴포넌트 패턴

### 4-1. 버튼

```jsx
// Primary — CTA, 다음 단계
<button className={styles.btn}>텍스트</button>

// Secondary — 뒤로 가기, 취소
<button className={styles.btnSecondary}>텍스트</button>

// Ghost (accent tinted) — 카드 내 액션
<button className={styles.panelBtn}>텍스트</button>
```

```css
/* Primary */
.btn {
  padding: 10px 24px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Secondary */
.btnSecondary {
  padding: 10px 24px;
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}
.btnSecondary:hover { background: var(--code-bg); }

/* Ghost */
.panelBtn {
  padding: 6px 14px;
  background: var(--accent-bg);
  color: var(--accent);
  border: 1px solid var(--accent-border);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.panelBtn:hover { background: var(--accent); color: #fff; }
```

### 4-2. 카드

```css
.card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
/* hover가 필요한 경우 */
.card:hover {
  box-shadow: var(--shadow);
}
```

### 4-3. 인풋 / 텍스트에리어

```css
.input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 15px;
  background: var(--bg);
  color: var(--text-h);
  width: 100%;
  box-sizing: border-box;
}
.input:focus {
  outline: none;
  border-color: var(--accent-border);
}

/* 대본·코드용 텍스트에리어 */
.textarea {
  /* 위와 동일 + */
  font-family: var(--mono);
  background: var(--code-bg);
  resize: vertical;
}
```

### 4-4. 뱃지 / 태그

```css
/* 내레이션 */
.narration {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--code-bg);
  color: var(--text);
}

/* 대사 / 강조 */
.dialogue {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--accent-bg);
  color: var(--accent);
}
```

### 4-5. 빈 상태 (Empty State)

```css
.empty {
  color: var(--text);
  padding: 32px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  text-align: center;
}
```

### 4-6. 페이지 하단 액션 바

항상 좌우 버튼 (`← 이전` / `다음 →`) 패턴을 유지합니다.

```jsx
<div className={styles.actions}>
  <button className={styles.btnSecondary} onClick={() => navigate('/prev')}>
    ← 이전 페이지
  </button>
  <button className={styles.btn} onClick={() => navigate('/next')}>
    다음 페이지 →
  </button>
</div>
```

```css
.actions {
  display: flex;
  justify-content: space-between;
  margin-top: 32px;
}
```

### 4-7. 진행률 바

```jsx
<div className={styles.bar}>
  <div className={styles.fill} style={{ width: `${progress}%` }} />
</div>
```

```css
.bar {
  width: 100%;
  height: 12px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
}
.fill {
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.4s ease;
}
```

---

## 5. 레이아웃 규칙

### 페이지 너비

```css
/* 단일 컬럼 콘텐츠 (폼, 리스트) */
.page {
  padding: 40px 24px;
  max-width: 760px;
  margin: 0 auto;
}

/* 2단 레이아웃 (씬 편집기 등) */
.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
}

/* 카드 그리드 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}
```

### 네비게이션 바

- 높이: `56px`, `position: sticky; top: 0; z-index: 100`
- 배경: `var(--bg)`, 하단 border: `1px solid var(--border)`
- 활성 탭: `background: var(--accent-bg); color: var(--accent); font-weight: 500`

---

## 6. 보더 반경

| 용도 | 값 |
|------|----|
| 페이지 카드, 인풋, 버튼 | `8px` |
| 소형 버튼, 뱃지, 코드 | `4–6px` |
| 진행률 바, pill | `99px` |
| 이미지 썸네일 | `6px` |

---

## 7. 애니메이션

| 속성 | 값 |
|------|----|
| 버튼 hover (opacity) | `transition: opacity 0.15s` |
| 배경색 변환 | `transition: background 0.15s` |
| 진행률 바 | `transition: width 0.4s ease` |
| 그림자 hover | `transition: box-shadow 0.3s` |

무거운 애니메이션(translate, scale) 은 지금 단계에서 사용하지 않습니다.

---

## 8. 다크모드

별도 작업 불필요. `prefers-color-scheme: dark` 미디어 쿼리로 `index.css`가 자동으로 처리합니다. CSS 변수만 사용하면 다크모드가 자동으로 적용됩니다.

---

## 9. 파일 네이밍 규칙

| 대상 | 규칙 |
|------|------|
| 페이지 컴포넌트 | `PascalCase + Page.jsx` — `CharacterPage.jsx` |
| 공통 컴포넌트 | `PascalCase.jsx` — `SceneCard.jsx` |
| CSS 모듈 | 컴포넌트명 + `.module.css` — `CharacterPage.module.css` |
| 클래스명 | `camelCase` — `.btnSecondary`, `.sceneCard` |

---

## 10. 체크리스트 (컴포넌트 작성 전)

- [ ] 색상은 CSS 변수 사용? (`var(--accent)` 등)
- [ ] 폰트 사이즈는 체계 안에 있음? (11/13/14/15/18px)
- [ ] 버튼은 Primary / Secondary / Ghost 중 하나로?
- [ ] 빈 상태(empty state) 처리했음?
- [ ] 다크모드에서 깨지는 하드코딩 색상 없음?
- [ ] 페이지 하단에 `actions` 바(이전/다음) 있음?

---

*최종 업데이트: 26-05-28*
