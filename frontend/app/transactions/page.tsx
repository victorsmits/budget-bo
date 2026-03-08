"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Download, Filter, Search } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { ErrorCard } from "@/components/error"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import {
  getCategoryBadgeClass,
  getCategoryLabel,
  getTransactionDisplayLabel,
  TRANSACTION_CATEGORY_LABELS,
} from "@/lib/transaction-presentation"
import { cn } from "@/lib/utils"
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
  const [showFilters, setShowFilters] = useState(false)

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
      const matchesSearch = getTransactionDisplayLabel(transaction)
        .toLowerCase()
        .includes(searchQuery.toLowerCase())

      const matchesType =
        transactionType === "all" ||
        (transactionType === "expense" && transaction.is_expense) ||
        (transactionType === "income" && !transaction.is_expense)

      return matchesSearch && matchesType
    })
  }, [transactions, searchQuery, transactionType])

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
            <p className="text-muted-foreground">Historique ({pagination.total} transactions)</p>
          </div>
          <Button variant="outline" onClick={handleExportCSV} disabled={filteredTransactions.length === 0}>
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-4">
              <div className="relative max-w-sm flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Rechercher un libellé ou marchand..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>

              <Button variant="outline" size="sm" onClick={() => setShowFilters((value) => !value)}>
                <Filter className="mr-2 h-4 w-4" />
                Filtres
              </Button>
            </div>

            {showFilters && (
              <div className="mt-4 flex flex-wrap items-center gap-4 rounded-md border bg-muted/20 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Catégorie:</span>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
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

                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Type:</span>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    value={transactionType}
                    onChange={(event) => setTransactionType(event.target.value as TransactionTypeFilter)}
                  >
                    <option value="all">Tous</option>
                    <option value="expense">Dépenses</option>
                    <option value="income">Revenus</option>
                  </select>
                </div>

                {(selectedCategory || transactionType !== "all" || searchQuery) && (
                  <Button variant="ghost" size="sm" onClick={resetFilters}>
                    Réinitialiser
                  </Button>
                )}
              </div>
            )}
          </CardHeader>

          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : transactions.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <p>Aucune transaction.</p>
                <p className="text-sm">Lancez une synchronisation bancaire.</p>
              </div>
            ) : (
              <div className="relative w-full overflow-auto">
                <table className="w-full caption-bottom text-sm">
                  <thead className="[&_tr]:border-b">
                    <tr className="border-b">
                      <th className="h-12 px-4 text-left font-medium text-muted-foreground">Date</th>
                      <th className="h-12 px-4 text-left font-medium text-muted-foreground">Libellé</th>
                      <th className="h-12 px-4 text-left font-medium text-muted-foreground">Catégorie</th>
                      <th className="h-12 px-4 text-right font-medium text-muted-foreground">Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.map((transaction) => {
                      const displayLabel = getTransactionDisplayLabel(transaction)
                      return (
                        <tr key={transaction.id} className="border-b hover:bg-muted/50">
                          <td className="p-4 align-middle">
                            <Link href={`/transactions/${transaction.id}`} className="block">
                              {transaction.date}
                            </Link>
                          </td>
                          <td className="p-4 align-middle">
                            <Link href={`/transactions/${transaction.id}`} className="block">
                              <div>
                                <p className="font-medium">{displayLabel}</p>
                                {displayLabel !== transaction.raw_label && (
                                  <p className="text-xs text-muted-foreground">{transaction.raw_label}</p>
                                )}
                              </div>
                            </Link>
                          </td>
                          <td className="p-4 align-middle">
                            <Link href={`/transactions/${transaction.id}`} className="block">
                              <Badge variant="secondary" className={getCategoryBadgeClass(transaction.category)}>
                                {getCategoryLabel(transaction.category)}
                              </Badge>
                            </Link>
                          </td>
                          <td
                            className={cn(
                              "p-4 text-right align-middle font-medium",
                              transaction.is_expense ? "text-red-600" : "text-green-600",
                            )}
                          >
                            <Link href={`/transactions/${transaction.id}`} className="block">
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
              <div className="mt-4 flex items-center justify-between border-t pt-4">
                <p className="text-sm text-muted-foreground">
                  Page {pagination.page} sur {pagination.pages} ({pagination.total} transactions)
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchTransactions(pagination.page - 1)}
                    disabled={!pagination.has_prev || isLoading}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchTransactions(pagination.page + 1)}
                    disabled={!pagination.has_next || isLoading}
                  >
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
