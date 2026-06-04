import { NavLink } from 'react-router-dom'
import styles from './NavBar.module.css'
import NotificationBell from './NotificationBell'

import navHome from '@design/assets/figma-icons/Nav/nav_home.svg'
import navVoiceInput from '@design/assets/figma-icons/Nav/nav_voice_input.svg'
import navStoryInput from '@design/assets/figma-icons/Nav/nav_story_input.svg'
import navSceneCheck from '@design/assets/figma-icons/Nav/nav_scene_check.svg'
import navCharacter from '@design/assets/figma-icons/Nav/nav_character.svg'
import navVoice from '@design/assets/figma-icons/Nav/nav_voice.svg'
import navBackground from '@design/assets/figma-icons/Nav/nav_background.svg'
import navSceneEditor from '@design/assets/figma-icons/Nav/nav_scene_editor.svg'
import navTimeline from '@design/assets/figma-icons/Nav/nav_timeline.svg'
import navExport from '@design/assets/figma-icons/Nav/nav_export.svg'
import logo from '@design/assets/figma-icons/Nav/nav_Logo.svg'

const NAV_ITEMS = [
  { to: '/', label: '홈', icon: navHome },
  { to: '/voice-input', label: '음성 입력', icon: navVoiceInput },
  { to: '/story-input', label: '스토리 입력', icon: navStoryInput },
  { to: '/scene-check', label: '씬 확인', icon: navSceneCheck },
  { to: '/character', label: '캐릭터', icon: navCharacter },
  { to: '/voice', label: '보이스', icon: navVoice },
  { to: '/background', label: '배경', icon: navBackground },
  { to: '/scene-editor', label: '씬 편집', icon: navSceneEditor },
  { to: '/timeline', label: '타임라인', icon: navTimeline },
  { to: '/render', label: '출력', icon: navExport },
]

export default function NavBar() {
  return (
    <nav className={styles.nav}>
      <div className={styles.logoContainer}>
        <img src={logo} alt="몽실책방 로고" className={styles.logoImage} />
      </div>
      <ul className={styles.list}>
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <li key={to} className={styles.item}>
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive ? `${styles.link} ${styles.active}` : styles.link
              }
            >
              <img src={icon} alt={`${label} 아이콘`} className={styles.icon} />
              <span className={styles.label}>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
      <NotificationBell />
    </nav>
  )
}
