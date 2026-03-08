"use client"

import DashboardLayout from "./dashboard-layout"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { QueryErrorBoundary } from "@/components/ui/query-error-boundary"
import {
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
  Repeat,
  CreditCard,
  Loader2,
} from "lucide-react"
import { useDashboardData } from "@/hooks/api"
import { useBankAccountsSummary } from "@/hooks/api/useAccounts"
import { DashboardSkeleton } from "@/components/loading"
import { ErrorCard } from "@/components/error"
import { AuthErrorHandler } from "@/components/auth/auth-error-handler"
import { CategoryBadge } from "@/components/transactions/category-badge"
import { TransactionCard } from "@/components/transactions/transaction-card"
import { useMemo } from "react"
import { cn } from "@/lib/utils"


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

  const { data: accountsSummary, isLoading: isLoadingAccounts } = useBankAccountsSummary()

  const handleSync = async () => {
    if (credentials && credentials.length > 0) {
      syncCredential.mutate(credentials[0].id)
    }
  }

  const stats = useMemo(() => {
    // Use real bank balance if available, otherwise fall back to calculated net
    const realBalance = accountsSummary?.total_balance
    const displayBalance = realBalance !== undefined 
      ? realBalance.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })
      : summary?.net !== undefined
        ? summary.net.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })
        : "0 €"

    return [
      {
        title: "Solde réel",
        value: displayBalance,
        change: realBalance !== undefined ? "Solde bancaire" : "Calculé",
        trend: (realBalance ?? summary?.net ?? 0) >= 0 ? "up" : "down",
        icon: Wallet,
      },
      {
        title: "Dépenses ce mois",
        value: summary?.total_expenses ? summary.total_expenses.toLocaleString("fr-FR", { style: "currency", currency: "EUR" }) : "0 €",
        change: "",
        trend: "down",
        icon: ArrowDownRight,
      },
      {
        title: "Revenus ce mois",
        value: summary?.total_income ? summary.total_income.toLocaleString("fr-FR", { style: "currency", currency: "EUR" }) : "0 €",
        change: "",
        trend: "up",
        icon: ArrowUpRight,
      },
      {
        title: "Transactions",
        value: recentTransactions?.length.toString() ?? "0",
        change: "",
        trend: "neutral",
        icon: CreditCard,
      },
    ]
  }, [summary, recentTransactions, accountsSummary])

  const calculateDaysLeft = (dateString: string | null) => {
    if (!dateString) return null
    const target = new Date(dateString)
    const today = new Date()
    const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return Math.max(0, diff)
  }

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
        <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Vue d&apos;ensemble de vos finances {summary ? `(${summary.period.start} → ${summary.period.end})` : ""}
            </p>
          </div>
            <Button 
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
                  Sync Bancaire
                </>
              )}
            </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon
            const TrendIcon = stat.trend === "up" ? ArrowUpRight : ArrowDownRight
            const trendColor = stat.trend === "up" ? "text-green-600" : stat.trend === "down" ? "text-red-600" : "text-gray-600"

            return (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {stat.title}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  {stat.change && (
                    <p className={cn("text-xs", trendColor)}>
                      <TrendIcon className="mr-1 inline h-3 w-3" />
                      {stat.change}
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          <Card className="lg:col-span-4">
            <CardHeader>
              <CardTitle>Dépenses par catégorie</CardTitle>
              <CardDescription>Répartition ce mois</CardDescription>
            </CardHeader>
            <CardContent>
              {summary?.by_category?.length === 0 ? (
                <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                  Aucune dépense ce mois
                </div>
              ) : (
                <div className="space-y-4">
                  {summary?.by_category?.map((cat: { category: string; count: number; total: number }) => (
                    <div key={cat.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        <CategoryBadge category={cat.category} />
                        <span className="text-xs text-muted-foreground">({cat.count})</span>
                      </div>
                      <span className="font-medium text-red-600">
                        -{cat.total.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Prochains paiements</CardTitle>
              <CardDescription>Dépenses récurrentes à venir</CardDescription>
            </CardHeader>
            <CardContent>
              {!upcomingRecurring || upcomingRecurring.length === 0 ? (
                <div className="text-muted-foreground text-sm">
                  Aucune dépense récurrente à venir
                </div>
              ) : (
                <div className="space-y-4">
                  {upcomingRecurring?.slice(0, 5).map((item) => {
                    const daysLeft = calculateDaysLeft(item.next_expected_date)
                    return (
                      <div key={item.id} className="flex items-center justify-between">
                        <div className="space-y-1">
                          <p className="text-sm font-medium">{item.pattern_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {daysLeft === null ? "Date inconnue" : daysLeft === 0 ? "Aujourd'hui" : `Dans ${daysLeft} jour${daysLeft > 1 ? "s" : ""}`}
                          </p>
                        </div>
                        <div className="font-medium text-red-600">
                          -{Number(item.average_amount).toFixed(2)} €
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Transactions récentes</CardTitle>
            <CardDescription>Les 5 dernières opérations</CardDescription>
          </CardHeader>
          <CardContent>
            {!recentTransactions || recentTransactions.length === 0 ? (
              <div className="text-muted-foreground text-sm">
                Aucune transaction. Lancez une synchronisation bancaire.
              </div>
            ) : (
              <div className="space-y-2">
                {recentTransactions?.map((tx) => (
                  <TransactionCard key={tx.id} transaction={tx} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      </DashboardLayout>
    </QueryErrorBoundary>
  )
}

