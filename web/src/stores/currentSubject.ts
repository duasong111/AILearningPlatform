import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { SUBJECT_CHOICES } from '@/api/subjects'
import { useMySubjectsStore } from './mySubjects'
import type { SubjectCode } from '@/types/learning'

/**
 * 全局当前学科 store —— 所有页面共享
 *
 *   AppShell 顶栏的学科选择器写入此 store,
 *   GalaxyView / PracticeView / CourseDetailView 等页面读取.
 *   持久化到 localStorage, 刷新不丢失.
 */
export const useCurrentSubjectStore = defineStore(
  'currentSubject',
  () => {
    const mySubjects = useMySubjectsStore()

    const code = ref<SubjectCode>(
      (mySubjects.subjects[0]?.name as SubjectCode) ?? 'data_structure',
    )

    // 当用户添加新学科时, 如果当前选的是默认值且不在已拥有列表中, 不自动切
    // 当用户删除当前学科时, 自动切到第一个已拥有学科
    watch(
      () => mySubjects.subjects,
      (subs) => {
        if (subs.length === 0) return
        const owned = new Set(subs.map((s) => s.name))
        if (!owned.has(code.value)) {
          code.value = (subs[0]?.name as SubjectCode) ?? 'data_structure'
        }
      },
      { deep: true },
    )

    function set(newCode: SubjectCode): void {
      code.value = newCode
    }

    /** 所有学科, 已拥有的排前面 */
    function orderedCodes(): SubjectCode[] {
      const owned = new Set(mySubjects.subjects.map((s) => s.name))
      const all = SUBJECT_CHOICES.map((c) => c.code as SubjectCode)
      const yes = all.filter((c) => owned.has(c))
      const no = all.filter((c) => !owned.has(c))
      return [...yes, ...no]
    }

    return { code, set, orderedCodes }
  },
  {
    persist: {
      key: 'aiteach.currentSubject',
      pick: ['code'],
    },
  },
)
