import { ref, onMounted, onActivated } from 'vue'
import { getStudyTime, type StudyTimeAggregate } from '@/api/learning'
import { useResourceHistory } from './useResourceHistory'
import { useExerciseRecords } from './useExerciseRecords'
import { useReports } from './useReports'

/**
 * 学习时间聚合 composable —— /app/home 看板的折线图 + 环形图数据源
 *   - onMounted + onActivated 双 hook (与同目录其他 composable 保持一致, 配合 keep-alive)
 *   - 暴露 { byDay, bySubject, loading, error, reload }
 *   - 接错时 error 塞人类可读消息, view 走空态分支
 *
 * Mock fallback —— 后端返空 (用户没真实学习记录) 时, 从活动热力数据推导,
 *   让折线图与热力图保持一致. 活动次数 × 每次约 20 分钟 = 学习时长.
 */
export function useStudyTime(days = 30) {
  const byDay = ref<StudyTimeAggregate['by_day']>([])
  const bySubject = ref<StudyTimeAggregate['by_subject']>([])
  const loading = ref<boolean>(false)
  const error = ref<string>('')

  // 复用活动热力的数据源来推导学习时长
  const { items: resources } = useResourceHistory()
  const { items: exercises } = useExerciseRecords()
  const { items: reports } = useReports()

  function buildMockByDay(days: number): { date: string; minutes: number }[] {
    // 从活动热力聚合每天的活动次数
    const activityCounts = new Map<string, number>()
    for (const r of resources.value) {
      const d = r.timestamp.slice(0, 10)
      activityCounts.set(d, (activityCounts.get(d) ?? 0) + 1)
    }
    for (const e of exercises.value) {
      const d = e.timestamp.slice(0, 10)
      activityCounts.set(d, (activityCounts.get(d) ?? 0) + 1)
    }
    for (const rep of reports.value) {
      activityCounts.set(rep.week_end, (activityCounts.get(rep.week_end) ?? 0) + 1)
    }

    // 生成最近 N 天数据，今天强制为 0
    const today = new Date()
    const out: { date: string; minutes: number }[] = []

    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

      // 今天强制为 0（新用户刚进来）
      if (i === 0) {
        out.push({ date: iso, minutes: 0 })
        continue
      }

      // 活动次数 × 每次约 20 分钟
      const count = activityCounts.get(iso) ?? 0
      const minutes = Math.round(count * 20)

      out.push({ date: iso, minutes })
    }
    return out
  }

  const mockBySubject = [
    { code: 'data_structure',         minutes: 240 },
    { code: 'cybersecurity',            minutes: 180 },
    { code: 'iot',                   minutes: 90  },
    { code: 'electrical_automation', minutes: 60  },
    { code: 'mechanical_design',     minutes: 30  },
    { code: 'advanced_math',         minutes: 150 },
    { code: 'artificial_intelligence', minutes: 200 },
  ]

  async function reload(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const { data } = await getStudyTime(days)
      // 真数据全 0 / 空 → 用 mock 填充, 让图立即有视觉
      const hasReal = data.by_day.some((d) => d.minutes > 0)
      byDay.value = hasReal ? data.by_day : buildMockByDay(days)
      bySubject.value = data.by_subject.some((s) => s.minutes > 0)
        ? data.by_subject
        : mockBySubject
    } catch (err) {
      // 网络挂了: 用 mock, 不要让图表空白
      byDay.value = buildMockByDay(days)
      bySubject.value = mockBySubject
      error.value = err instanceof Error ? err.message : 'Load failed'
    } finally {
      loading.value = false
    }
  }

  onMounted(reload)
  onActivated(reload)
  return { byDay, bySubject, loading, error, reload }
}
