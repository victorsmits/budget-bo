"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Download, Filter, Search, SlidersHorizontal } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { ErrorCard } from "@/components/error"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import {
  getCategoryBadgeClass,
  getCategoryLabel,
  getTransactionDisplayLabel,
  TRANSACTION_CATEGORY_LABELS,
} from "@/lib/transaction-presentation"
import { cn, formatCurrency } from "@/lib/utils"
import { Transaction } from "@/types/api"

type TransactionTypeFilter = "all" | "expense" | "income"

interface PaginationState {
  page: number
  size: number
  total: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

const INITIAL_PAGINATION: PaginationState = {
  page: 1,
  size: 20,
  total: 0,
  pages: 0,
  has_next: false,
  has_prev: false,
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [pagination, setPagination] = useState<PaginationState>(INITIAL_PAGINATION)
  const [selectedCategory, setSelectedCategory] = useState("")
  const [transactionType, setTransactionType] = useState<TransactionTypeFilter>("all")
  const [showFilters, setShowFilters] = useState(true)

  const fetchTransactions = async (page = 1, category = selectedCategory) => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await api.transactions.list({
        page,
        size: pagination.size,
        ...(category ? { category } : {}),
      })

      setTransactions(data.items || [])
      setPagination({
        page: data.page || 1,
        size: data.size || INITIAL_PAGINATION.size,
        total: data.total || 0,
        pages: data.pages || 0,
        has_next: data.has_next || false,
        has_prev: data.has_prev || false,
      })
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Erreur lors du chargement")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions(1, selectedCategory)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory])

  const filteredTransactions = useMemo(() => {
    return transactions.filter((transaction) => {
      const matchesSearch = getTransactionDisplayLabel(transaction).toLowerCase().includes(searchQuery.toLowerCase())
      const matchesType =
        transactionType === "all" ||
        (transactionType === "expense" && transaction.is_expense) ||
        (transactionType === "income" && !transaction.is_expense)

      return matchesSearch && matchesType
    })
  }, [transactions, searchQuery, transactionType])

  const insights = useMemo(() => {
    const expenses = filteredTransactions.filter((item) => item.is_expense)
    const incomes = filteredTransactions.filter((item) => !item.is_expense)

    const totalExpenses = expenses.reduce((acc, item) => acc + Number(item.amount), 0)
    const totalIncome = incomes.reduce((acc, item) => acc + Number(item.amount), 0)

    return { totalExpenses, totalIncome, totalNet: totalIncome - totalExpenses }
  }, [filteredTransactions])

  const resetFilters = () => {
    setSelectedCategory("")
    setTransactionType("all")
    setSearchQuery("")
  }

  const handleExportCSV = () => {
    if (filteredTransactions.length === 0) return

    const headers = ["Date", "Libellé", "Catégorie", "Type", "Montant", "Devise"]
    const rows = filteredTransactions.map((transaction) => [
      transaction.date,
      `"${getTransactionDisplayLabel(transaction).replace(/"/g, '""')}"`,
      getCategoryLabel(transaction.category),
      transaction.is_expense ? "Dépense" : "Revenu",
      transaction.is_expense ? -transaction.amount : transaction.amount,
      transaction.currency || "EUR",
    ])

    const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n")
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    const url = URL.createObjectURL(blob)

    link.setAttribute("href", url)
    link.setAttribute("download", `transactions_${new Date().toISOString().split("T")[0]}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (error) {
    return (
      <DashboardLayout>
        <ErrorCard title="Erreur de chargement" description={error} retry={() => fetchTransactions(1)} />
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="glass-card rounded-3xl p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Centre de contrôle des flux</p>
              <h1 className="text-3xl font-semibold">Transactions</h1>
              <p className="text-sm text-muted-foreground">{pagination.total} opérations enregistrées</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <MetricCard label="Entrées" value={`+${formatCurrency(insights.totalIncome)}`} tone="text-green-600" />
              <MetricCard label="Sorties" value={`-${formatCurrency(insights.totalExpenses)}`} tone="text-red-600" />
              <MetricCard
                label="Net"
                value={`${insights.totalNet >= 0 ? "+" : ""}${formatCurrency(insights.totalNet)}`}
                tone={insights.totalNet >= 0 ? "text-green-600" : "text-red-600"}
              />
            </div>
          </div>
        </section>

        <Card className="rounded-3xl">
          <CardHeader className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <CardTitle className="text-xl">Moteur de recherche & filtres</CardTitle>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setShowFilters((v) => !v)}>
                  <SlidersHorizontal className="mr-2 h-4 w-4" />
                  {showFilters ? "Masquer" : "Afficher"}
                </Button>
                <Button variant="outline" size="sm" onClick={handleExportCSV} disabled={filteredTransactions.length === 0}>
                  <Download className="mr-2 h-4 w-4" /> Export CSV
                </Button>
              </div>
            </div>

            <div className="relative max-w-lg">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Rechercher un libellé ou un marchand..."
                className="pl-9"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>

            {showFilters && (
              <div className="grid gap-3 rounded-2xl border bg-muted/25 p-4 md:grid-cols-3">
                <div>
                  <p className="mb-1 text-sm font-medium">Catégorie</p>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                    value={selectedCategory}
                    onChange={(event) => setSelectedCategory(event.target.value)}
                  >
                    <option value="">Toutes</option>
                    {Object.entries(TRANSACTION_CATEGORY_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <p className="mb-1 text-sm font-medium">Type</p>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm"
                    value={transactionType}
                    onChange={(event) => setTransactionType(event.target.value as TransactionTypeFilter)}
                  >
                    <option value="all">Tous</option>
                    <option value="expense">Dépenses</option>
                    <option value="income">Revenus</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button variant="ghost" className="w-full" onClick={resetFilters}>
                    <Filter className="mr-2 h-4 w-4" /> Réinitialiser les filtres
                  </Button>
                </div>
              </div>
            )}
          </CardHeader>

          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-full rounded-xl" />
                ))}
              </div>
            ) : transactions.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <p>Aucune transaction.</p>
                <p className="text-sm">Lancez une synchronisation bancaire.</p>
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-muted-foreground">
                    <tr>
                      <th className="h-11 px-4 text-left">Date</th>
                      <th className="h-11 px-4 text-left">Libellé</th>
                      <th className="h-11 px-4 text-left">Catégorie</th>
                      <th className="h-11 px-4 text-right">Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.map((transaction) => {
                      const displayLabel = getTransactionDisplayLabel(transaction)
                      return (
                        <tr key={transaction.id} className="border-t transition-colors hover:bg-muted/20">
                          <td className="p-4">
                            <Link href={`/transactions/${transaction.id}`}>{transaction.date}</Link>
                          </td>
                          <td className="p-4">
                            <Link href={`/transactions/${transaction.id}`}>
                              <p className="font-medium">{displayLabel}</p>
                              {displayLabel !== transaction.raw_label && (
                                <p className="text-xs text-muted-foreground">{transaction.raw_label}</p>
                              )}
                            </Link>
                          </td>
                          <td className="p-4">
                            <Badge variant="secondary" className={getCategoryBadgeClass(transaction.category)}>
                              {getCategoryLabel(transaction.category)}
                            </Badge>
                          </td>
                          <td className={cn("p-4 text-right font-medium", transaction.is_expense ? "text-red-600" : "text-green-600")}>
                            <Link href={`/transactions/${transaction.id}`}>
                              {transaction.is_expense ? "-" : "+"}
                              {Number(transaction.amount).toFixed(2)} {transaction.currency || "EUR"}
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {pagination.pages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {pagination.page} sur {pagination.pages} ({pagination.total} transactions)
                </p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => fetchTransactions(pagination.page - 1)} disabled={!pagination.has_prev || isLoading}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => fetchTransactions(pagination.page + 1)} disabled={!pagination.has_next || isLoading}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-2xl border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("text-lg font-semibold", tone)}>{value}</p>
    </div>
  )
}
