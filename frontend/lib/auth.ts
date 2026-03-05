"use client"

import { useState, useEffect } from "react"

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
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  })

  useEffect(() => {
    // Check auth status from backend
    fetch("/api/auth/me", { credentials: "include" })
      .then((res) => {
        if (res.ok) {
          return res.json()
        }
        throw new Error("Not authenticated")
      })
      .then((user) => {
        setState({
          user,
          isLoading: false,
          isAuthenticated: true,
        })
      })
      .catch(() => {
        setState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
        })
      })
  }, [])

  return state
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  })
  window.location.href = "/login"
}
