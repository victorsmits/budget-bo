import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { apiClient } from "@/lib/api"

export interface McpOAuthClient {
  client_id: string
  client_name: string
}

export interface McpToken {
  id: string
  label: string
  is_active: boolean
  created_at: string
  last_used_at: string | null
  oauth_client: McpOAuthClient | null
  /** Only present right after creation */
  token?: string
}

export function useMcpTokens() {
  return useQuery<McpToken[]>({
    queryKey: ["mcp-tokens"],
    queryFn: () => apiClient("/users/mcp/tokens"),
    staleTime: 60_000,
  })
}

export function useCreateMcpToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (label: string) =>
      apiClient("/users/mcp/tokens", {
        method: "POST",
        body: JSON.stringify({ label }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mcp-tokens"] })
    },
    onError: () => toast.error("Impossible de créer le token"),
  })
}

export function useRevokeMcpToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient(`/users/mcp/tokens/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Token révoqué")
      qc.invalidateQueries({ queryKey: ["mcp-tokens"] })
    },
    onError: () => toast.error("Impossible de révoquer le token"),
  })
}

export function useRenameMcpToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, label }: { id: string; label: string }) =>
      apiClient(`/users/mcp/tokens/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      }),
    onSuccess: () => {
      toast.success("Token mis à jour")
      qc.invalidateQueries({ queryKey: ["mcp-tokens"] })
    },
    onError: () => toast.error("Impossible de mettre à jour le token"),
  })
}
