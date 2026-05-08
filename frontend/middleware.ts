import { NextRequest, NextResponse } from 'next/server'

const PROTECTED_PATHS = ['/', '/history', '/settings']
const AUTH_PATHS = ['/login', '/register']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasSession = request.cookies.get('wto_has_session')?.value === '1'

  const isProtected = PROTECTED_PATHS.some(p =>
    pathname === p || pathname.startsWith(p + '/')
  )
  const isAuthPath = AUTH_PATHS.some(p => pathname.startsWith(p))

  if (isProtected && !hasSession) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isAuthPath && hasSession) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/', '/history', '/settings', '/login', '/register'],
}
