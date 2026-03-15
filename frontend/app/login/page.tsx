"use client"

import { ShieldCheck, Wallet2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function LoginPage() {
  const handleLogin = () => {
    // Redirection directe vers l'OAuth
    window.location.href = "/api/auth/login"
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,_hsl(var(--muted))_0%,_hsl(var(--background))_55%)] p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Wallet2 className="size-7" />
          </div>
          <CardTitle className="text-3xl">Budget Bo</CardTitle>
          <CardDescription>Nouvelle interface, même API. Connectez-vous pour commencer.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleLogin} className="w-full" size="lg">
            Connexion avec Google
          </Button>
          <p className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="size-4" /> Authentification sécurisée OAuth
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
