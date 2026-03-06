// Types pour les réponses de l'API
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface ApiResponse<T> {
  data: T
  success?: boolean
  message?: string
}

// Types pour les transactions
export interface Transaction {
  id: string
  cleaned_label: string | null
  raw_label: string
  amount: number
  date: string
  category: string
  is_expense: boolean
  is_recurring: boolean
}

// Types pour les dépenses récurrentes
export interface RecurringExpense {
  id: string
  pattern_name: string
  average_amount: number
  next_expected_date: string | null
}

// Types pour le résumé
export interface SummaryData {
  period: { start: string; end: string }
  total_expenses: number
  total_income: number
  net: number
  by_category: { category: string; total: number; count: number }[]
}

// Types pour les identifiants bancaires
export interface Credential {
  id: string
  bank_name: string
  bank_label?: string
  bank_website?: string
  login: string
  last_sync?: string
  is_active: boolean
}

// Types additionnels pour les filtres et stats
export interface TransactionFilters {
  category?: string
  start_date?: string
  end_date?: string
  page?: number
  size?: number
}

export interface RecurringStats {
  total_patterns: number
  total_monthly_amount: number
  categories: { category: string; count: number; total_amount: number }[]
}
