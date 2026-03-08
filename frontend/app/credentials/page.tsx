"use client"

import { useEffect, useState } from "react"
import { Building2, Loader2, Pencil, Plus, RefreshCw, Shield, Trash2 } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { api } from "@/lib/api"
import { ErrorCard } from "@/components/error"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"

interface Credential {
  id: string
  bank_name: string
  bank_label: string | null
  bank_website: string | null
  is_active: boolean
  sync_status: string | null
  last_sync_at: string | null
  created_at: string
}

const bankOptions = [
  { value: "cragr", label: "Crédit Agricole" },
  { value: "bnporc", label: "BNP Paribas" },
  { value: "sg", label: "Société Générale" },
  { value: "lcl", label: "LCL" },
  { value: "caissedepargne", label: "Caisse d'Épargne" },
  { value: "banquepopulaire", label: "Banque Populaire" },
  { value: "creditmutuel", label: "Crédit Mutuel" },
  { value: "hsbc", label: "HSBC" },
  { value: "boursorama", label: "Boursorama" },
  { value: "hellobank", label: "Hello bank!" },
  { value: "monabanq", label: "Monabanq" },
  { value: "fortuneo", label: "Fortuneo" },
  { value: "boursobank", label: "BoursoBank" },
  { value: "axa", label: "AXA Banque" },
  { value: "ing", label: "ING" },
  { value: "other", label: "Autre" },
]

const cragrWebsites = [
  { value: "ca-nord", label: "CA du Nord" },
  { value: "ca-paris", label: "CA d'Île-de-France" },
  { value: "ca-loirehloire", label: "CA Loire Haute-Loire" },
  { value: "ca-sud", label: "CA du Languedoc" },
  { value: "ca-centreouest", label: "CA Centre-Ouest" },
  { value: "ca-normandie", label: "CA Normandie" },
]

export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [syncingId, setSyncingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({ bank_name: "cragr", bank_label: "", bank_website: "", login: "", password: "" })

  const fetchCredentials = async () => {
    setIsLoading(true)
    try {
      const data = await api.credentials.list()
      setCredentials(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchCredentials()
  }, [])

  const resetForm = () => {
    setFormData({ bank_name: "cragr", bank_label: "", bank_website: "", login: "", password: "" })
    setIsAdding(false)
    setIsEditing(false)
    setEditingId(null)
  }

  const handleEdit = (cred: Credential) => {
    setEditingId(cred.id)
    setIsEditing(true)
    setIsAdding(true)
    setFormData({ bank_name: cred.bank_name, bank_label: cred.bank_label || "", bank_website: cred.bank_website || "", login: "", password: "" })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (isEditing && editingId) {
        const updateData: any = { bank_name: formData.bank_name, bank_label: formData.bank_label || undefined, bank_website: formData.bank_website || undefined }
        if (formData.login) updateData.login = formData.login
        if (formData.password) updateData.password = formData.password
        await api.credentials.update(editingId, updateData)
      } else {
        await api.credentials.create({ bank_name: formData.bank_name, bank_label: formData.bank_label || undefined, bank_website: formData.bank_website || undefined, login: formData.login, password: formData.password })
      }
      resetForm()
      await fetchCredentials()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur création")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSync = async (id: string) => {
    setSyncingId(id)
    try {
      await api.credentials.sync(id)
      await fetchCredentials()
    } finally {
      setSyncingId(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer ce compte bancaire ?\n\nCette action supprimera également toutes les transactions associées.")) return
    try {
      await api.credentials.delete(id)
      await fetchCredentials()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression")
    }
  }

  const getStatusBadge = (status: string | null) => {
    switch (status) {
      case "success":
        return <Badge className="bg-emerald-100 text-emerald-700">Sync OK</Badge>
      case "error":
        return <Badge variant="destructive">Erreur</Badge>
      case "syncing":
        return <Badge className="bg-blue-100 text-blue-700">En cours</Badge>
      default:
        return <Badge variant="outline">En attente</Badge>
    }
  }

  const showWebsiteField = formData.bank_name === "cragr"

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="glass-card rounded-3xl p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Gestion des connexions</p>
              <h1 className="text-3xl font-semibold">Comptes bancaires</h1>
              <p className="text-sm text-muted-foreground">{credentials.length} compte{credentials.length > 1 ? "s" : ""} configuré(s)</p>
            </div>
            <Button onClick={() => setIsAdding(true)} disabled={isAdding}><Plus className="mr-2 h-4 w-4" />Ajouter une connexion</Button>
          </div>
        </section>

        {error && <ErrorCard title="Erreur" description={error} retry={fetchCredentials} />}

        {isAdding && (
          <Card className="rounded-3xl">
            <CardHeader>
              <CardTitle>{isEditing ? "Modifier la connexion" : "Ajouter une connexion"}</CardTitle>
              <CardDescription className="flex items-center gap-2"><Shield className="h-4 w-4" /> Identifiants chiffrés AES-256.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="bank">Banque</Label>
                    <select id="bank" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm" value={formData.bank_name} onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}>
                      {bankOptions.map((bank) => <option key={bank.value} value={bank.value}>{bank.label}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="label">Nom personnalisé</Label>
                    <Input id="label" value={formData.bank_label} onChange={(e) => setFormData({ ...formData, bank_label: e.target.value })} placeholder="Ex: Compte principal" />
                  </div>
                </div>

                {showWebsiteField && (
                  <div className="space-y-2">
                    <Label htmlFor="website">Région Crédit Agricole</Label>
                    <select id="website" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm" value={formData.bank_website} onChange={(e) => setFormData({ ...formData, bank_website: e.target.value })} required>
                      <option value="">Sélectionnez une région</option>
                      {cragrWebsites.map((site) => <option key={site.value} value={site.value}>{site.label}</option>)}
                    </select>
                  </div>
                )}

                <div className="space-y-2"><Label htmlFor="login">Identifiant</Label><Input id="login" required={!isEditing} value={formData.login} onChange={(e) => setFormData({ ...formData, login: e.target.value })} /></div>
                <div className="space-y-2"><Label htmlFor="password">Mot de passe</Label><Input id="password" type="password" required={!isEditing} value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} /></div>

                <div className="flex gap-2">
                  <Button type="submit" disabled={isSubmitting}>{isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{isEditing ? "Enregistrer" : "Ajouter"}</Button>
                  <Button type="button" variant="outline" onClick={resetForm}>Annuler</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="space-y-4">{Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-28 w-full rounded-2xl" />)}</div>
        ) : credentials.length === 0 ? (
          <Card className="rounded-3xl"><CardContent className="py-12 text-center"><Building2 className="mx-auto mb-3 h-10 w-10 text-muted-foreground" /><p className="text-muted-foreground">Aucun compte configuré.</p></CardContent></Card>
        ) : (
          <div className="grid gap-4">
            {credentials.map((cred) => (
              <Card key={cred.id} className="rounded-3xl">
                <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10"><Building2 className="h-5 w-5 text-primary" /></div>
                    <div>
                      <p className="font-medium">{cred.bank_label || bankOptions.find((b) => b.value === cred.bank_name)?.label || cred.bank_name}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        {getStatusBadge(cred.sync_status)}
                        {cred.last_sync_at && <span>Dernière sync: {new Date(cred.last_sync_at).toLocaleDateString("fr-FR")}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleSync(cred.id)} disabled={syncingId === cred.id}>{syncingId === cred.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}<span className="ml-2">Sync</span></Button>
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(cred)} disabled={isAdding}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(cred.id)} disabled={isAdding} className="text-red-600 hover:text-red-700"><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
