import { TransactionCorrectionPayload } from "@/types/api"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"  // Fallback for development only

interface FetchOptions extends RequestInit {
  requireAuth?: boolean
}


const CSRF_SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"])

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()!.split(";").shift() || null
  return null
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

  const method = (fetchOptions.method || "GET").toUpperCase()
  if (!CSRF_SAFE_METHODS.has(method)) {
    const csrfToken = getCookie("csrftoken")
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken
    }
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
    list: (params?: { category?: string; is_expense?: boolean; date_from?: string; date_to?: string; page?: number; size?: number }) => {
      const searchParams = new URLSearchParams()
      if (params?.category) searchParams.append("category", params.category)
      if (typeof params?.is_expense === "boolean") searchParams.append("is_expense", String(params.is_expense))
      if (params?.date_from) searchParams.append("date_from", params.date_from)
      if (params?.date_to) searchParams.append("date_to", params.date_to)
      if (params?.page) searchParams.append("page", params.page.toString())
      if (params?.size) searchParams.append("size", params.size.toString())
      const query = searchParams.toString()
      return apiClient(`/transactions${query ? `?${query}` : ""}`)
    },
    getById: (id: string) => apiClient(`/transactions/${id}`),
    summary: () => apiClient("/transactions/summary"),
    enrichBulk: (payload?: { max_transactions?: number; worker_count?: number; enrich_all?: boolean }) =>
      apiClient("/transactions/enrich", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    enrich: (id: string) => apiClient(`/transactions/${id}/enrich`, { method: "POST" }),
    correct: (id: string, payload: TransactionCorrectionPayload) =>
      apiClient(`/transactions/${id}/correction`, { method: "PATCH", body: JSON.stringify(payload) }),

    analyticsQuery: (params?: {
      date_from?: string
      date_to?: string
      is_expense?: boolean
      category?: string
      label?: string
      label_match?: "exact" | "contains" | "icontains"
      merchant?: string
      merchant_match?: "exact" | "contains" | "icontains"
      group_by?: "none" | "day" | "month" | "year" | "category" | "merchant" | "label"
      limit?: number
    }) => {
      const searchParams = new URLSearchParams()
      if (params?.date_from) searchParams.append("date_from", params.date_from)
      if (params?.date_to) searchParams.append("date_to", params.date_to)
      if (typeof params?.is_expense === "boolean") searchParams.append("is_expense", String(params.is_expense))
      if (params?.category) searchParams.append("category", params.category)
      if (params?.label) searchParams.append("label", params.label)
      if (params?.label_match) searchParams.append("label_match", params.label_match)
      if (params?.merchant) searchParams.append("merchant", params.merchant)
      if (params?.merchant_match) searchParams.append("merchant_match", params.merchant_match)
      if (params?.group_by) searchParams.append("group_by", params.group_by)
      if (typeof params?.limit === "number") searchParams.append("limit", String(params.limit))
      const query = searchParams.toString()
      return apiClient(`/transactions/analytics/query${query ? `?${query}` : ""}`)
    },
  },

  // Recurring
  recurring: {
    list: () => apiClient("/recurring"),
    upcoming: () => apiClient("/recurring/upcoming"),
    detect: () => apiClient("/recurring/detect", { method: "POST" }),
    delete: (id: string) => apiClient(`/recurring/${id}`, { method: "DELETE" }),
    summary: () => apiClient("/recurring/stats/summary"),
  },

  // Credentials
  credentials: {
    list: () => apiClient("/credentials"),
    create: (data: { bank_name: string; bank_label?: string; bank_website?: string; login: string; password: string }) =>
      apiClient("/credentials", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: { bank_name?: string; bank_label?: string; bank_website?: string; login?: string; password?: string }) =>
      apiClient(`/credentials/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => apiClient(`/credentials/${id}`, { method: "DELETE" }),
    sync: (id: string, params?: { days_back?: number }) =>
      apiClient(`/credentials/${id}/sync`, {
        method: "POST",
        body: JSON.stringify({ days_back: params?.days_back }),
      }),
  },

  // Accounts
  accounts: {
    list: () => apiClient("/accounts"),
    summary: () => apiClient("/accounts/summary"),
    getById: (id: string) => apiClient(`/accounts/${id}`),
  },

  // MCP tokens
  mcp: {
    tokens: () => apiClient("/users/mcp/tokens"),
    createToken: (label: string) =>
      apiClient("/users/mcp/tokens", { method: "POST", body: JSON.stringify({ label }) }),
    revokeToken: (id: string) =>
      apiClient(`/users/mcp/tokens/${id}`, { method: "DELETE" }),
    renameToken: (id: string, label: string) =>
      apiClient(`/users/mcp/tokens/${id}`, { method: "PATCH", body: JSON.stringify({ label }) }),
    approveConsent: (params: {
      client_id: string
      redirect_uri: string
      state: string
      code_challenge: string
      code_challenge_method: string
    }) => apiClient("/mcp/oauth/approve", { method: "POST", body: JSON.stringify(params) }),
  },
}
