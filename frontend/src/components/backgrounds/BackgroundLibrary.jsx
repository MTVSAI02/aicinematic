import useBackgroundStore from '@/store/useBackgroundStore'
import BackgroundCard from './BackgroundCard'
import styles from '@/pages/background/BackgroundPage.module.css'

// 배경 라이브러리(재사용 자산)의 목록만 담당한다.
// "씬에 배경 연결"은 BackgroundPage가 아니라 Scene Editor의 책임으로 옮겼다.
export default function BackgroundLibrary() {
  const backgrounds = useBackgroundStore((s) => s.backgrounds)

  if (backgrounds.length === 0) {
    return <p className={styles.empty}>아직 저장된 배경이 없어요.</p>
  }

  return (
    <ul className={styles.grid}>
      {backgrounds.map((b) => (
        <BackgroundCard key={b.backgroundId} background={b} />
      ))}
    </ul>
  )
}
