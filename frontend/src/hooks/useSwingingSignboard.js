import { useEffect, useRef, useState } from 'react'

export default function useSwingingSignboard(ratio = 2533 / 2672) {
  const titleRef = useRef(null)
  const [frameHeight, setFrameHeight] = useState(0)

  useEffect(() => {
    const el = titleRef.current
    if (!el) return

    const updateHeight = () => {
      const rect = el.getBoundingClientRect()
      if (rect.width > 0) {
        const height = rect.width * ratio
        setFrameHeight(height)
      }
    }

    updateHeight()
    window.addEventListener('resize', updateHeight)
    const timer = setTimeout(updateHeight, 150)

    const observer = new ResizeObserver(() => {
      updateHeight()
    })
    observer.observe(el)

    return () => {
      window.removeEventListener('resize', updateHeight)
      clearTimeout(timer)
      observer.disconnect()
    }
  }, [ratio])

  useEffect(() => {
    const el = titleRef.current
    if (!el) return

    let angle = 0
    let velocity = 0

    let isDragging = false
    let lastX = 0
    let lastTime = Date.now()

    let time = 0
    let frameId

    const springK = 0.15      // 복원력 계수
    const damping = 0.92      // 감쇠 계수

    const updatePhysics = () => {
      time += 16.67
      
      // 평상시 미세하게 둥실거리는 효과
      const floatAngle = Math.sin(time * 0.001) * 1.5

      if (!isDragging) {
        // 복원력과 댐핑 적용한 시계추 진자 물리
        const acceleration = -springK * angle
        velocity += acceleration
        velocity *= damping
        angle += velocity * 0.08
      }

      // 끈 상단 회전축 기준으로 transform 회전만 적용
      el.style.transform = `rotate(${angle + floatAngle}deg)`

      frameId = requestAnimationFrame(updatePhysics)
    }

    const handleStart = (clientX) => {
      isDragging = true
      lastX = clientX
      lastTime = Date.now()
      el.style.cursor = 'grabbing'
    }

    const handleMove = (clientX) => {
      if (!isDragging) return
      const now = Date.now()
      const dt = now - lastTime

      const deltaX = clientX - lastX
      
      // 마우스 X 변화량을 진자 각도 변화량으로 변환 (끈 길이가 450px이므로 각도 변화율 완화)
      angle += deltaX * 0.08

      // 회전각 한계선 제한
      if (angle > 20) angle = 20
      if (angle < -20) angle = -20

      if (dt > 0) {
        const targetVelocity = (deltaX / dt) * 4
        velocity = velocity * 0.3 + targetVelocity * 0.7
      }

      lastX = clientX
      lastTime = now
    }

    const handleEnd = () => {
      if (isDragging) {
        isDragging = false
        el.style.cursor = 'grab'
      }
    }

    const onMouseDown = (e) => {
      e.preventDefault()
      handleStart(e.clientX)
    }
    const onMouseMove = (e) => {
      handleMove(e.clientX)
    }
    const onMouseUp = () => {
      handleEnd()
    }

    const onTouchStart = (e) => {
      if (e.touches.length > 0) {
        handleStart(e.touches[0].clientX)
      }
    }
    const onTouchMove = (e) => {
      if (e.touches.length > 0) {
        handleMove(e.touches[0].clientX)
      }
    }
    const onTouchEnd = () => {
      handleEnd()
    }

    el.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('touchend', onTouchEnd)

    frameId = requestAnimationFrame(updatePhysics)
    el.style.cursor = 'grab'
    el.style.transformOrigin = '50% 50%'

    return () => {
      cancelAnimationFrame(frameId)
      if (el) {
        el.removeEventListener('mousedown', onMouseDown)
        el.removeEventListener('touchstart', onTouchStart)
      }
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('touchend', onTouchEnd)
    }
  }, [])

  return { titleRef, frameHeight }
}
