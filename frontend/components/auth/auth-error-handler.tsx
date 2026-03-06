"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

export function AuthErrorHandler({ error }: { error?: Error }) {
  const router = useRouter()

  useEffect(() => {
    if (error?.message.includes("401")) {
      router.push("/login")
    }
  }, [error, router])

  return null
}
