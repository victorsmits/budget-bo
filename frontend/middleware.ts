import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

import { defaultLocale, locales } from './i18n/config'

const publicRoutes = ['/login', '/api/auth/callback', '/api/auth/login'] as const

const stripLocalePrefix = (pathname: string): string => {
  const segments = pathname.split('/').filter(Boolean)
  const firstSegment = segments[0]

  if (firstSegment && locales.includes(firstSegment as (typeof locales)[number])) {
    const withoutLocale = `/${segments.slice(1).join('/')}`
    return withoutLocale === '/' ? '/' : withoutLocale
  }

  return pathname
}

const resolveLocaleFromPathname = (pathname: string): (typeof locales)[number] => {
  const localeCandidate = pathname.split('/').filter(Boolean)[0]

  if (localeCandidate && locales.includes(localeCandidate as (typeof locales)[number])) {
    return localeCandidate as (typeof locales)[number]
  }

  return defaultLocale
}

export function middleware(request: NextRequest): NextResponse {
  const pathname = request.nextUrl.pathname
  const normalizedPathname = stripLocalePrefix(pathname)

  if (publicRoutes.some((route) => normalizedPathname.startsWith(route))) {
    return NextResponse.next()
  }

  const session = request.cookies.get('sessionid')

  if (!session) {
    const locale = resolveLocaleFromPathname(pathname)
    const loginPath = locale === defaultLocale ? '/login' : `/${locale}/login`
    return NextResponse.redirect(new URL(loginPath, request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
}
