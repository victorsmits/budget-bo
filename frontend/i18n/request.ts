import { notFound } from 'next/navigation'

import { defaultLocale, locales, type Locale } from './config'

interface RequestConfig {
  locale: Locale
  messages: Record<string, unknown>
}

type GetRequestConfig = (
  factory: (context: { locale?: string }) => Promise<RequestConfig>,
) => (context: { locale?: string }) => Promise<RequestConfig>

const getRequestConfig = (
  require('next-intl/server') as { getRequestConfig: GetRequestConfig }
).getRequestConfig

export default getRequestConfig(async ({ locale }) => {
  const resolvedLocale = (locale ?? defaultLocale) as Locale

  if (!locales.includes(resolvedLocale)) {
    notFound()
  }

  return {
    locale: resolvedLocale,
    messages: (await import(`./messages/${resolvedLocale}.json`)).default as Record<string, unknown>,
  }
})
