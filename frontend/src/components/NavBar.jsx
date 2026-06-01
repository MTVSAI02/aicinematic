import { NavLink } from 'react-router-dom'
import styles from './NavBar.module.css'

const NAV_ITEMS = [
  { to: '/', label: '홈' },
  { to: '/voice-input', label: '음성 입력' },
  { to: '/story-input', label: '스토리 입력' },
  { to: '/scene-check', label: '씬 확인' },
  { to: '/character', label: '캐릭터' },
  { to: '/voice', label: '보이스' },
  { to: '/background', label: '배경' },
  { to: '/scene-editor', label: '씬 편집' },
  { to: '/timeline', label: '타임라인' },
  { to: '/export', label: '출력' },
]

export default function NavBar() {
  return (
    <nav className={styles.nav}>
      <span className={styles.logo}>AI Cinematic</span>
      <ul className={styles.list}>
        {NAV_ITEMS.map(({ to, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive ? `${styles.link} ${styles.active}` : styles.link
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
