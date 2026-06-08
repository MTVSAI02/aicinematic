import useCharacterStore from '@/store/useCharacterStore'
import CharacterCard from './CharacterCard'
import styles from '@/pages/character/CharacterPage.module.css'

export default function CharacterList() {
  const characters = useCharacterStore((s) => s.characters)

  if (characters.length === 0) {
    return <p className={styles.empty}>아직 생성된 캐릭터가 없어요.</p>
  }

  return (
    <ul className={styles.grid}>
      {characters.map((c) => (
        <CharacterCard key={c.characterId} character={c} />
      ))}
    </ul>
  )
}
