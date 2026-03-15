import type { Metadata } from 'next'

import { Toaster } from '@/components/ui/toaster'

import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Budget Bo - Gestion de Dépenses',
  description: 'SaaS Spending Tracker avec synchronisation bancaire et IA',
}

interface RootLayoutProps {
  children: React.ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang='fr' suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  )
}
