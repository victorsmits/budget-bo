"use client"

import { useState, useEffect } from "react"
import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Plus, Trash2, RefreshCw, Building2, Loader2, Pencil } from "lucide-react"
import { api } from "@/lib/api"
import { ErrorCard } from "@/components/error"
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

// Website options for cragr (regional banks)
const cragrWebsites = [
  { value: "ca-nord", label: "CA du Nord" },
  { value: "ca-paris", label: "CA d'Île-de-France" },
  { value: "ca-loirehloire", label: "CA Loire Haute-Loire" },
  { value: "ca-sud", label: "CA du Languedoc" },
  { value: "ca-centreouest", label: "CA Centre-Ouest" },
  { value: "ca-normandie", label: "CA Normandie" },
  { value: "ca-bretagnepaysdelaloire", label: "CA Bretagne-Pays de Loire" },
  { value: "ca-picardie", label: "CA de la Picardie" },
  { value: "ca-champagnebourgogne", label: "CA Champagne-Bourgogne" },
  { value: "ca-alsacevosges", label: "CA d'Alsace-Vosges" },
  { value: "ca-franchecomte", label: "CA Franche-Comté" },
  { value: "ca-aquitaine", label: "CA d'Aquitaine" },
  { value: "ca-midi", label: "CA du Midi" },
  { value: "ca-martinique", label: "CA de la Martinique" },
  { value: "ca-guadeloupe", label: "CA de la Guadeloupe" },
  { value: "ca-reunion", label: "CA de La Réunion" },
  { value: "ca-toulouse", label: "CA de Toulouse" },
  { value: "ca-provencecotedazur", label: "CA Provence Côte d'Azur" },
  { value: "ca-centrefrance", label: "CA Centre France" },
  { value: "ca-anjoumaine", label: "CA Anjou Maine" },
  { value: "ca-est", label: "CA de l'Est" },
  { value: "ca-charenteperigord", label: "CA Charente-Périgord" },
  { value: "ca-latouraineetdupoitou", label: "CA de la Touraine et du Poitou" },
  { value: "ca-auvergnerhonedalpes", label: "CA Auvergne Rhône Alpes" },
  { value: "ca-morbihan", label: "CA du Morbihan" },
  { value: "ca-finistere", label: "CA de la Finistère" },
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
  const [formData, setFormData] = useState({
    bank_name: "cragr",
    bank_label: "",
    bank_website: "",
    login: "",
    password: "",
  })

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
    setFormData({
      bank_name: cred.bank_name,
      bank_label: cred.bank_label || "",
      bank_website: cred.bank_website || "",
      login: "",
      password: "",
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (isEditing && editingId) {
        // Update existing credential
        const updateData: any = {
          bank_name: formData.bank_name,
          bank_label: formData.bank_label || undefined,
          bank_website: formData.bank_website || undefined,
        }
        if (formData.login) updateData.login = formData.login
        if (formData.password) updateData.password = formData.password
        await api.credentials.update(editingId, updateData)
      } else {
        // Create new credential
        await api.credentials.create({
          bank_name: formData.bank_name,
          bank_label: formData.bank_label || undefined,
          bank_website: formData.bank_website || undefined,
          login: formData.login,
          password: formData.password,
        })
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
    } catch (err) {
      console.error("Sync failed", err)
    } finally {
      setSyncingId(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer ce compte bancaire ?\n\nCette action supprimera également toutes les transactions associées.")) {
      return
    }
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
        return <Badge className="bg-green-100 text-green-700">Sync OK</Badge>
      case "error":
        return <Badge variant="destructive">Erreur</Badge>
      case "syncing":
        return <Badge className="bg-blue-100 text-blue-700">En cours...</Badge>
      default:
        return <Badge variant="outline">En attente</Badge>
    }
  }

  const showWebsiteField = formData.bank_name === "cragr"

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Comptes Bancaires</h1>
            <p className="text-muted-foreground">
              Gérez vos connexions bancaires ({credentials.length} compte{credentials.length > 1 ? "s" : ""})
            </p>
          </div>
          <Button onClick={() => setIsAdding(true)} disabled={isAdding}>
            <Plus className="mr-2 h-4 w-4" />
            Ajouter un compte
          </Button>
        </div>

        {error && <ErrorCard title="Erreur" description={error} retry={fetchCredentials} />}

        {isAdding && (
          <Card>
            <CardHeader>
              <CardTitle>{isEditing ? "Modifier le compte" : "Ajouter un compte bancaire"}</CardTitle>
              <CardDescription>
                Vos identifiants sont chiffrés avec AES-256
                {isEditing && " - Laissez login/mot de passe vides pour ne pas les modifier"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="bank">Banque</Label>
                    <select
                      id="bank"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      value={formData.bank_name}
                      onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                    >
                      {bankOptions.map((bank) => (
                        <option key={bank.value} value={bank.value}>
                          {bank.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="label">Nom personnalisé (optionnel)</Label>
                    <Input
                      id="label"
                      placeholder="ex: Mon CA principal"
                      value={formData.bank_label}
                      onChange={(e) => setFormData({ ...formData, bank_label: e.target.value })}
                    />
                  </div>
                </div>

                {showWebsiteField && (
                  <div className="space-y-2">
                    <Label htmlFor="website">Région CA (obligatoire pour Crédit Agricole)</Label>
                    <select
                      id="website"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      value={formData.bank_website}
                      onChange={(e) => setFormData({ ...formData, bank_website: e.target.value })}
                      required
                    >
                      <option value="">-- Sélectionnez votre région --</option>
                      {cragrWebsites.map((site) => (
                        <option key={site.value} value={site.value}>
                          {site.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="login">Identifiant {isEditing && "(laisser vide pour ne pas modifier)"}</Label>
                  <Input
                    id="login"
                    required={!isEditing}
                    placeholder="Votre identifiant bancaire"
                    value={formData.login}
                    onChange={(e) => setFormData({ ...formData, login: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Mot de passe {isEditing && "(laisser vide pour ne pas modifier)"}</Label>
                  <Input
                    id="password"
                    type="password"
                    required={!isEditing}
                    placeholder="Votre mot de passe"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {isEditing ? "Enregistrer" : "Ajouter"}
                  </Button>
                  <Button type="button" variant="outline" onClick={resetForm}>
                    Annuler
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        ) : credentials.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Building2 className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Aucun compte bancaire configuré</p>
              <p className="text-sm text-muted-foreground mt-2">
                Ajoutez votre premier compte pour synchroniser vos transactions
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {credentials.map((cred) => (
              <Card key={cred.id}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-lg">
                          {cred.bank_label || bankOptions.find(b => b.value === cred.bank_name)?.label || cred.bank_name}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          {getStatusBadge(cred.sync_status)}
                          {cred.bank_website && cred.bank_name === "cragr" && (
                            <span className="text-xs text-muted-foreground">
                              ({cragrWebsites.find(w => w.value === cred.bank_website)?.label || cred.bank_website})
                            </span>
                          )}
                          {cred.last_sync_at && (
                            <span className="text-xs text-muted-foreground">
                              Dernière sync: {new Date(cred.last_sync_at).toLocaleDateString("fr-FR")}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSync(cred.id)}
                        disabled={syncingId === cred.id}
                      >
                        {syncingId === cred.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                        <span className="ml-2 hidden sm:inline">Sync</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(cred)}
                        disabled={isAdding}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(cred.id)}
                        disabled={isAdding}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
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
