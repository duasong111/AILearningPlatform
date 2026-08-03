import { ref, onMounted, onActivated } from 'vue'
import { listResourceHistory } from '@/api/learning'
import type { ResourceHistoryItem } from '@/types/learning'

/**
 * 资源历史 list composable
 *   - onMounted + onActivated 双 hook: 首次 mount 触发, keep-alive 缓存命中 (用户
 *     从其他 tab 切回) 也触发. 不加 onActivated 会"切回有数据但不再 fetch" 的
 *     "假正常"症状, 配合 <keep-alive> 包裹是必须的.
 *   - 暴露 { items, loading, error, reload } 给 Tab 用
 *   - 接错 (network / 5xx) 时把人类可读消息塞 error, view 自己决定怎么展示
 */
export function useResourceHistory() {
  const items = ref<ResourceHistoryItem[]>([])
  const loading = ref<boolean>(false)
  const error = ref<string>('')

  async function reload(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const { data } = await listResourceHistory()
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
