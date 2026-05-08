const ACCESS_KEY = 'wto_access'
const REFRESH_KEY = 'wto_refresh'
const USER_ID_KEY = 'wto_user_id'

export function saveTokens(access: string, refresh: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
  document.cookie = `wto_has_session=1; path=/; max-age=${60 * 60 * 24 * 30}`
}

export function saveUserId(userId: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(USER_ID_KEY, userId)
}

export function getUserId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(USER_ID_KEY)
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(REFRESH_KEY)
}

export function clearTokens() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_ID_KEY)
  document.cookie = 'wto_has_session=; path=/; max-age=0'
}

export function isAuthenticated(): boolean {
  return !!getAccessToken()
}
