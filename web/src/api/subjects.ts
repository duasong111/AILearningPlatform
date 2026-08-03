import http from './http'
import { ENDPOINTS } from './endpoints'
import type { MySubject, SubjectChoice } from '@/types/response'

// ============================================================
// 学科 API

// 与 backend/users/models.py:34-42 的 Subject.SUBJECT_CHOICES 严格对齐
// 显示名也从后端搬过来, 这样不联网也能正确渲染卡片
export const SUBJECT_CHOICES: readonly SubjectChoice[] = [
  { code: 'data_structure', name: '数据结构' },
  { code: 'cybersecurity', name: '网络安全' },
  { code: 'iot', name: '物联网技术' },
  { code: 'electrical_automation', name: 'Python 编程' },
  { code: 'mechanical_design', name: '操作系统' },
  { code: 'advanced_math', name: '软件工程' },
  { code: 'artificial_intelligence', name: '人工智能' },
] as const

// 反查表: code → 显示名 (CourseCatalog / MyCourses 都要用)
export function getSubjectDisplayName(code: string): string {
  return SUBJECT_CHOICES.find((c) => c.code === code)?.name ?? code
}

// GET /api/subjects/  → 7 门预定义 (NOT 用户已选)
export function listSubjectChoices(): Promise<{ data: { subjects: SubjectChoice[] } }> {
  return http.get(ENDPOINTS.SUBJECTS)
}

// GET /api/subjects/mine/  →  当前用户已选过的学科 (含 id、display_name)
//   后端 SubjectViewSet.mine (line 194 of users/views.py) — @action(detail=False, url_path='mine')
//   返 { subjects: SubjectSerializer.data }
//   解包成 MySubject[] 让上层 store 接口不变
export async function listMySubjects(): Promise<{ data: MySubject[] }> {
  const { data } = await http.get<{ subjects: MySubject[] }>(`${ENDPOINTS.SUBJECTS}mine/`)
  return { data: data.subjects }
}

export function addSubject(code: string): Promise<{ data: MySubject }> {
  return http.post(ENDPOINTS.SUBJECTS, { name: code })
}

export function removeSubject(id: number): Promise<{ data: void }> {
  return http.delete(`${ENDPOINTS.SUBJECTS}${id}/`)
}

export default {
  SUBJECT_CHOICES,
  getSubjectDisplayName,
  listSubjectChoices,
  listMySubjects,
  addSubject,
  removeSubject,
}
