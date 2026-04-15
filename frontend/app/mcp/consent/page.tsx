"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useState } from "react"
import { BotMessageSquare, Check, Database, LayoutDashboard, Repeat2, ShieldCheck, X } from "lucide-react"
import { toast } from "sonner"

import { useAuth } from "@/lib/auth"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

const MCP_SCOPES = [
  { icon: LayoutDashboard, label: "Voir vos comptes bancaires et soldes" },
  { icon: Database, label: "Lire vos transactions (lecture seule)" },
  { icon: Repeat2, label: "Accéder à vos dépenses récurrentes" },
  { icon: BotMessageSquare, label: "Interroger vos données via Claude AI" },
]

function ConsentContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, isLoading } = useAuth()
  const [isPending, setIsPending] = useState(false)

  const clientId = searchParams.get("client_id") || ""
  const clientName = searchParams.get("client_name") || clientId
  const redirectUri = searchParams.get("redirect_uri") || ""
  const state = searchParams.get("state") || ""
  const codeChallenge = searchParams.get("code_challenge") || ""
  const codeChallengeMethod = searchParams.get("code_challenge_method") || "S256"

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!user) {
    const currentUrl = window.location.href
    router.replace(`/login?next=${encodeURIComponent(currentUrl)}`)
    return null
  }

  if (!clientId || !redirectUri) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center text-destructive">
            Paramètres de requête OAuth invalides.
          </CardContent>
        </Card>
      </div>
    )
  }

  const handleApprove = async () => {
    setIsPending(true)
    try {
      const result = await api.mcp.approveConsent({
        client_id: clientId,
        redirect_uri: redirectUri,
        state,
        code_challenge: codeChallenge,
        code_challenge_method: codeChallengeMethod,
      })
      window.location.href = result.redirect_uri
    } catch {
      toast.error("Erreur lors de l'autorisation. Veuillez réessayer.")
      setIsPending(false)
    }
  }

  const handleDeny = () => {
    const params = new URLSearchParams({ error: "access_denied" })
    if (state) params.set("state", state)
    window.location.href = `${redirectUri}?${params.toString()}`
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <div className="mb-4 flex items-center justify-center gap-4">
            <span className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <BotMessageSquare className="size-7" />
            </span>
          </div>
          <CardTitle className="text-xl">Autoriser l'accès</CardTitle>
          <CardDescription>
            <span className="font-semibold text-foreground">{clientName}</span> souhaite accéder à votre
            compte Budget Bo.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* User info */}
          <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-3">
            <Avatar className="size-9">
              <AvatarImage src={user.profile_picture || ""} alt={user.display_name || ""} />
              <AvatarFallback>{user.display_name?.[0] || user.email?.[0] || "U"}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.display_name || "Vous"}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>

          {/* Scopes */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Cette application pourra :</p>
            {MCP_SCOPES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2.5 text-sm">
                <Check className="size-4 shrink-0 text-green-500" />
                <span>{label}</span>
              </div>
            ))}
          </div>

          {/* Security notice */}
          <div className="flex gap-2 rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
            <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-primary" />
            <span>Accès en lecture seule. Aucune donnée ne peut être modifiée via cette connexion.</span>
          </div>
        </CardContent>

        <CardFooter className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={handleDeny} disabled={isPending}>
            <X className="mr-2 size-4" /> Refuser
          </Button>
          <Button className="flex-1" onClick={handleApprove} disabled={isPending}>
            {isPending ? (
              <span className="flex items-center gap-2">
                <span className="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Autorisation…
              </span>
            ) : (
              <>
                <Check className="mr-2 size-4" /> Autoriser
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

export default function McpConsentPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <ConsentContent />
    </Suspense>
  )
}
