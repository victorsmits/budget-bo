// Export centralisé des hooks API
export * from './useTransactions'
export * from './useRecurring'
export * from './useCredentials'

// Hook combiné pour le dashboard
import { useTransactionSummary, useRecentTransactions } from './useTransactions'
import { useUpcomingRecurring } from './useRecurring'
import { useCredentials, useSyncCredential } from './useCredentials'
import { useQuery } from '@tanstack/react-query'

export function useDashboardData() {
  const summary = useTransactionSummary()
  const recentTransactions = useRecentTransactions(5)
  const upcomingRecurring = useUpcomingRecurring()
  const credentials = useCredentials()
  const syncCredential = useSyncCredential()

  const isLoading = summary.isLoading || recentTransactions.isLoading || upcomingRecurring.isLoading
  const error = summary.error

  return {
    summary: summary.data,
    recentTransactions: recentTransactions.data,
    upcomingRecurring: upcomingRecurring.data,
    credentials: credentials.data,
    isLoading,
    error,
    syncCredential,
    refetch: () => {
      summary.refetch()
      recentTransactions.refetch()
      upcomingRecurring.refetch()
      credentials.refetch()
    }
  }
}
