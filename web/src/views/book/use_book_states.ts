import { ref, watch } from 'vue'
import type { BookStatus } from '@/data/books'
import { openReadingSession } from '@/api/learning'

const LS_KEY = 'aiteach.bookshelf'

interface BookState {
  status: BookStatus
  addedAt: string
  lastReadAt: string | null
  // 后端 BookReadingSession.id —— best-effort 上报时存, 关书/心跳时用
  activeReadingSessionId?: number | null
}

type StatesMap = Record<string, BookState>

function loadFromStorage(): StatesMap {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? (JSON.parse(raw) as StatesMap) : {}
  } catch {
    return {}
  }
}

export function useBookStates() {
  const states = ref<StatesMap>(loadFromStorage())

  watch(states, (val) => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(val))
    } catch {
      // ignore write errors
    }
  })

  function getStatus(id: string): BookStatus {
    return states.value[id]?.status ?? 'unread'
  }

  function getLastRead(id: string): string | null {
    return states.value[id]?.lastReadAt ?? null
  }

  /**
   * 打开书 —— 同步:
   *   1) 写 localStorage (status/lastReadAt 立刻反映到 UI)
   *   2) best-effort 调 `openReadingSession` 上报后端 (失败不阻塞 UI)
   * BookShelf.vue:181-183 的 `openReader()` 调 `openBook(book.id)`, 不需要 await.
   * 改成 async 是为了支持后续心跳/关闭的扩展 (BookReadingSession.id 存在 states[id].activeReadingSessionId)
   */
  async function openBook(id: string): Promise<void> {
    const now = new Date().toISOString()
    const existing = states.value[id]
    states.value = {
      ...states.value,
      [id]: existing
        ? { ...existing, status: existing.status === 'unread' ? 'reading' : existing.status, lastReadAt: now }
        : { status: 'reading', addedAt: now, lastReadAt: now },
    }
    // best-effort 上报后端
    try {
      const { data } = await openReadingSession(id)
      // 把后端返回的 reading session id 存进 localStorage, 关书/心跳用得上
      const cur = states.value[id]
      if (cur && data?.id) {
        states.value = { ...states.value, [id]: { ...cur, activeReadingSessionId: data.id } }
      }
    } catch {
      // 静默失败, 不阻塞 UI
    }
  }

  function setStatus(id: string, status: Exclude<BookStatus, 'unread'>): void {
    const now = new Date().toISOString()
    const existing = states.value[id]
    states.value = {
      ...states.value,
      [id]: existing
        ? { ...existing, status, lastReadAt: now }
        : { status, addedAt: now, lastReadAt: now },
    }
  }

  return { states, getStatus, getLastRead, openBook, setStatus }
}
