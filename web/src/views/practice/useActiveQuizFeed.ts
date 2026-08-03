// ============================================================
// useActiveQuizFeed — 从后端取 "ready 队列", 自己不再 POST 生成题
//
// 设计目标:
//   1. onMounted 调用 GET /api/quiz/active-queue/?subject=&plan=.
//   2. 后端自己负责:  看到 ready 数 < 2 自动补 celery task 生成新 batch.
//   3. 前端只 next(), 不重复造题.
//   4. 切换 plan (route query 变化) 时重拉一次 (debounce 避免与 start 抢跑).
// ============================================================

import { ref, watch, onScopeDispose, type Ref } from 'vue'
import type { StructuredQuestion } from '@/api/quiz'
import http from '@/api/http'
import { ENDPOINTS } from '@/api/endpoints'

export interface QuizFeedItem {
  id: number
  task_id: string
  subject_id: number
  subject_display: string
  subject_code: string
  requested_count: number
  state: 'generating' | 'complete' | 'error'
  questions: StructuredQuestion[]
  item_progress: Record<string, { answered: boolean; correct: boolean }>
  source: 'plan' | 'normal'
  created_at: string
  completed_at: string | null
}

export interface FeedOptions {
  subjectName: Ref<string>
  planId: Ref<number | null | undefined>
}

// 多久自动重新拉一次 (毫秒). 后端 answering 完一道题会 refill,
// 这里 poll 一次只是为能看到新题.  用户不感知.
const POLL_INTERVAL_MS = 4000
// subject/plan 切换的防抖窗口: 短时间内多次变化合并为一次请求
const SWITCH_DEBOUNCE_MS = 150

export function useActiveQuizFeed(opts: FeedOptions) {
  const ready = ref<QuizFeedItem[]>([])
  const generating = ref<QuizFeedItem[]>([])
  const lastFetchAt = ref<number>(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let disposed = false

  async function fetchOnce(): Promise<void> {
    if (disposed) return
    if (!opts.subjectName.value) return
    const params: Record<string, string> = { subject: opts.subjectName.value }
    if (opts.planId.value != null) params.plan = String(opts.planId.value)
    loading.value = true
    try {
      const { data } = await http.get(ENDPOINTS.QUIZ_ACTIVE_QUEUE, { params })
      if (disposed) return
      ready.value = data.ready || []
      generating.value = data.generating || []
      lastFetchAt.value = Date.now()
      error.value = null
    } catch (e: any) {
      if (!disposed) error.value = e?.message ?? 'failed to load queue'
    } finally {
      loading.value = false
    }
  }

  // 用户答完题后再主动拉一次. 后端按需补题.
  async function refresh(): Promise<void> {
    await fetchOnce()
  }

  function start() {
    if (disposed) return
    // 取消待发的 debounce 拉取, 避免和 start 抢跑产生两个并发请求
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    fetchOnce()
    if (timer == null) {
      timer = setInterval(() => {
        fetchOnce()
      }, POLL_INTERVAL_MS)
    }
  }

  function dispose() {
    disposed = true
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  onScopeDispose(dispose)

  // subject or plan 切换时立即重拉 (debounce 后, 不等 4s 间隔)
  watch(
    () => [opts.subjectName.value, opts.planId.value],
    () => {
      ready.value = []
      generating.value = []
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        debounceTimer = null
        fetchOnce()
      }, SWITCH_DEBOUNCE_MS)
    },
  )

  return {
    ready,
    generating,
    lastFetchAt,
    loading,
    error,
    fetchOnce,
    refresh,
    start,
    dispose,
  }
}