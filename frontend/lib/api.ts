import { TransactionCorrectionPayload } from "@/types/api"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"  // Fallback for development only

interface FetchOptions extends RequestInit {
  requireAuth?: boolean
}

export async function apiClient(
  endpoint: string,
  options: FetchOptions = {}
): Promise<any> {
  const { requireAuth = true, ...fetchOptions } = options

  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((fetchOptions.headers as Record<string, string>) || {}),
  }

  const config: RequestInit = {
    ...fetchOptions,
    headers,
    credentials: "include",
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    // Ne pas rediriger automatiquement, laisser React Query gérer les erreurs
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  // Handle empty responses
  if (response.status === 204) {
    return null
  }

  return response.json()
}

// API endpoints
export const api = {
  // Auth
  auth: {
    me: () => apiClient("/users/me"),
    logout: () => apiClient("/auth/logout", { method: "POST" }),
  },

  // Transactions
  transactions: {
    list: (params?: { category?: string; start_date?: string; end_date?: string; page?: number; size?: number; search?: string }) => {
      const searchParams = new URLSearchParams()
      if (params?.category) searchParams.append("category", params.category)
      if (params?.start_date) searchParams.append("start_date", params.start_date)
      if (params?.end_date) searchParams.append("end_date", params.end_date)
      if (params?.page) searchParams.append("page", params.page.toString())
      if (params?.size) searchParams.append("size", params.size.toString())
      if (params?.search) searchParams.append("search", params.search)
      const query = searchParams.toString()
      return apiClient(`/transactions${query ? `?${query}` : ""}`)
    },
    getById: (id: string) => apiClient(`/transactions/${id}`),
    summary: () => apiClient("/transactions/summary"),
    enrich: (id: string) => apiClient(`/transactions/${id}/enrich`, { method: "POST" }),
    correct: (id: string, payload: TransactionCorrectionPayload) =>
      apiClient(`/transactions/${id}/correction`, { method: "PATCH", body: JSON.stringify(payload) }),
  },

  // Recurring
  recurring: {
    list: () => apiClient("/recurring"),
    upcoming: (days_ahead?: number) => apiClient(`/recurring/upcoming${days_ahead ? `?days_ahead=${days_ahead}` : ""}`),
    get: (id: string) => apiClient(`/recurring/${id}`),
    detect: (months_back?: number) =>
      apiClient("/recurring/detect", {
        method: "POST",
        body: JSON.stringify({ months_back: months_back || 6 }),
      }),
    cancel: (id: string) => apiClient(`/recurring/${id}/cancel`, { method: "POST" }),
    rename: (id: string, new_name: string) =>
      apiClient(`/recurring/${id}/rename`, {
        method: "PATCH",
        body: JSON.stringify({ new_name }),
      }),
    delete: (id: string) => apiClient(`/recurring/${id}`, { method: "DELETE" }),
    stats: () => apiClient("/recurring/stats/summary"),
  },

  // Credentials
  credentials: {
    list: () => apiClient("/credentials"),
    create: (data: { bank_name: string; bank_label?: string; bank_website?: string; login: string; password: string }) =>
      apiClient("/credentials", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: { bank_name?: string; bank_label?: string; bank_website?: string; login?: string; password?: string }) =>
      apiClient(`/credentials/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => apiClient(`/credentials/${id}`, { method: "DELETE" }),
    sync: (id: string) => apiClient(`/credentials/${id}/sync`, { method: "POST" }),
  },

  // Accounts
  accounts: {
    list: () => apiClient("/accounts"),
    summary: () => apiClient("/accounts/summary"),
    getById: (id: string) => apiClient(`/accounts/${id}`),
  },
}
