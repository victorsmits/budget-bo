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
  merchant_name?: string | null
  amount: number
  date: string
  category: string
  is_expense: boolean
  is_recurring: boolean
  currency?: string
  ai_confidence?: number | null
}

export interface TransactionCorrectionPayload {
  cleaned_label?: string | null
  merchant_name?: string | null
  category?: string
  is_expense?: boolean
}

// Types pour les dépenses récurrentes
export interface RecurringExpense {
  id: string
  user_id: string
  pattern_name: string
  pattern: string
  average_amount: number
  amount_variation_pct: number
  frequency_days: number | null
  day_of_month: number | null
  day_of_week: number | null
  next_expected_date: string | null
  is_active: boolean
  confidence_score: number
  matched_transaction_count: number
  first_seen_date: string
  last_seen_date: string
  created_at: string
}


// Types pour le résumé
export interface SummaryData {
  total_expenses: number
  total_income: number
  by_category: { category: string; total: number }[]
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
  is_expense?: boolean
  date_from?: string
  date_to?: string
  page?: number
  size?: number
}

export interface RecurringSummary {
  active_count: number
  estimated_monthly_total: number
}
