import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { PaginatedResponse, RecurringExpense, RecurringSummary } from "@/types/api"

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

export function useUpcomingRecurring() {
  return useQuery({
    queryKey: ["recurring", "upcoming"],
    queryFn: () => api.recurring.upcoming(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecurringSummary() {
  return useQuery({
    queryKey: ["recurring", "summary"],
    queryFn: () => api.recurring.summary() as Promise<RecurringSummary>,
    staleTime: 10 * 60 * 1000,
  })
}

export function useDetectRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => api.recurring.detect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      toast.success("Détection des dépenses récurrentes réussie")
    },
    onError: () => toast.error("Échec de la détection des dépenses récurrentes"),
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
