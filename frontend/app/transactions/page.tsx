"use client"

import { useState, useEffect } from "react"
import DashboardLayout from "../dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, Filter, Download } from "lucide-react"
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

  const fetchTransactions = async (page = 1) => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.transactions.list({ page, size: pagination.size })
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

  const filteredTransactions = transactions.filter((tx) =>
    (tx.cleaned_label || tx.raw_label).toLowerCase().includes(searchQuery.toLowerCase())
  )

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
          <Button variant="outline" disabled>
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
              <Button variant="outline" size="sm" disabled>
                <Filter className="mr-2 h-4 w-4" />
                Filtres
              </Button>
            </div>
          </CardHeader>
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
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ")
}
