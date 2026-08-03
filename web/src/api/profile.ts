import http from './http'
import { ENDPOINTS } from './endpoints'
import type { UserProfile } from '@/types/response'

export function getProfile(subject: string): Promise<{ data: UserProfile }> {
  return http.get(ENDPOINTS.PROFILE, { params: { subject } })
}

export function updateProfile(
  subject: string,
  payload: Partial<UserProfile>,
): Promise<{ data: UserProfile }> {
  return http.patch(ENDPOINTS.PROFILE, payload, { params: { subject } })
}

export function completeProfile(subject: string): Promise<{ data: UserProfile }> {
  return http.post(ENDPOINTS.PROFILE_COMPLETE, { subject })
}

export default {
  getProfile,
  updateProfile,
  completeProfile,
}
