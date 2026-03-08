"use client"

import { useState, useEffect } from "react"
import { AlertCircle, Calendar, Loader2, Play, Repeat, TrendingUp } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorCard } from "@/components/error"

interface RecurringExpense {
  id: string
  pattern_name: string
  pattern_type: string | null
  average_amount: number
  frequency_days: number | null
  confidence_score: number | null
  next_expected_date: string | null
  last_detected_at: string
  category: string | null
  is_active: boolean
}

const patternLabels: Record<string, string> = {
  weekly: "Hebdomadaire",
  monthly: "Mensuel",
  quarterly: "Trimestriel",
  annually: "Annuel",
  daily: "Quotidien",
}

const categoryLabels: Record<string, string> = {
  housing: "Logement",
  subscriptions: "Abonnements",
  utilities: "Factures",
  insurance: "Assurance",
  food: "Alimentation",
  transportation: "Transport",
  other: "Autre",
}

export default function RecurringPage() {
  const [recurring, setRecurring] = useState<RecurringExpense[]>([])
  const [upcoming, setUpcoming] = useState<RecurringExpense[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isDetecting, setIsDetecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRecurring = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [recurringData, upcomingData] = await Promise.all([api.recurring.list(), api.recurring.upcoming(30)])
      setRecurring(recurringData)
      setUpcoming(upcomingData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchRecurring()
  }, [])

  const handleDetect = async () => {
    setIsDetecting(true)
    try {
      await api.recurring.detect(6)
      await fetchRecurring()
    } finally {
      setIsDetecting(false)
    }
  }

  const totalMonthly = recurring.filter((e) => e.frequency_days && e.frequency_days <= 31).reduce((sum, e) => sum + e.average_amount, 0)
  const upcomingTotal = upcoming.reduce((sum, e) => sum + e.average_amount, 0)
  const avgConfidence = recurring.length > 0 ? recurring.reduce((sum, e) => sum + (e.confidence_score || 0), 0) / recurring.length : 0

  if (error) {
    return (
      <DashboardLayout>
        <ErrorCard title="Erreur de chargement" description={error} retry={fetchRecurring} />
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="glass-card rounded-3xl p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Moteur de récurrence</p>
              <h1 className="text-3xl font-semibold">Abonnements & paiements prévisibles</h1>
              <p className="text-sm text-muted-foreground">{recurring.length} patterns détectés automatiquement</p>
            </div>
            <Button onClick={handleDetect} disabled={isDetecting}>
              {isDetecting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}Relancer la détection
            </Button>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <InfoCard icon={Repeat} label="Impact mensuel" value={`-${totalMonthly.toFixed(2)} €`} sub={`${recurring.length} lignes actives`} />
          <InfoCard icon={Calendar} label="À payer sur 30 jours" value={`-${upcomingTotal.toFixed(2)} €`} sub={`${upcoming.length} paiements attendus`} />
          <InfoCard icon={TrendingUp} label="Confiance IA" value={`${(avgConfidence * 100).toFixed(0)}%`} sub="Précision moyenne" />
        </section>

        <div className="grid gap-4 xl:grid-cols-5">
          <Card className="xl:col-span-3 rounded-3xl">
            <CardHeader>
              <CardTitle>Catalogue des paiements récurrents</CardTitle>
              <CardDescription>Détection pilotée par vos historiques bancaires</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}</div>
              ) : recurring.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">Aucun pattern détecté. Lancez une analyse IA.</p>
              ) : (
                <div className="space-y-3">
                  {recurring.map((expense) => {
                    const daysLeft = calculateDaysLeft(expense.next_expected_date)
                    return (
                      <div key={expense.id} className="rounded-2xl border p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="font-medium">{expense.pattern_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {categoryLabels[expense.category || "other"]} • {patternLabels[expense.pattern_type || "monthly"]}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-red-600">-{Number(expense.average_amount).toFixed(2)} €</p>
                            <p className="text-xs text-muted-foreground">{daysLeft === null ? "Date inconnue" : daysLeft === 0 ? "Aujourd'hui" : `Dans ${daysLeft} jours`}</p>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="xl:col-span-2 rounded-3xl">
            <CardHeader>
              <CardTitle>Timeline des échéances</CardTitle>
              <CardDescription>Priorisez les sorties imminentes</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {upcoming.length > 0 && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <AlertCircle className="h-4 w-4" />Prochaine alerte
                  </p>
                  <p className="mt-1 text-sm">{upcoming[0].pattern_name} • {Number(upcoming[0].average_amount).toFixed(2)} €</p>
                </div>
              )}

              {upcoming.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aucun paiement à venir.</p>
              ) : (
                upcoming
                  .sort((a, b) => (a.next_expected_date || "").localeCompare(b.next_expected_date || ""))
                  .map((expense) => (
                    <div key={expense.id} className="flex items-center justify-between rounded-xl border p-3 text-sm">
                      <span className="font-medium">{expense.pattern_name}</span>
                      <Badge variant="secondary">J+{calculateDaysLeft(expense.next_expected_date) ?? "?"}</Badge>
                    </div>
                  ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

function InfoCard({ icon: Icon, label, value, sub }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; sub: string }) {
  return (
    <Card className="rounded-3xl">
      <CardContent className="p-5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{label}</p>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <p className="text-2xl font-semibold">{value}</p>
        <p className="text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  )
}

function calculateDaysLeft(dateString: string | null) {
  if (!dateString) return null
  const target = new Date(dateString)
  const today = new Date()
  const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  return Math.max(0, diff)
}
