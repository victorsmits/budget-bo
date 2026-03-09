"use client"

import { Building2, Info, Pencil, Plus, RefreshCw, ShieldCheck, Trash2 } from "lucide-react"
import { useState } from "react"

import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  useCreateCredential,
  useCredentials,
  useDeleteCredential,
  useSyncCredential,
  useUpdateCredential,
} from "@/hooks/api/useCredentials"

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

const CRAGR_WEBSITES = [
  { value: "ca-paris", label: "Île-de-France" },
  { value: "ca-nord", label: "Nord de France" },
  { value: "ca-aquitaine", label: "Aquitaine" },
  { value: "ca-provencecotedazur", label: "Provence Côte d’Azur" },
  { value: "ca-alsacevosges", label: "Alsace Vosges" },
]

const BANK_OPTIONS = Object.entries(BANK_LABELS).map(([value, label]) => ({ value, label }))

export default function CredentialsPage() {
  const credentials = useCredentials()
  const createCredential = useCreateCredential()
  const updateCredential = useUpdateCredential()
  const deleteCredential = useDeleteCredential()
  const syncCredential = useSyncCredential()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({
    bank_name: "cragr",
    bank_label: "",
    bank_website: "",
    login: "",
    password: "",
  })

  const isCragr = form.bank_name === "cragr"

  const reset = () => {
    setShowForm(false)
    setEditingId(null)
    setForm({ bank_name: "cragr", bank_label: "", bank_website: "", login: "", password: "" })
  }

  const submit = () => {
    if (!editingId && (!form.login.trim() || !form.password.trim())) return
    if (isCragr && !form.bank_website.trim()) return

    if (editingId) {
      updateCredential.mutate({
        id: editingId,
        data: {
          bank_name: form.bank_name,
          bank_label: form.bank_label || undefined,
          bank_website: form.bank_website || undefined,
          login: form.login || undefined,
          password: form.password || undefined,
        },
      })
    } else {
      createCredential.mutate({
        bank_name: form.bank_name,
        bank_label: form.bank_label || undefined,
        bank_website: form.bank_website || undefined,
        login: form.login,
        password: form.password,
      })
    }
    reset()
  }

  return (
    <DashboardLayout>
      <div className="space-y-4 pb-6">
        <PageHeader title="Comptes bancaires" subtitle="Ajoutez, modifiez et synchronisez vos accès bancaires." />

        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="mr-2 size-4" />
          {showForm ? "Fermer le formulaire" : "Ajouter un compte"}
        </Button>

        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>{editingId ? "Modifier un compte" : "Nouveau compte bancaire"}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-4">
              <div className="rounded-lg border bg-muted/40 p-3 text-sm text-muted-foreground">
                <p className="flex items-center gap-2 font-medium text-foreground">
                  <ShieldCheck className="size-4" /> Informations importantes
                </p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  <li>Vos identifiants sont chiffrés côté serveur.</li>
                  <li>Pour Crédit Agricole, la région est obligatoire.</li>
                  <li>En mode édition, laisser identifiant/mot de passe vide conserve les valeurs actuelles.</li>
                </ul>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Banque</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.bank_name}
                    onChange={(e) => setForm((s) => ({ ...s, bank_name: e.target.value, bank_website: "" }))}
                  >
                    {BANK_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Nom affiché (optionnel)</Label>
                  <Input
                    placeholder="Ex: Compte principal"
                    value={form.bank_label}
                    onChange={(e) => setForm((s) => ({ ...s, bank_label: e.target.value }))}
                  />
                </div>

                {isCragr && (
                  <div className="space-y-2 md:col-span-2">
                    <Label>Région Crédit Agricole</Label>
                    <select
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={form.bank_website}
                      onChange={(e) => setForm((s) => ({ ...s, bank_website: e.target.value }))}
                    >
                      <option value="">Sélectionner votre région</option>
                      {CRAGR_WEBSITES.map((site) => (
                        <option key={site.value} value={site.value}>
                          {site.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-muted-foreground">Cette information est requise pour connecter certains accès CA.</p>
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Identifiant bancaire {editingId ? "(optionnel en édition)" : ""}</Label>
                  <Input
                    placeholder="Votre identifiant"
                    value={form.login}
                    onChange={(e) => setForm((s) => ({ ...s, login: e.target.value }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Mot de passe {editingId ? "(optionnel en édition)" : ""}</Label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={(e) => setForm((s) => ({ ...s, password: e.target.value }))}
                  />
                </div>
              </div>

              <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
                <p className="flex items-center gap-2"><Info className="size-3.5" /> Après création, cliquez sur <strong>Sync</strong> pour lancer la première synchronisation.</p>
              </div>

              <div className="flex gap-2">
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
                  <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Building2 className="size-5" />
                  </span>
                  <div>
                    <p className="font-medium">
                      {credential.bank_label || BANK_LABELS[credential.bank_name] || credential.bank_name}
                    </p>
                    <p className="text-xs text-muted-foreground">{credential.login}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowForm(true)
                      setEditingId(credential.id)
                      setForm({
                        bank_name: credential.bank_name,
                        bank_label: credential.bank_label || "",
                        bank_website: credential.bank_website || "",
                        login: "",
                        password: "",
                      })
                    }}
                  >
                    <Pencil className="mr-2 size-4" />Éditer
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => syncCredential.mutate(credential.id)}>
                    <RefreshCw className="mr-2 size-4" />Sync
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => deleteCredential.mutate(credential.id)}>
                    <Trash2 className="mr-2 size-4" />Supprimer
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}
