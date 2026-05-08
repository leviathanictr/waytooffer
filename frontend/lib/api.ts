import axios from 'axios'
import { getAccessToken, getRefreshToken, saveTokens, clearTokens } from './auth'
import type { Profile, Session, Resume, ResumeListItem } from './types'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
})

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401: try to refresh token
let refreshing = false
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !refreshing) {
      refreshing = true
      const refresh = getRefreshToken()
      if (refresh) {
        try {
          const { data } = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/refresh`,
            { refresh_token: refresh }
          )
          saveTokens(data.access_token, refresh)
          error.config.headers.Authorization = `Bearer ${data.access_token}`
          refreshing = false
          return api.request(error.config)
        } catch {
          clearTokens()
          if (typeof window !== 'undefined') window.location.href = '/login'
        }
      } else {
        clearTokens()
        if (typeof window !== 'undefined') window.location.href = '/login'
      }
      refreshing = false
    }
    return Promise.reject(error)
  }
)

// Auth endpoints
export const auth = {
  register: (data: { phone: string; email: string; password: string; password_confirm: string }) =>
    api.post<{ user_id: string; needs_verification: boolean }>('/auth/register', data),

  login: (data: { login: string; password: string }) =>
    api.post<{ access_token: string; refresh_token: string }>('/auth/login', data),

  verifyEmail: (data: { user_id: string; code: string }) =>
    api.post<{ success: boolean; message: string }>('/auth/verify-email', data),

  verifyPhone: (data: { user_id: string; code: string }) =>
    api.post<{ success: boolean; message: string }>('/auth/verify-phone', data),

  resendVerification: (data: { user_id: string; type: 'email' | 'phone' }) =>
    api.post('/auth/resend-verification', data),

  changePassword: (data: { old_password: string; new_password: string; new_password_confirm: string }) =>
    api.post('/auth/change-password', data),

  changeEmail: (data: { new_email: string; password: string }) =>
    api.post('/auth/change-email', data),

  changePhone: (data: { new_phone: string; password: string }) =>
    api.post('/auth/change-phone', data),
}

// Profile
export const profile = {
  get: () => api.get<Profile>('/profile'),
  update: (data: Profile) => api.put<Profile>('/profile', data),
}

// Session
export const session = {
  create: (data: { vacancy_url?: string; vacancy_text?: string }) =>
    api.post<Session>('/session', data),

  sendMessage: (sessionId: string, text: string) =>
    api.post<{ reply: string; is_complete: boolean }>(`/session/${sessionId}/message`, { text }),

  generate: (sessionId: string) =>
    api.post<Resume>(`/session/${sessionId}/generate`),
}

// Resume
export const resume = {
  list: () => api.get<ResumeListItem[]>('/resume'),
  get: (id: string) => api.get<Resume>(`/resume/${id}`),
  pdfUrl: (id: string) => `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/resume/${id}/pdf`,
}

export default api
