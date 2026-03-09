"use client"

import { Building2, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react"
import { useState } from "react"

import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useCreateCredential, useCredentials, useDeleteCredential, useSyncCredential, useUpdateCredential } from "@/hooks/api/useCredentials"

const BANK_LABELS: Record<string, string> = {
  cragr: "Crédit Agricole",
  bnporc: "BNP Paribas",
  sg: "Société Générale",
  lcl: "LCL",
  boursobank: "BoursoBank",
  boursorama: "Boursorama",
  caissedepargne: "Caisse d'Épargne",
  banquepopulaire: "Banque Populaire",
  creditmutuel: "Crédit Mutuel",
}

export default function CredentialsPage() {
  const credentials = useCredentials()
  const createCredential = useCreateCredential()
  const updateCredential = useUpdateCredential()
  const deleteCredential = useDeleteCredential()
  const syncCredential = useSyncCredential()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ bank_name: "cragr", bank_label: "", login: "", password: "" })

  const reset = () => {
    setShowForm(false)
    setEditingId(null)
    setForm({ bank_name: "cragr", bank_label: "", login: "", password: "" })
  }

  const submit = () => {
    if (editingId) {
      updateCredential.mutate({
        id: editingId,
        data: {
          bank_name: form.bank_name,
          bank_label: form.bank_label || undefined,
          login: form.login || undefined,
          password: form.password || undefined,
        },
      })
    } else {
      createCredential.mutate({ ...form, bank_label: form.bank_label || undefined })
    }
    reset()
  }

  return (
    <DashboardLayout>
      <div className="space-y-4 pb-6">
        <PageHeader title="Comptes bancaires" subtitle="Connectez vos banques, synchronisez et éditez vos accès." />

        <Button onClick={() => setShowForm((v) => !v)}><Plus className="mr-2 size-4" />{editingId ? "Fermer" : "Ajouter un compte"}</Button>

        {showForm && (
          <Card>
            <CardContent className="grid gap-3 p-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Code banque</Label>
                <Input value={form.bank_name} onChange={(e) => setForm((s) => ({ ...s, bank_name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Nom affiché</Label>
                <Input value={form.bank_label} onChange={(e) => setForm((s) => ({ ...s, bank_label: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Identifiant {editingId ? "(laisser vide pour conserver)" : ""}</Label>
                <Input value={form.login} onChange={(e) => setForm((s) => ({ ...s, login: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Mot de passe {editingId ? "(laisser vide pour conserver)" : ""}</Label>
                <Input type="password" value={form.password} onChange={(e) => setForm((s) => ({ ...s, password: e.target.value }))} />
              </div>
              <div className="flex gap-2 md:col-span-2">
                <Button onClick={submit}>{editingId ? "Mettre à jour" : "Enregistrer"}</Button>
                <Button variant="outline" onClick={reset}>Annuler</Button>
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
                    <p className="font-medium">{credential.bank_label || BANK_LABELS[credential.bank_name] || credential.bank_name}</p>
                    <p className="text-xs text-muted-foreground">{credential.login}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => { setShowForm(true); setEditingId(credential.id); setForm({ bank_name: credential.bank_name, bank_label: credential.bank_label || "", login: "", password: "" }) }}><Pencil className="mr-2 size-4" />Éditer</Button>
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
