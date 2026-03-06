"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "./api"

interface User {
  id: string
  email: string
  display_name?: string
  profile_picture?: string
}

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

export function useAuth(): AuthState {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.auth.me(),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !error && !!user,
  }
}

export async function logout(): Promise<void> {
  await api.auth.logout()
  window.location.href = "/login"
}

// Export du hook de déconnexion pour les composants
export { useLogout } from "@/hooks/api/useAuth"
