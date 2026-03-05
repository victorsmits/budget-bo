"use client"

import { useState, useEffect } from "react"
import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Calendar, Repeat, TrendingUp, AlertCircle, Play, Loader2 } from "lucide-react"
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

const categoryColors: Record<string, string> = {
  housing: "bg-blue-100 text-blue-700",
  subscriptions: "bg-purple-100 text-purple-700",
  utilities: "bg-yellow-100 text-yellow-700",
  insurance: "bg-orange-100 text-orange-700",
  food: "bg-green-100 text-green-700",
  transportation: "bg-pink-100 text-pink-700",
  other: "bg-gray-100 text-gray-700",
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
      const [recurringData, upcomingData] = await Promise.all([
        api.recurring.list(),
        api.recurring.upcoming(30),
      ])
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
    } catch (err) {
      console.error("Detection failed", err)
    } finally {
      setIsDetecting(false)
    }
  }

  const calculateDaysLeft = (dateString: string | null) => {
    if (!dateString) return null
    const target = new Date(dateString)
    const today = new Date()
    const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return Math.max(0, diff)
  }

  const totalMonthly = recurring
    .filter((e) => e.frequency_days && e.frequency_days <= 31)
    .reduce((sum, e) => sum + e.average_amount, 0)

  const upcomingTotal = upcoming.reduce((sum, e) => sum + e.average_amount, 0)

  const avgConfidence = recurring.length > 0
    ? recurring.reduce((sum, e) => sum + (e.confidence_score || 0), 0) / recurring.length
    : 0

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dépenses Récurrentes</h1>
            <p className="text-muted-foreground">
              Suivi et détection automatique ({recurring.length} patterns)
            </p>
          </div>
          <Button onClick={handleDetect} disabled={isDetecting}>
            {isDetecting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Détection IA
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total mensuel</CardTitle>
              <Repeat className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Number(totalMonthly).toFixed(2)} €</div>
              <p className="text-xs text-muted-foreground">
                {recurring.filter((e) => e.frequency_days && e.frequency_days <= 31).length} paiements mensuels
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">À venir (30j)</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">-{Number(upcomingTotal).toFixed(2)} €</div>
              <p className="text-xs text-muted-foreground">{upcoming.length} paiements attendus</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Confiance moyenne</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(Number(avgConfidence) * 100).toFixed(0)}%</div>
              <p className="text-xs text-muted-foreground">Sur {recurring.length} patterns détectés</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Patterns détectés</CardTitle>
              <CardDescription>Détectés automatiquement par l&apos;IA</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : recurring.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Aucune dépense récurrente détectée.</p>
                  <p className="text-sm mt-2">Cliquez sur "Détection IA" pour analyser vos transactions.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {recurring.map((expense) => {
                    const daysLeft = calculateDaysLeft(expense.next_expected_date)
                    return (
                      <div key={expense.id} className="flex items-center justify-between p-4 rounded-lg border">
                        <div className="flex items-center gap-4">
                          <div className={cn("h-10 w-10 rounded-full flex items-center justify-center", categoryColors[expense.category || "other"] || categoryColors.other)}>
                            <Repeat className="h-5 w-5" />
                          </div>
                          <div>
                            <p className="font-medium">{expense.pattern_name}</p>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Badge variant="secondary" className={categoryColors[expense.category || "other"] || categoryColors.other}>
                                {categoryLabels[expense.category || "other"] || expense.category}
                              </Badge>
                              <span>•</span>
                              <span>{patternLabels[expense.pattern_type || "monthly"] || expense.pattern_type || "Mensuel"}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-red-600">-{Number(expense.average_amount).toFixed(2)} €</p>
                          {daysLeft !== null && (
                            <div className="flex items-center gap-2 mt-1">
                              {daysLeft === 0 ? (
                                <Badge variant="destructive" className="text-xs">Aujourd&apos;hui</Badge>
                              ) : daysLeft <= 7 ? (
                                <Badge variant="outline" className="text-xs border-orange-300 text-orange-700">
                                  Dans {daysLeft} jours
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">Dans {daysLeft} jours</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Calendrier</CardTitle>
              <CardDescription>Vue des prochains paiements</CardDescription>
            </CardHeader>
            <CardContent>
              {upcoming.length > 0 && (
                <div className="flex items-center gap-3 p-3 rounded-lg bg-orange-50 border border-orange-200 mb-4">
                  <AlertCircle className="h-5 w-5 text-orange-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-orange-900">Paiement imminent</p>
                    <p className="text-xs text-orange-700">
                      {upcoming[0].pattern_name} ({Number(upcoming[0].average_amount).toFixed(2)} €)
                    </p>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <p className="text-sm font-medium">Ce mois</p>
                {upcoming.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun paiement à venir</p>
                ) : (
                  upcoming
                    .sort((a, b) => (a.next_expected_date || "").localeCompare(b.next_expected_date || ""))
                    .map((expense) => {
                      const daysLeft = calculateDaysLeft(expense.next_expected_date)
                      return (
                        <div key={expense.id} className="flex items-center justify-between text-sm">
                          <span>{expense.pattern_name}</span>
                          <span className="text-muted-foreground">
                            {daysLeft === null ? "?" : daysLeft === 0 ? "Aujourd'hui" : `J+${daysLeft}`}
                          </span>
                        </div>
                      )
                    })
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
