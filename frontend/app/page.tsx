"use client"

import { useState, useEffect } from "react"
import DashboardLayout from "./dashboard-layout"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
  TrendingUp,
  Repeat,
  CreditCard,
  Loader2,
} from "lucide-react"
import { api } from "@/lib/api"
import { DashboardSkeleton } from "@/components/loading"
import { ErrorCard } from "@/components/error"

interface Transaction {
  id: string
  cleaned_label: string | null
  raw_label: string
  amount: number
  date: string
  category: string
  is_expense: boolean
  is_recurring: boolean
}

interface RecurringExpense {
  id: string
  pattern_name: string
  average_amount: number
  next_expected_date: string | null
}

interface SummaryData {
  period: { start: string; end: string }
  total_expenses: number
  total_income: number
  net: number
  by_category: { category: string; total: number; count: number }[]
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([])
  const [upcomingRecurring, setUpcomingRecurring] = useState<RecurringExpense[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboardData = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const [summaryData, transactions, recurring] = await Promise.all([
        api.transactions.summary(),
        api.transactions.list({ limit: 5 }),
        api.recurring.upcoming(30),
      ])
      
      setSummary(summaryData)
      setRecentTransactions(transactions)
      setUpcomingRecurring(recurring)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const handleSync = async () => {
    try {
      // TODO: Implement actual sync
      console.log("Sync triggered")
      await fetchDashboardData()
    } catch (err) {
      console.error("Sync failed", err)
    }
  }

  const calculateDaysLeft = (dateString: string | null) => {
    if (!dateString) return null
    const target = new Date(dateString)
    const today = new Date()
    const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return Math.max(0, diff)
  }

  if (isLoading) {
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
          description={error}
          retry={fetchDashboardData}
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

  const stats = [
    {
      title: "Solde net",
      value: `${summary.net.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}`,
      change: "",
      trend: summary.net >= 0 ? "up" : "down",
      icon: Wallet,
    },
    {
      title: "Dépenses ce mois",
      value: `${summary.total_expenses.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}`,
      change: "",
      trend: "down",
      icon: ArrowDownRight,
    },
    {
      title: "Revenus ce mois",
      value: `${summary.total_income.toLocaleString("fr-FR", { style: "currency", currency: "EUR" })}`,
      change: "",
      trend: "up",
      icon: ArrowUpRight,
    },
    {
      title: "Transactions",
      value: recentTransactions.length.toString(),
      change: "",
      trend: "neutral",
      icon: CreditCard,
    },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Vue d&apos;ensemble de vos finances ({summary.period.start} → {summary.period.end})
            </p>
          </div>
          <Button onClick={handleSync}>Sync Bancaire</Button>
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
              {summary.by_category.length === 0 ? (
                <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                  Aucune dépense ce mois
                </div>
              ) : (
                <div className="space-y-4">
                  {summary.by_category.map((cat) => (
                    <div key={cat.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        <span className="text-sm">{cat.category}</span>
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
              {upcomingRecurring.length === 0 ? (
                <div className="text-muted-foreground text-sm">
                  Aucune dépense récurrente à venir
                </div>
              ) : (
                <div className="space-y-4">
                  {upcomingRecurring.slice(0, 5).map((item) => {
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
                          -{item.average_amount.toFixed(2)} €
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
            {recentTransactions.length === 0 ? (
              <div className="text-muted-foreground text-sm">
                Aucune transaction. Lancez une synchronisation bancaire.
              </div>
            ) : (
              <div className="space-y-4">
                {recentTransactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "h-9 w-9 rounded-full flex items-center justify-center",
                        tx.is_expense ? "bg-red-100 text-red-600" : "bg-green-100 text-green-600"
                      )}>
                        {tx.is_expense ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
                      </div>
                      <div>
                        <p className="text-sm font-medium">{tx.cleaned_label || tx.raw_label}</p>
                        <p className="text-xs text-muted-foreground">{tx.date} • {tx.category}</p>
                      </div>
                    </div>
                    <div className={cn("font-medium", tx.is_expense ? "text-red-600" : "text-green-600")}>
                      {tx.is_expense ? "-" : "+"}{tx.amount.toFixed(2)} €
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
