import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export interface BankAccount {
  id: string
  user_id: string
  credential_id: string
  account_id: string
  account_label: string
  account_type: string
  balance: number
  currency: string
  created_at: string
  updated_at: string
  last_sync_at: string
}

export interface AccountsSummary {
  total_accounts: number
  total_balance: number
  currency: string
}

export function useBankAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.accounts.list(),
    staleTime: 60 * 1000, // 1 minute
  })
}

export function useBankAccountsSummary() {
  return useQuery({
    queryKey: ["accounts", "summary"],
    queryFn: () => api.accounts.summary(),
    staleTime: 60 * 1000, // 1 minute
  })
}
