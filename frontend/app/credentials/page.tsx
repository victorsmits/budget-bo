"use client"

import { Building2, Plus, RefreshCw, Trash2 } from "lucide-react"
import { useState } from "react"

import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useCreateCredential, useCredentials, useDeleteCredential, useSyncCredential } from "@/hooks/api/useCredentials"

export default function CredentialsPage() {
  const credentials = useCredentials()
  const createCredential = useCreateCredential()
  const deleteCredential = useDeleteCredential()
  const syncCredential = useSyncCredential()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ bank_name: "cragr", bank_label: "", login: "", password: "" })

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <PageHeader title="Comptes bancaires" subtitle="Connectez vos banques et lancez la synchronisation." />

        <Button onClick={() => setShowForm((v) => !v)}><Plus className="mr-2 size-4" />Ajouter un compte</Button>

        {showForm && (
          <Card>
            <CardContent className="grid gap-3 p-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Code banque</Label>
                <Input value={form.bank_name} onChange={(e) => setForm((s) => ({ ...s, bank_name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Libellé (optionnel)</Label>
                <Input value={form.bank_label} onChange={(e) => setForm((s) => ({ ...s, bank_label: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Identifiant</Label>
                <Input value={form.login} onChange={(e) => setForm((s) => ({ ...s, login: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Mot de passe</Label>
                <Input type="password" value={form.password} onChange={(e) => setForm((s) => ({ ...s, password: e.target.value }))} />
              </div>
              <div className="md:col-span-2">
                <Button onClick={() => createCredential.mutate({ ...form })}>Enregistrer</Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-2">
          {(credentials.data || []).map((credential) => (
            <Card key={credential.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Building2 className="size-5" /></span>
                  <div>
                    <p className="font-medium">{credential.bank_label || credential.bank_name}</p>
                    <p className="text-xs text-muted-foreground">{credential.login}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => syncCredential.mutate(credential.id)}><RefreshCw className="mr-2 size-4" />Sync</Button>
                  <Button variant="destructive" size="sm" onClick={() => deleteCredential.mutate(credential.id)}><Trash2 className="mr-2 size-4" />Supprimer</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}
