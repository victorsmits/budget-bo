"use client"

import { useMemo } from "react"
import {
  ArrowDownRight,
  ArrowUpRight,
  CreditCard,
  Loader2,
  Repeat,
  Sparkles,
  Wallet,
} from "lucide-react"

import DashboardLayout from "./dashboard-layout"
import { useDashboardData } from "@/hooks/api"
import { useBankAccountsSummary } from "@/hooks/api/useAccounts"
import { DashboardSkeleton } from "@/components/loading"
import { ErrorCard } from "@/components/error"
import { AuthErrorHandler } from "@/components/auth/auth-error-handler"
import { TransactionCard } from "@/components/transactions/transaction-card"
import { QueryErrorBoundary } from "@/components/ui/query-error-boundary"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"

export default function DashboardPage() {
  const {
    summary,
    recentTransactions,
    upcomingRecurring,
    credentials,
    isLoading,
    error,
    syncCredential,
  } = useDashboardData()

  const { data: accountsSummary, isLoading: isLoadingAccounts } =
    useBankAccountsSummary()

  const handleSync = async () => {
    if (credentials && credentials.length > 0) {
      syncCredential.mutate(credentials[0].id)
    }
  }

  const stats = useMemo(() => {
    const realBalance = accountsSummary?.total_balance
    const net = summary?.net ?? 0
    const displayBalance =
      realBalance !== undefined
        ? realBalance
        : net

    return [
      {
        title: "Solde actuel",
        value: formatCurrency(displayBalance),
        helper: realBalance !== undefined ? "Donnée bancaire" : "Donnée calculée",
        icon: Wallet,
      },
      {
        title: "Dépenses du mois",
        value: formatCurrency(summary?.total_expenses ?? 0),
        helper: "Sorties cumulées",
        icon: ArrowDownRight,
      },
      {
        title: "Revenus du mois",
        value: formatCurrency(summary?.total_income ?? 0),
        helper: "Entrées cumulées",
        icon: ArrowUpRight,
      },
      {
        title: "Mouvements récents",
        value: String(recentTransactions?.length ?? 0),
        helper: "5 dernières opérations",
        icon: CreditCard,
      },
    ]
  }, [summary, recentTransactions, accountsSummary])

  const budgetHealth = useMemo(() => {
    const income = summary?.total_income ?? 0
    const expenses = summary?.total_expenses ?? 0

    if (income <= 0) {
      return 0
    }

    const remainingPercent = ((income - expenses) / income) * 100
    return Math.max(0, Math.min(100, Math.round(remainingPercent)))
  }, [summary])

  if (isLoading || isLoadingAccounts) {
    return (
      <DashboardLayout>
        <DashboardSkeleton />
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <ErrorCard
          title="Erreur de chargement"
          description={error.message}
          retry={() => window.location.reload()}
        />
      </DashboardLayout>
    )
  }

  if (!summary) {
    return (
      <DashboardLayout>
        <ErrorCard
          title="Aucune donnée"
          description="Aucune transaction trouvée. Ajoutez un compte bancaire pour commencer."
        />
      </DashboardLayout>
    )
  }

  return (
    <QueryErrorBoundary>
      <DashboardLayout>
        <AuthErrorHandler error={error || undefined} />

        <div className="space-y-6">
          <Card className="border-none bg-gradient-to-r from-slate-900 via-indigo-900 to-slate-900 text-white shadow-xl">
            <CardContent className="p-6 md:p-8">
              <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                <div className="space-y-2">
                  <Badge className="bg-white/15 text-white hover:bg-white/20">
                    <Sparkles className="mr-1 h-3.5 w-3.5" />
                    Nouvelle interface
                  </Badge>
                  <h1 className="text-2xl font-semibold md:text-3xl">Tableau de bord financier</h1>
                  <p className="text-sm text-slate-200">
                    Suivi en temps réel de vos flux • Période du {summary.period.start} au {summary.period.end}
                  </p>
                </div>

                <div className="flex flex-col items-start gap-2 md:items-end">
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-300">Solde disponible</span>
                  <p className="text-3xl font-bold">{stats[0].value}</p>
                  <Button
                    variant="secondary"
                    onClick={handleSync}
                    disabled={syncCredential.isPending || !credentials?.length}
                  >
                    {syncCredential.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Synchronisation...
                      </>
                    ) : (
                      <>
                        <Repeat className="mr-2 h-4 w-4" />
                        Synchroniser mes comptes
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {stats.map((stat) => {
              const Icon = stat.icon
              return (
                <Card key={stat.title} className="border-slate-200/80">
                  <CardHeader className="pb-3">
                    <CardDescription>{stat.title}</CardDescription>
                    <CardTitle className="text-2xl">{stat.value}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between pt-0">
                    <span className="text-xs text-muted-foreground">{stat.helper}</span>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
              )
            })}
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Répartition des dépenses</CardTitle>
                <CardDescription>Catégories les plus actives ce mois-ci</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {summary.by_category.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucune dépense enregistrée pour cette période.</p>
                ) : (
                  summary.by_category.map((cat: { category: string; count: number; total: number }) => {
                    const ratio = summary.total_expenses
                      ? Math.round((cat.total / summary.total_expenses) * 100)
                      : 0

                    return (
                      <div key={cat.category} className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{cat.category}</span>
                            <Badge variant="secondary">{cat.count} ops</Badge>
                          </div>
                          <span className="font-semibold text-red-600">
                            -{formatCurrency(cat.total)}
                          </span>
                        </div>
                        <Progress value={ratio} />
                      </div>
                    )
                  })
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Santé budgétaire</CardTitle>
                <CardDescription>Part de revenu encore disponible</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="mb-2 flex items-end justify-between">
                    <span className="text-sm text-muted-foreground">Reste à vivre</span>
                    <span className="text-xl font-semibold">{budgetHealth}%</span>
                  </div>
                  <Progress value={budgetHealth} />
                </div>
                <Separator />
                <div className="space-y-2 text-sm">
                  <p className="flex items-center justify-between">
                    <span className="text-muted-foreground">Revenus</span>
                    <span className="font-medium text-green-600">+{formatCurrency(summary.total_income)}</span>
                  </p>
                  <p className="flex items-center justify-between">
                    <span className="text-muted-foreground">Dépenses</span>
                    <span className="font-medium text-red-600">-{formatCurrency(summary.total_expenses)}</span>
                  </p>
                  <p className="flex items-center justify-between">
                    <span className="text-muted-foreground">Solde net</span>
                    <span className="font-medium">{formatCurrency(summary.net)}</span>
                  </p>
                </div>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-4 xl:grid-cols-5">
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Prochains paiements</CardTitle>
                <CardDescription>Récurrences à surveiller</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {!upcomingRecurring || upcomingRecurring.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun paiement récurrent détecté.</p>
                ) : (
                  upcomingRecurring.slice(0, 5).map((item) => {
                    const daysLeft = calculateDaysLeft(item.next_expected_date)
                    return (
                      <div key={item.id} className="rounded-lg border p-3">
                        <p className="font-medium">{item.pattern_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {daysLeft === null
                            ? "Date inconnue"
                            : daysLeft === 0
                              ? "Prévu aujourd'hui"
                              : `Prévu dans ${daysLeft} jour${daysLeft > 1 ? "s" : ""}`}
                        </p>
                        <p className="mt-2 text-sm font-semibold text-red-600">
                          -{formatCurrency(Number(item.average_amount))}
                        </p>
                      </div>
                    )
                  })
                )}
              </CardContent>
            </Card>

            <Card className="xl:col-span-3">
              <CardHeader>
                <CardTitle>Transactions récentes</CardTitle>
                <CardDescription>Historique des dernières opérations synchronisées</CardDescription>
              </CardHeader>
              <CardContent>
                {!recentTransactions || recentTransactions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Aucune transaction. Lancez une synchronisation bancaire.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {recentTransactions.map((tx) => (
                      <TransactionCard key={tx.id} transaction={tx} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </section>
        </div>
      </DashboardLayout>
    </QueryErrorBoundary>
  )
}

function calculateDaysLeft(dateString: string | null) {
  if (!dateString) return null

  const target = new Date(dateString)
  const today = new Date()
  const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  return Math.max(0, diff)
}

function formatCurrency(value: number) {
  return value.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })
}
