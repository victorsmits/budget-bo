"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { ChevronLeft, ChevronRight, Download, Search } from "lucide-react"

import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { CategoryBadge } from "@/components/transactions/category-badge"
import { CategorySelect } from "@/components/transactions/category-select"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { getCategoryLabel, getTransactionDisplayLabel } from "@/lib/transaction-presentation"
import { Transaction } from "@/types/api"

export default function TransactionsPage() {
  const [items, setItems] = useState<Transaction[]>([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("")

  useEffect(() => {
    api.transactions.list({ page, size: 20, ...(category ? { category } : {}) }).then((data) => {
      setItems(data.items || [])
      setPages(data.pages || 1)
      setTotal(data.total || 0)
    })
  }, [page, category])

  const filtered = useMemo(() => items.filter((t) => getTransactionDisplayLabel(t).toLowerCase().includes(search.toLowerCase())), [items, search])

  const exportCSV = () => {
    const csv = [["Date", "Libellé", "Catégorie", "Montant"], ...filtered.map((t) => [t.date, getTransactionDisplayLabel(t), getCategoryLabel(t.category), `${t.is_expense ? "-" : "+"}${t.amount}`])]
      .map((r) => r.join(","))
      .join("\n")
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = `transactions_${new Date().toISOString().split("T")[0]}.csv`
    a.click()
  }

  return (
    <DashboardLayout>
      <div className="space-y-4">
        <PageHeader title="Transactions" subtitle={`${total} opérations synchronisées`} />

        <Card>
          <CardContent className="space-y-3 p-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Recherche rapide" />
              </div>
              <CategorySelect value={category} onChange={(v) => { setCategory(v); setPage(1) }} includeAllOption />
              <Button variant="outline" onClick={exportCSV} disabled={!filtered.length}><Download className="mr-2 size-4" />Exporter CSV</Button>
            </div>

            <div className="space-y-2">
              {filtered.map((t) => (
                <Link key={t.id} href={`/transactions/${t.id}`} className="block rounded-xl border p-3 hover:bg-muted/40">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{getTransactionDisplayLabel(t)}</p>
                      <p className="text-xs text-muted-foreground">{t.date}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <CategoryBadge category={t.category} />
                      <p className={t.is_expense ? "font-semibold text-rose-600" : "font-semibold text-emerald-600"}>{t.is_expense ? "-" : "+"}{Number(t.amount).toFixed(2)} €</p>
                    </div>
                  </div>
                </Link>
              ))}
              {!filtered.length && <p className="py-8 text-center text-sm text-muted-foreground">Aucune transaction.</p>}
            </div>

            <div className="flex items-center justify-between border-t pt-3">
              <p className="text-sm text-muted-foreground">Page {page}/{pages}</p>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft className="size-4" /></Button>
                <Button variant="outline" size="icon" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}><ChevronRight className="size-4" /></Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
