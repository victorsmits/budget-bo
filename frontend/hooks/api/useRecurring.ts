import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import {
  PaginatedResponse,
  RecurringExpense,
  RecurringExpenseDetail,
  RecurringStats,
} from "@/types/api"

export function useRecurringExpenses() {
  return useQuery({
    queryKey: ["recurring"],
    queryFn: () => api.recurring.list(),
    select: (data) => {
      if (data && typeof data === "object" && "items" in data) {
        return (data as PaginatedResponse<RecurringExpense>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecurringDetail(expenseId?: string) {
  return useQuery({
    queryKey: ["recurring", "detail", expenseId],
    queryFn: () => {
      if (!expenseId) return Promise.resolve(null)
      return api.recurring.get(expenseId) as Promise<RecurringExpenseDetail>
    },
    enabled: Boolean(expenseId),
  })
}

export function useUpcomingRecurring(daysAhead = 30) {
  return useQuery({
    queryKey: ["recurring", "upcoming", daysAhead],
    queryFn: () => api.recurring.upcoming(daysAhead),
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecurringStats() {
  return useQuery({
    queryKey: ["recurring", "stats"],
    queryFn: () => api.recurring.stats(),
    staleTime: 10 * 60 * 1000,
  })
}

export function useDetectRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (monthsBack?: number) => api.recurring.detect(monthsBack),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Détection des dépenses récurrentes réussie")
    },
    onError: () => toast.error("Échec de la détection des dépenses récurrentes"),
  })
}

export function useCancelRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (expenseId: string) => api.recurring.cancel(expenseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Récurrence annulée")
    },
    onError: () => toast.error("Impossible d'annuler la récurrence"),
  })
}

export function useRenameRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ expenseId, newName }: { expenseId: string; newName: string }) =>
      api.recurring.rename(expenseId, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Récurrence renommée")
    },
    onError: () => toast.error("Impossible de renommer la récurrence"),
  })
}

export function useDeleteRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (expenseId: string) => api.recurring.delete(expenseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Récurrence supprimée")
    },
    onError: () => toast.error("Impossible de supprimer la récurrence"),
  })
}
