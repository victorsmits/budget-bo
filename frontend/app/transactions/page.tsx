"use client"

import { useState, useEffect } from "react"
import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, Filter, Download, ChevronLeft, ChevronRight } from "lucide-react"
import { api } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { ErrorCard } from "@/components/error"
import Link from "next/link"

interface Transaction {
  id: string
  cleaned_label: string | null
  raw_label: string
  amount: number
  date: string
  category: string
  is_expense: boolean
  is_recurring: boolean
  currency: string
}

const categoryColors: Record<string, string> = {
  subscriptions: "bg-purple-100 text-purple-700",
  food: "bg-green-100 text-green-700",
  income: "bg-blue-100 text-blue-700",
  utilities: "bg-yellow-100 text-yellow-700",
  transportation: "bg-orange-100 text-orange-700",
  healthcare: "bg-red-100 text-red-700",
  shopping: "bg-pink-100 text-pink-700",
  housing: "bg-indigo-100 text-indigo-700",
  insurance: "bg-cyan-100 text-cyan-700",
  entertainment: "bg-fuchsia-100 text-fuchsia-700",
  education: "bg-teal-100 text-teal-700",
  travel: "bg-amber-100 text-amber-700",
  other: "bg-gray-100 text-gray-700",
}

const categoryLabels: Record<string, string> = {
  subscriptions: "Abonnements",
  food: "Alimentation",
  income: "Revenus",
  utilities: "Factures",
  transportation: "Transport",
  healthcare: "Santé",
  shopping: "Achats",
  housing: "Logement",
  insurance: "Assurance",
  entertainment: "Divertissement",
  education: "Éducation",
  travel: "Voyage",
  other: "Autre",
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [pagination, setPagination] = useState({
    page: 1,
    size: 20,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false,
  })
  const [selectedCategory, setSelectedCategory] = useState<string>("")
  const [transactionType, setTransactionType] = useState<string>("all")
  const [showFilters, setShowFilters] = useState(false)

  const fetchTransactions = async (page = 1) => {
    setIsLoading(true)
    setError(null)
    try {
      const params: any = { page, size: pagination.size }
      if (selectedCategory) {
        params.category = selectedCategory
      }
      const data = await api.transactions.list(params)
      setTransactions(data.items || [])
      setPagination({
        page: data.page || 1,
        size: data.size || 20,
        total: data.total || 0,
        pages: data.pages || 0,
        has_next: data.has_next || false,
        has_prev: data.has_prev || false,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [])

  const filteredTransactions = transactions.filter((tx) => {
    const matchesSearch = (tx.cleaned_label || tx.raw_label).toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = transactionType === "all" ||
      (transactionType === "expense" && tx.is_expense) ||
      (transactionType === "income" && !tx.is_expense)
    return matchesSearch && matchesType
  })

  const handleExportCSV = () => {
    if (filteredTransactions.length === 0) return

    const headers = ["Date", "Libellé", "Catégorie", "Type", "Montant", "Devise"]
    const rows = filteredTransactions.map((tx) => [
      tx.date,
      `"${(tx.cleaned_label || tx.raw_label).replace(/"/g, '""')}"`,
      categoryLabels[tx.category] || tx.category,
      tx.is_expense ? "Dépense" : "Revenu",
      tx.is_expense ? -tx.amount : tx.amount,
      tx.currency,
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
        <ErrorCard
          title="Erreur de chargement"
          description={error}
          retry={fetchTransactions}
        />
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
            <p className="text-muted-foreground">
              Historique ({pagination.total} transactions)
            </p>
          </div>
          <Button
            variant="outline"
            onClick={handleExportCSV}
            disabled={filteredTransactions.length === 0}
          >
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Rechercher..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className={showFilters ? "bg-muted" : ""}
              >
                <Filter className="mr-2 h-4 w-4" />
                Filtres
              </Button>
            </div>
          </CardHeader>

          {/* Filtres */}
          {showFilters && (
            <div className="px-6 pb-4 border-b">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Catégorie:</span>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    value={selectedCategory}
                    onChange={(e) => {
                      setSelectedCategory(e.target.value)
                      fetchTransactions(1)
                    }}
                  >
                    <option value="">Toutes</option>
                    {Object.entries(categoryLabels).map(([key, label]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Type:</span>
                  <select
                    className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    value={transactionType}
                    onChange={(e) => setTransactionType(e.target.value)}
                  >
                    <option value="all">Tous</option>
                    <option value="expense">Dépenses</option>
                    <option value="income">Revenus</option>
                  </select>
                </div>
                {(selectedCategory || transactionType !== "all") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedCategory("")
                      setTransactionType("all")
                      fetchTransactions(1)
                    }}
                  >
                    Réinitialiser
                  </Button>
                )}
              </div>
            </div>
          )}

          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : transactions.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
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
                    {filteredTransactions.map((tx) => (
                      <tr key={tx.id} className="border-b hover:bg-muted/50">
                        <td className="p-4 align-middle">
                          <Link href={`/transactions/${tx.id}`} className="block">
                            {tx.date}
                          </Link>
                        </td>
                        <td className="p-4 align-middle">
                          <Link href={`/transactions/${tx.id}`} className="block">
                            <div>
                              <p className="font-medium">{tx.cleaned_label || tx.raw_label}</p>
                              {tx.cleaned_label && tx.cleaned_label !== tx.raw_label && (
                                <p className="text-xs text-muted-foreground">{tx.raw_label}</p>
                              )}
                            </div>
                          </Link>
                        </td>
                        <td className="p-4 align-middle">
                          <Link href={`/transactions/${tx.id}`} className="block">
                            <Badge variant="secondary" className={categoryColors[tx.category] || categoryColors.other}>
                              {categoryLabels[tx.category] || tx.category}
                            </Badge>
                          </Link>
                        </td>
                        <td className={cn("p-4 align-middle text-right font-medium", tx.is_expense ? "text-red-600" : "text-green-600")}>
                          <Link href={`/transactions/${tx.id}`} className="block">
                            {tx.is_expense ? "-" : "+"}{Number(tx.amount).toFixed(2)} {tx.currency}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t mt-4">
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

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
