import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"
import { Credential, PaginatedResponse } from "@/types/api"

// Types exportés depuis @/types/api
export type { Credential } from "@/types/api"

export interface CreateCredentialData {
  bank_name: string
  bank_label?: string
  bank_website?: string
  login: string
  password: string
}

export interface UpdateCredentialData {
  bank_name?: string
  bank_label?: string
  bank_website?: string
  login?: string
  password?: string
}

// Hooks
export function useCredentials() {
  return useQuery({
    queryKey: ["credentials"],
    queryFn: () => api.credentials.list(),
    select: (data) => {
      if (data && typeof data === 'object' && 'items' in data) {
        return (data as PaginatedResponse<Credential>).items
      }
      return Array.isArray(data) ? data : []
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useCreateCredential() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: CreateCredentialData) => api.credentials.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["credentials"] })
      toast.success("Compte bancaire ajouté avec succès")
    },
    onError: (error) => {
      console.error("Create credential failed:", error)
      toast.error("Échec de l'ajout du compte bancaire")
    },
  })
}

export function useUpdateCredential() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCredentialData }) => 
      api.credentials.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["credentials"] })
      queryClient.invalidateQueries({ queryKey: ["credential", id] })
      toast.success("Compte bancaire mis à jour")
    },
    onError: (error) => {
      console.error("Update credential failed:", error)
      toast.error("Échec de la mise à jour du compte bancaire")
    },
  })
}

export function useSyncCredential() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ credentialId, days_back }: { credentialId: string; days_back?: number }) =>
      api.credentials.sync(credentialId, { days_back }),
    onSuccess: () => {
      // Invalider toutes les queries qui pourraient être affectées
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["recurring"] })
      queryClient.invalidateQueries({ queryKey: ["credentials"] })
      toast.success("Synchronisation en cours...")
    },
    onError: (error) => {
      console.error("Sync credential failed:", error)
      toast.error("Échec de la synchronisation")
    },
  })
}

export function useDeleteCredential() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (credentialId: string) => api.credentials.delete(credentialId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["credentials"] })
      toast.success("Compte bancaire supprimé")
    },
    onError: (error) => {
      console.error("Delete credential failed:", error)
      toast.error("Échec de la suppression")
    },
  })
}
