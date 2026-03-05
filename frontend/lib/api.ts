const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

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
    if (response.status === 401) {
      // Redirect to login on auth error
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
    }
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
    me: () => apiClient("/auth/me"),
    logout: () => apiClient("/auth/logout", { method: "POST" }),
  },

  // Transactions
  transactions: {
    list: (params?: { category?: string; start_date?: string; end_date?: string; limit?: number }) => {
      const searchParams = new URLSearchParams()
      if (params?.category) searchParams.append("category", params.category)
      if (params?.start_date) searchParams.append("start_date", params.start_date)
      if (params?.end_date) searchParams.append("end_date", params.end_date)
      if (params?.limit) searchParams.append("limit", params.limit.toString())
      const query = searchParams.toString()
      return apiClient(`/transactions${query ? `?${query}` : ""}`)
    },
    summary: () => apiClient("/transactions/summary"),
  },

  // Recurring
  recurring: {
    list: () => apiClient("/recurring"),
    upcoming: (days_ahead?: number) => apiClient(`/recurring/upcoming${days_ahead ? `?days_ahead=${days_ahead}` : ""}`),
    detect: (months_back?: number) => apiClient("/recurring/detect", {
      method: "POST",
      body: JSON.stringify({ months_back: months_back || 6 }),
    }),
    stats: () => apiClient("/recurring/stats/summary"),
  },

  // Credentials
  credentials: {
    list: () => apiClient("/credentials"),
    create: (data: { bank_name: string; bank_label?: string; login: string; password: string }) =>
      apiClient("/credentials", { method: "POST", body: JSON.stringify(data) }),
    sync: (id: string) => apiClient(`/credentials/${id}/sync`, { method: "POST" }),
  },
}
