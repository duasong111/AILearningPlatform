import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as subjectsApi from '@/api/subjects'
import type { MySubject } from '@/types/response'

/**
 * 用户已添加的学科 (= 课程) store —— UI 的唯一真相源
 *
 * 为什么需要这个 store?
 *   后端的 GET /api/subjects/ 返回的是固定 7 门预定义学科, 而不是 "我已添加的".
 *   (backend SubjectViewSet.list 把 queryset 覆盖掉了, 详见 api/subjects.ts:listMySubjects)
 *   所以前端必须自己维护一份 "用户已添加" 的列表, 通过持久化插件落地到 localStorage.
 *
 *   - POST /api/subjects/   → push 进 subjects (get_or_create 幂等, 重复加返回同一行)
 *   - DELETE /api/subjects/<id>/ → 从 subjects 里过滤掉
 *   - 没有 list-mine 接口的兜底: loadFromBackend() 当前返 []
 *
 *   未来后端补上 GET /api/subjects/mine/ 后,
 *   只改 api/subjects.ts 的 listMySubjects() 函数体, 本 store 一行不用动.
 *
 * 持久化:
 *   key = 'aiteach.mySubjects', pick = ['subjects'].
 *   登出时 *不* 清除 (与 userStore 解耦) —— 同设备同账号再登能直接看到已选课程.
 *   如果以后要求强对齐 backend, 在 user.logout 里手动 useMySubjectsStore().reset() 即可.
 */
export const useMySubjectsStore = defineStore(
  'mySubjects',
  () => {
    // ─── state ────────────────────────────────────────────
    const subjects = ref<MySubject[]>([])
    const loading = ref<boolean>(false)
    const lastError = ref<string>('')

    // ─── getters ──────────────────────────────────────────
    // 快速 lookup, 给 CourseCatalogView "Add / Added ✓" 用
    const ownedCodes = computed<Set<string>>(
      () => new Set(subjects.value.map((s) => s.name)),
    )
    const isOwned = (code: string): boolean => ownedCodes.value.has(code)
    const count = computed<number>(() => subjects.value.length)

    // ─── actions ──────────────────────────────────────────
    /** 后端 hydration —— 拉 GET /api/subjects/mine/ (SubjectViewSet.mine) */
    async function loadFromBackend(): Promise<void> {
      loading.value = true
      lastError.value = ''
      try {
        const { data } = await subjectsApi.listMySubjects()
        // 只在后端返非空时覆盖 (避免空 stub 把本地数据冲掉)
        if (data.length > 0) {
          subjects.value = data
        }
      } catch (err) {
        lastError.value = err instanceof Error ? err.message : 'Load failed'
      } finally {
        loading.value = false
      }
    }

    /**
     * 添加学科. backend get_or_create 幂等, 但本地数组要去重 (按 name/code).
     * 抛错给调用方, 让 view 决定 toast 文案.
     */
    async function add(code: string): Promise<MySubject> {
      const { data } = await subjectsApi.addSubject(code)
      // 去重: backend 返的可能是已存在的同一行
      const existing = subjects.value.find((s) => s.name === data.name)
      if (existing) {
        // 用 backend 返的 (可能更新过 updated_at) 替换本地老的
        Object.assign(existing, data)
        return existing
      }
      subjects.value.push(data)
      return data
    }

    async function remove(id: number): Promise<void> {
      await subjectsApi.removeSubject(id)
      subjects.value = subjects.value.filter((s) => s.id !== id)
    }

    /** 调试/测试用. 生产路径不调. */
    function reset(): void {
      subjects.value = []
      loading.value = false
      lastError.value = ''
    }

    return {
      subjects,
      loading,
      lastError,
      ownedCodes,
      isOwned,
      count,
      loadFromBackend,
      add,
      remove,
      reset,
    }
  },
  {
    persist: {
      key: 'aiteach.mySubjects',
      pick: ['subjects'],     // 只持久化 subjects, loading/error 走运行时
    },
  },
)
