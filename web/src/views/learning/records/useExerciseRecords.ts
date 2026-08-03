import { ref, onMounted, onActivated } from 'vue'
import { listExerciseRecords } from '@/api/learning'
import type { ExerciseRecord } from '@/types/learning'

/**
 * 习题记录 list composable —— 与 useResourceHistory 同模式
 *   onMounted + onActivated 双 hook (配合 <keep-alive>)
 */
export function useExerciseRecords() {
  const items = ref<ExerciseRecord[]>([])
  const loading = ref<boolean>(false)
  const error = ref<string>('')

  async function reload(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const { data } = await listExerciseRecords()
      items.value = data.items
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Load failed'
    } finally {
      loading.value = false
    }
  }

  onMounted(reload)
  onActivated(reload)
  return { items, loading, error, reload }
}
