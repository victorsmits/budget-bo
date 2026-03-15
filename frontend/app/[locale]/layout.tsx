import type { Metadata, Viewport } from 'next'
import { notFound } from 'next/navigation'

import { defaultLocale, locales, type Locale } from '@/i18n/config'

interface LocaleLayoutProps {
  children: React.ReactNode
  params: {
    locale: string
  }
}

export const metadata: Metadata = {
  title: 'Budget Bo - Gestion de Dépenses',
  description: 'SaaS Spending Tracker avec synchronisation bancaire et IA',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Budget Bo',
  },
  icons: {
    apple: '/icon-192.png',
  },
}

export const viewport: Viewport = {
  themeColor: '#6C63FF',
}

export default function LocaleLayout({ children, params }: LocaleLayoutProps) {
  const localeCandidate = params.locale
  const locale = (localeCandidate || defaultLocale) as Locale

  if (!locales.includes(locale)) {
    notFound()
  }

  return <>{children}</>
}
