import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { toast } from "sonner"

export function useLogout() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      // Invalider toutes les queries
      queryClient.clear()
      window.location.href = "/login"
    },
    onError: (error) => {
      console.error("Logout failed:", error)
      toast.error("Erreur lors de la déconnexion")
    },
  })
}
