// 相对时间格式化 —— 给学习记录 Tab 的左侧时间戳用
//   不引第三方 (dayjs / date-fns), ~30 行手写够用了
//   阈值: 60s / 60min / 24h / 30d 之后退回 yyyy-mm-dd
export function formatRelative(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return iso

  const diff = Date.now() - t                       // ms
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return 'just now'

  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`

  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`

  const day = Math.floor(hr / 24)
  if (day < 30) return `${day}d ago`

  // ≥ 30 天 → yyyy-mm-dd
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 周报 header 用: "Jun 1 → Jun 7"
export function formatWeekRange(startIso: string, endIso: string): string {
  const fmt = (iso: string) => {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return `${MONTHS[d.getMonth()]} ${d.getDate()}`
  }
  return `${fmt(startIso)} → ${fmt(endIso)}`
}
