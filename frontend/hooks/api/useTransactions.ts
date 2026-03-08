import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import {
  PaginatedResponse,
  SummaryData,
  Transaction,
  TransactionCorrectionPayload,
  TransactionFilters,
} from "@/types/api"

// Types exportés depuis @/types/api
export type {
  Transaction,
  SummaryData,
  TransactionCorrectionPayload,
  TransactionFilters,
} from "@/types/api"

// Hooks
export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => api.transactions.list(filters || {}),
    select: (data) => {
      // Gérer les réponses paginées ou directes
      if (data && typeof data === "object" && "items" in data) {
        return (data as PaginatedResponse<Transaction>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 30 * 1000, // 30 seconds
  })
}

export function useTransactionSummary() {
  return useQuery({
    queryKey: ["transactions", "summary"],
    queryFn: () => api.transactions.summary(),
    staleTime: 60 * 1000, // 1 minute
  })
}

export function useRecentTransactions(limit: number = 5) {
  return useQuery({
    queryKey: ["transactions", "recent", limit],
    queryFn: () => api.transactions.list({ size: limit }),
    select: (data) => {
      // Gérer les réponses paginées ou directes
      if (data && typeof data === "object" && "items" in data) {
        return (data as PaginatedResponse<Transaction>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 30 * 1000,
  })
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: ["transaction", id],
    queryFn: () => api.transactions.getById(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useEnrichTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (transactionId: string) => {
      const response = await api.transactions.enrich(transactionId)
      return response
    },
    onSuccess: (_, transactionId) => {
      // Invalider la query spécifique et la liste
      queryClient.invalidateQueries({ queryKey: ["transaction", transactionId] })
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      toast.success("Transaction enrichie avec succès")
    },
    onError: (error) => {
      console.error("Enrich failed:", error)
      toast.error("Échec de l'enrichissement de la transaction")
    },
  })
}

export function useCorrectTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      transactionId,
      payload,
    }: {
      transactionId: string
      payload: TransactionCorrectionPayload
    }) => {
      const response = await api.transactions.correct(transactionId, payload)
      return response
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["transaction", variables.transactionId] })
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      toast.success("Correction enregistrée et mémorisée")
    },
    onError: (error) => {
      console.error("Correction failed:", error)
      toast.error("Impossible d'enregistrer la correction")
    },
  })
}
