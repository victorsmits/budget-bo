import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { RecurringExpense, RecurringStats, PaginatedResponse } from "@/types/api"

// Types exportés depuis @/types/api
export type { RecurringExpense, RecurringStats } from "@/types/api"

// Hooks
export function useRecurringExpenses() {
  return useQuery({
    queryKey: ["recurring"],
    queryFn: () => api.recurring.list(),
    select: (data) => {
      if (data && typeof data === 'object' && 'items' in data) {
        return (data as PaginatedResponse<RecurringExpense>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useUpcomingRecurring(daysAhead: number = 30) {
  return useQuery({
    queryKey: ["recurring", "upcoming", daysAhead],
    queryFn: () => api.recurring.upcoming(daysAhead),
    select: (data) => {
      if (data && typeof data === 'object' && 'items' in data) {
        return (data as PaginatedResponse<RecurringExpense>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecurringStats() {
  return useQuery({
    queryKey: ["recurring", "stats"],
    queryFn: () => api.recurring.stats(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

export function useDetectRecurring() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (monthsBack?: number) => {
      const response = await api.recurring.detect(monthsBack)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Détection des dépenses récurrentes réussie")
    },
    onError: (error) => {
      console.error("Detection failed:", error)
      toast.error("Échec de la détection des dépenses récurrentes")
    },
  })
}
