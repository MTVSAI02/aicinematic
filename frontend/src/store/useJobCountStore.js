import { create } from 'zustand'

// 현재 폴링 중인 job 개수 추적. pollJob 시작/종료 시 increment/decrement.
// useNotifications 가 이 값을 보고 폴링 여부를 결정한다.
const useJobCountStore = create((set) => ({
  activeJobCount: 0,
  increment: () => set((s) => ({ activeJobCount: s.activeJobCount + 1 })),
  decrement: () => set((s) => ({ activeJobCount: Math.max(0, s.activeJobCount - 1) })),
}))

export default useJobCountStore
