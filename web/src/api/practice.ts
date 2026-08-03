import http from './http'
import { ENDPOINTS } from './endpoints'

// ────── 类型定义 ──────

export interface PracticeScene {
  title: string
  html: string
  widgetType: string
  widgetConfig: Record<string, any> | null
}

export interface PracticeSession {
  id: number
  search_query: string
  language: string
  scene_count: number
  outlines: Record<string, any>[]
  scenes: PracticeScene[]
  status: 'generating' | 'ready' | 'error'
  error_message: string
  created_at: string
  updated_at: string
}

// ────── API 函数 ──────

export function getPracticeSession(id: number) {
  return http.get<PracticeSession>(ENDPOINTS.PRACTICE_SESSION(id))
}
